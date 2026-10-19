"""FastAPI app serving the Pantheon Web UI."""

from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import signal
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pantheon import __version__
from pantheon.core.budgets import BudgetExceededError
from pantheon.core.channels import CHANNELS, ChannelAuthError, ChannelQueueFullError
from pantheon.core.connections import (
    connection_config,
    normalized_config,
    provider_identity,
    resolve_connection,
)
from pantheon.core.context import HISTORY_MESSAGE_CHARACTERS, HISTORY_MESSAGES
from pantheon.core.credentials import CredentialError, atomic_text
from pantheon.core.extensions import (
    EXTENSION_ROLES,
    MCPError,
    PluginStore,
    SkillStore,
    mcp_available,
)
from pantheon.core.media import MAX_INPUT_BYTES
from pantheon.core.memory import (
    DEFAULT_MEMORY_KINDS,
    DEFAULT_MEMORY_ROLES,
    classify_memory_text,
)
from pantheon.core.pantheon import Pantheon
from pantheon.core.paths import DataPaths
from pantheon.core.runtime import RuntimeLease, file_mutex
from pantheon.core.scheduler import ScheduleParseError, parse_schedule_request
from pantheon.core.services import WorkspaceServices
from pantheon.core.usage import UsageStore
from pantheon.llm import get_llm_client
from pantheon.llm.openai_client import is_responses_api_model
from pantheon.web.conversations import ConversationStore
from pantheon.web.model_catalog import (
    ModelDiscoveryError,
    discover_documented_models,
    discover_provider_models,
)
from pantheon.web.updates import UpdateChecker

STATIC_DIR = Path(__file__).parent / "static"
STREAM_HEARTBEAT_SECONDS = 5.0
MODEL_CACHE_TTL_SECONDS = 60 * 60
MODEL_DOCUMENTED_TTL_SECONDS = 6 * 60 * 60
MODEL_CATALOG_CHECK_INTERVAL_SECONDS = 5 * 60
MODEL_CACHE_VERSION = 1
OFFICIAL_MODEL_CATALOG_BASE_URLS = {
    "deepseek": {"https://api.deepseek.com", "https://api.deepseek.com/v1"},
    "openai": {"https://api.openai.com/v1"},
    "anthropic": {"https://api.anthropic.com", "https://api.anthropic.com/v1"},
    "ollama": {
        "http://localhost:11434",
        "http://localhost:11434/v1",
        "http://127.0.0.1:11434",
        "http://127.0.0.1:11434/v1",
    },
}
LOGGER = logging.getLogger(__name__)


class ConversationMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(max_length=HISTORY_MESSAGE_CHARACTERS)


class AskRequest(BaseModel):
    task: str
    user_task: str | None = None
    mode: str = "auto"          # "auto" | "role:<name>" | "multi"
    role: str | None = None     # convenience: --role foo → mode = "role:foo"
    skill: str | None = None    # optional explicit installed skill id
    overrides: dict[str, dict[str, str]] | None = None  # {role_name: {provider, model}}
    resume_task_id: str | None = None
    acknowledge_effects: bool = False
    attachments: list[str] = []
    history: list[ConversationMessage] = Field(default_factory=list, max_length=HISTORY_MESSAGES)


class PromptEnhanceRequest(BaseModel):
    prompt: str
    mode: str = "auto"
    overrides: dict[str, dict[str, str]] | None = None


class TerminalRequest(BaseModel):
    command: str
    cwd: str = ""
    timeout_seconds: int = 120


class WorkspaceFileSaveRequest(BaseModel):
    path: str
    content: str
    overwrite: bool = False


class SetupSaveRequest(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    apply_to_roles: bool = True
    credential_storage: str = "env"


class ConnectionSaveRequest(BaseModel):
    provider: str
    model: str = ""
    base_url: str | None = None
    api_key: str | None = None
    credential_storage: str = "env"


class DefaultModelsRequest(BaseModel):
    models: dict[str, dict[str, str]]


class RoleStatusRequest(BaseModel):
    overrides: dict[str, dict[str, str]] = {}


class SetupTestRequest(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None


class OnboardingRequest(BaseModel):
    action: str


class ResumeRequest(BaseModel):
    acknowledge_effects: bool = False


class WorkflowRequest(BaseModel):
    parallel_workers: int = 3
    replan_attempts: int = 1


class SetupModelsRequest(BaseModel):
    provider: str
    base_url: str | None = None
    api_key: str | None = None
    current_model: str | None = None


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class SecuritySaveRequest(BaseModel):
    enabled: bool
    username: str = "admin"
    password: str | None = None


class ChronosScheduleRequest(BaseModel):
    text: str


class MemorySaveRequest(BaseModel):
    content: str
    kind: str = "note"
    source: str = "manual"
    role: str = ""
    tags: list[str] | None = None


class MemorySettingsRequest(BaseModel):
    enabled: bool | None = None
    auto_capture: bool | None = None


class PromptExtensionRequest(BaseModel):
    name: str
    description: str = ""
    instructions: str
    roles: list[str] = []
    enabled: bool = True
    version: str = "1.0.0"
    trigger_terms: list[str] = []
    kind: str = "role"
    allow_implicit_invocation: bool = True


class ExtensionToggleRequest(BaseModel):
    enabled: bool


class MCPServerRequest(BaseModel):
    name: str
    transport: str = "stdio"
    command: str = ""
    args: list[str] = []
    cwd: str = ""
    url: str = ""
    env: dict[str, str] = {}
    headers_env: dict[str, str] = {}
    bearer_token_env_var: str = ""
    credential_env_var: str = ""
    credential_value: str = ""
    enabled: bool = True
    allow_agent_calls: bool = False
    roles: list[str] = []
    tool_policies: dict[str, dict[str, Any]] = {}
    startup_timeout_seconds: int = 15
    tool_timeout_seconds: int = 60


class MCPToolCallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}


class MCPToolPolicyRequest(BaseModel):
    enabled: bool = True
    roles: list[str] = []
    approval: str = "ask"


class MCPApprovalDecisionRequest(BaseModel):
    approved: bool


class WebhookConfigRequest(BaseModel):
    enabled: bool
    token: str = ""
    rotate_token: bool = False


AUTH_COOKIE_NAME = "pantheon_ui_session"
AUTH_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
AUTH_PASSWORD_SCHEME = "pbkdf2_sha256"
AUTH_PASSWORD_ITERATIONS = 260_000
TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
MAX_WORKSPACE_FILE_BYTES = 1_000_000
IGNORED_WORKSPACE_NAMES = {
    ".env",
    ".git",
    ".mypy_cache",
    ".pantheon",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
HTML_SUFFIXES = {".html", ".htm"}
TEXT_SUFFIXES = {
    ".css",
    ".csv",
    ".env.example",
    ".html",
    ".htm",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SETUP_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "label": "DeepSeek",
        "adapter": "openai",
        "env_var": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-flash",
        "models": [
            {"id": "deepseek-flash", "label": "DeepSeek V4.1 Flash"},
            {"id": "deepseek-v4-pro", "label": "DeepSeek V4 Pro"},
        ],
        "requires_key": True,
        "note": "OpenAI-compatible provider. Refresh to load models available to this API key.",
    },
    "openai": {
        "label": "OpenAI",
        "adapter": "openai",
        "env_var": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-6-astra",
        "models": [
            {"id": "gpt-6-astra", "label": "GPT-6 Astra"},
            {"id": "gpt-6.1-sol", "label": "GPT-6.1 Sol"},
            {"id": "gpt-6-sol", "label": "GPT-6 Sol"},
            {"id": "gpt-6-luna", "label": "GPT-6 Luna"},
            {"id": "gpt-5.6", "label": "GPT-5.6 Sol (alias)"},
            {"id": "gpt-5.6-sol", "label": "GPT-5.6 Sol"},
            {"id": "gpt-5.6-terra", "label": "GPT-5.6 Terra"},
            {"id": "gpt-5.6-luna", "label": "GPT-5.6 Luna"},
            {"id": "gpt-5.5", "label": "GPT-5.5"},
            {"id": "gpt-5.4", "label": "GPT-5.4"},
            {"id": "gpt-5.4-mini", "label": "GPT-5.4 mini"},
            {"id": "gpt-5.4-nano", "label": "GPT-5.4 nano"},
            {"id": "gpt-4o", "label": "GPT-4o (legacy compatible)"},
        ],
        "requires_key": True,
        "note": (
            "GPT-6 models use your OpenAI API key. Refresh models to check the "
            "account catalog, then use Test API to verify access before saving."
        ),
    },
    "anthropic": {
        "label": "Anthropic",
        "adapter": "anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com",
        "model": "claude-sonnet-4-6",
        "models": [
            {"id": "claude-fable-5-1", "label": "Claude Fable 5.1"},
            {"id": "claude-opus-5-5", "label": "Claude Opus 5.5"},
            {"id": "claude-sonnet-5-5", "label": "Claude Sonnet 5.5"},
            {"id": "claude-haiku-5-5", "label": "Claude Haiku 5.5"},
            {"id": "claude-opus-5", "label": "Claude Opus 5 (most capable)"},
            {"id": "claude-sonnet-5", "label": "Claude Sonnet 5 (balanced)"},
            {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (balanced)"},
            {"id": "claude-opus-4-8", "label": "Claude Opus 4.8 (deep reasoning)"},
            {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5"},
            {"id": "claude-fable-5", "label": "Claude Fable 5"},
        ],
        "requires_key": True,
        "note": (
            "Official Anthropic and compatible Claude Messages gateways. "
            "Change the Base URL only when your provider supplies one."
        ),
    },
    "ollama": {
        "label": "Ollama",
        "adapter": "ollama",
        "env_var": "",
        "base_url": "http://localhost:11434",
        "model": "llama3.1:8b",
        "models": [
            {"id": "llama3.1:8b", "label": "Llama 3.1 8B"},
            {"id": "llama3.1:70b", "label": "Llama 3.1 70B"},
            {"id": "qwen2.5:72b", "label": "Qwen 2.5 72B"},
            {"id": "mistral-large", "label": "Mistral Large"},
        ],
        "requires_key": False,
        "note": "Local model server. Start Ollama locally before sending requests.",
    },
}
CONFIGURED_ROLE_NAMES = ("hephaestus", "athena", "apollo")
SETUP_ROLE_ORDER = (
    ("hermes", "Hermes", "orchestrator", True),
    ("hephaestus", "Hephaestus", "code", True),
    ("athena", "Athena", "research", True),
    ("apollo", "Apollo", "creative", True),
    ("chronos", "Chronos", "scheduling", False),
)
INTEGRATION_CATALOG: dict[str, list[dict[str, Any]]] = {
    "mcp": [
        {
            "id": "workspace",
            "name": "Local Workspace",
            "status": "ready",
            "summary": "Files, terminal commands, and HTML preview inside the local Pantheon workspace.",
            "assigned_roles": ["hephaestus", "athena", "apollo"],
            "capabilities": ["files", "terminal", "preview"],
            "config_hint": "Built in; controlled by the web workspace APIs.",
        },
        {
            "id": "github",
            "name": "GitHub MCP",
            "status": "ready",
            "summary": "Connect GitHub's remote MCP endpoint for repository tools.",
            "assigned_roles": ["hermes", "hephaestus", "athena"],
            "capabilities": ["repository", "issues", "pull requests"],
            "config_hint": "Use the GitHub preset in Settings -> Integrations -> MCP.",
        },
        {
            "id": "browser",
            "name": "Browser MCP",
            "status": "planned",
            "summary": "Open pages, inspect generated websites, and collect visual QA evidence.",
            "assigned_roles": ["hephaestus", "athena"],
            "capabilities": ["browser", "screenshots", "inspection"],
            "config_hint": "Future browser automation connector.",
        },
        {
            "id": "database",
            "name": "Database MCP",
            "status": "planned",
            "summary": "Query local or remote databases for analysis and agent workflows.",
            "assigned_roles": ["athena", "hephaestus"],
            "capabilities": ["sql", "schema", "query"],
            "config_hint": "Future MCP server with secrets kept in .env.",
        },
    ],
    "plugins": [
        {
            "id": "workspace-toolkit",
            "name": "Workspace Toolkit",
            "status": "ready",
            "summary": "Artifacts, file saving, terminal execution, and preview controls.",
            "assigned_roles": ["hephaestus"],
            "capabilities": ["artifacts", "files", "terminal"],
            "config_hint": "Built in.",
        },
        {
            "id": "memory-pack",
            "name": "Memory Pack",
            "status": "ready",
            "summary": "Long-term memory, suggestions, and role-scoped recall.",
            "assigned_roles": ["hermes", "hephaestus", "athena", "apollo", "chronos"],
            "capabilities": ["memory", "suggestions", "role scope"],
            "config_hint": ".pantheon/memory.sqlite",
        },
        {
            "id": "scheduler-pack",
            "name": "Chronos Scheduler",
            "status": "ready",
            "summary": "Local scheduled jobs through Chronos.",
            "assigned_roles": ["chronos"],
            "capabilities": ["schedule", "jobs", "runs"],
            "config_hint": ".pantheon/chronos_jobs.json",
        },
        {
            "id": "collaboration-pack",
            "name": "Multi-role Council",
            "status": "ready",
            "summary": "Hermes plans and coordinates multiple gods for one task.",
            "assigned_roles": ["hermes", "hephaestus", "athena", "apollo"],
            "capabilities": ["planning", "routing", "synthesis"],
            "config_hint": "Built in.",
        },
    ],
    "skills": [
        {
            "id": "code-builder",
            "name": "Code Builder",
            "status": "ready",
            "summary": "Implementation, refactoring, generated files, and code-focused answers.",
            "assigned_roles": ["hephaestus"],
            "capabilities": ["/code", "/hephaestus", "Save to Files"],
            "config_hint": "Role prompt plus workspace tools.",
        },
        {
            "id": "research-brief",
            "name": "Research Brief",
            "status": "ready",
            "summary": "Structured analysis, comparisons, and source-oriented reasoning.",
            "assigned_roles": ["athena"],
            "capabilities": ["/research", "/athena", "memory recall"],
            "config_hint": "Role prompt.",
        },
        {
            "id": "creative-draft",
            "name": "Creative Draft",
            "status": "ready",
            "summary": "Copy, concepts, prompts, and visual direction.",
            "assigned_roles": ["apollo"],
            "capabilities": ["/creative", "/apollo", "artifact output"],
            "config_hint": "Role prompt.",
        },
        {
            "id": "schedule-task",
            "name": "Schedule Task",
            "status": "ready",
            "summary": "Natural-language local reminders and recurring tasks.",
            "assigned_roles": ["chronos"],
            "capabilities": ["/schedule", "jobs", "runs"],
            "config_hint": ".pantheon/chronos_jobs.json",
        },
    ],
    "channels": [
        {
            "id": "web-ui",
            "name": "Web UI",
            "status": "ready",
            "summary": "The current local browser workspace.",
            "assigned_roles": ["hermes", "hephaestus", "athena", "apollo", "chronos"],
            "capabilities": ["chat", "workspace", "settings"],
            "config_hint": "pantheon web --host 127.0.0.1 --port 8000",
        },
        {
            "id": "webhook",
            "name": "Webhook",
            "status": "ready",
            "summary": "Receive tasks from scripts, automation tools, or other services.",
            "assigned_roles": ["hermes", "chronos"],
            "capabilities": ["incoming task", "secret token"],
            "config_hint": "Enable it in Channels, then call /api/channels/webhook with its token.",
        },
        {
            "id": "team-chat",
            "name": "Team Chat",
            "status": "planned",
            "summary": "DingTalk, WeCom, Feishu, Telegram, Discord, or similar chat entry points.",
            "assigned_roles": ["hermes", "chronos"],
            "capabilities": ["messages", "mentions", "scheduled reports"],
            "config_hint": "Future channel adapters with secrets in .env.",
        },
    ],
}


def create_app(config_path: str | None = None, bind_host: str = "127.0.0.1", bind_port: int = 8000) -> FastAPI:
    """Build the FastAPI app. Pantheon instance is created lazily."""
    _pantheon: dict[str, Pantheon | None] = {"instance": None}
    workspace_root = Path(os.environ.get("PANTHEON_WORKSPACE", Path.cwd())).resolve()
    data_paths = DataPaths.for_workspace(workspace_root)
    workspace_services = WorkspaceServices(data_paths)
    readiness = workspace_services.readiness
    initially_configured = Path(config_path).exists() if config_path else data_paths.config.exists()
    chronos_scheduler = workspace_services.scheduler
    memory_store = workspace_services.memory
    conversation_store = ConversationStore(data_paths.state / "conversations.json")
    usage_store = UsageStore(data_paths.state / "usage.sqlite")
    task_store = workspace_services.tasks
    update_checker = UpdateChecker(__version__)
    skill_store = workspace_services.skills
    plugin_store = workspace_services.plugins
    mcp_manager = workspace_services.mcp
    mcp_approval_lock = threading.Lock()
    pending_mcp_approvals: dict[str, dict[str, Any]] = {}
    chronos_runner: dict[str, asyncio.Task | None] = {"task": None}
    chronos_job_tasks: set[asyncio.Task[None]] = set()
    model_catalog_runner: dict[str, asyncio.Task | None] = {"task": None}
    channel_runner: dict[str, asyncio.Task | None] = {'task': None}
    channel_cancel = threading.Event()
    model_catalog_attempts: dict[str, int] = {}
    model_catalog_errors: dict[str, str] = {}

    runtime = RuntimeLease(data_paths.state / "runtime.lock", {
        "host": bind_host, "port": bind_port, "workspace": str(workspace_root), "version": __version__,
    })

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        runtime.acquire()
        try:
            workspace_services.channels.recover_interrupted()
            channel_cancel.clear()
            channel_runner['task'] = asyncio.create_task(channel_loop())
            if chronos_runner["task"] is None or chronos_runner["task"].done():
                chronos_runner["task"] = asyncio.create_task(chronos_loop())
            if model_catalog_runner["task"] is None or model_catalog_runner["task"].done():
                model_catalog_runner["task"] = asyncio.create_task(model_catalog_loop())
            yield
        finally:
            channel_cancel.set()
            runner_tasks = [
                channel_runner.get('task'),
                chronos_runner.get("task"),
                model_catalog_runner.get("task"),
            ]
            for task in runner_tasks:
                if task is None:
                    continue
                task.cancel()
            await asyncio.gather(*(task for task in runner_tasks if task is not None), return_exceptions=True)
            active_jobs = tuple(chronos_job_tasks)
            for job_task in active_jobs:
                job_task.cancel()
            if active_jobs:
                await asyncio.gather(*active_jobs, return_exceptions=True)
            chronos_job_tasks.clear()
            chronos_runner["task"] = None
            model_catalog_runner["task"] = None
            channel_runner['task'] = None
            runtime.release()

    app = FastAPI(title="Pantheon Web UI", version=__version__, lifespan=lifespan)
    app.state.chronos_runner = chronos_runner
    app.state.chronos_job_tasks = chronos_job_tasks
    app.state.model_catalog_runner = model_catalog_runner

    def get_pantheon() -> Pantheon:
        if _pantheon["instance"] is None:
            active_config_path = config_path
            if active_config_path is None:
                configured_path = setup_config_path()
                if configured_path.exists():
                    active_config_path = str(configured_path)
            env_path = setup_env_path()
            _pantheon["instance"] = Pantheon(
                config_path=active_config_path,
                env_path=str(env_path) if env_path.exists() else None,
            )
            if hasattr(_pantheon["instance"], "services"):
                _pantheon["instance"].services = workspace_services
                _pantheon["instance"].handle_memory = False
                workspace_services.media.connection_provider = lambda: getattr(_pantheon['instance'], 'config', {})
                _pantheon['instance'].hermes.attachment_processor = workspace_services.media.understand
                _pantheon['instance'].hermes.media_context_provider = workspace_services.media.agent_context
                _pantheon['instance'].hermes.image_generator = workspace_services.media.generate_image
            chronos_role = _pantheon["instance"].get_role("chronos")
            if chronos_role is not None:
                chronos_role.config["scheduler"] = chronos_scheduler
            _pantheon["instance"].hermes.memory_context_provider = memory_context_for_role
            _pantheon["instance"].hermes.skill_context_provider = skill_store.context_block
            _pantheon["instance"].hermes.skill_catalog_provider = skill_store.catalog_for_roles
            _pantheon["instance"].hermes.skill_lookup_provider = skill_store.get
            _pantheon["instance"].hermes.plugin_context_provider = plugin_store.context_block
            _pantheon["instance"].hermes.mcp_context_provider = mcp_manager.agent_context
            _pantheon["instance"].hermes.mcp_tool_executor = mcp_tool_executor
        return _pantheon["instance"]

    def request_pantheon(overrides: dict[str, dict[str, str]] | None = None) -> Pantheon:
        """Snapshot execution objects so concurrent chats never mutate defaults."""
        base = get_pantheon()
        p = copy.copy(base)
        p.hermes = copy.copy(base.hermes)
        p.hermes.cancel_event = threading.Event()
        p.hermes.task_store = task_store
        p.hermes.active_task_id = None
        p.hermes.deadline = time.monotonic() + 600
        if hasattr(base, "roles"):
            p.roles = {name: copy.copy(role) for name, role in base.roles.items()}
            for role in p.roles.values():
                role.config = dict(role.config)
            p.hermes.roles = p.roles
        if hasattr(base, "router"):
            p.router = copy.copy(base.router)
            p.hermes.router = p.router
        for role_name, override in (overrides or {}).items():
            role = p.get_role(role_name)
            if role is None and role_name != 'hermes':
                raise ValueError(f"Unknown role: {role_name}")
            if role_name == 'chronos':
                continue
            provider_id = str(override.get("provider") or "").strip().lower()
            if provider_id:
                if provider_id not in SETUP_PROVIDER_PRESETS:
                    raise ValueError(f"Unknown provider: {provider_id}")
                preset = SETUP_PROVIDER_PRESETS[provider_id]
                adapter = str(preset["adapter"])
                providers = getattr(base, "config", {}).get("llm_providers", {})
                provider_config = providers.get(adapter, {})
                configured_provider = provider_config.get("provider_id") or provider_key_from_adapter(adapter, providers)
                if adapter == "openai" and not provider_config.get("provider_id"):
                    deepseek_key = env_value("DEEPSEEK_API_KEY")
                    if deepseek_key and provider_config.get("api_key") == deepseek_key:
                        configured_provider = "deepseek"
                matches = configured_provider == provider_id
                client = getattr(base, "llm_clients", {}).get(adapter) if matches else None
                if provider_identity(provider_id, providers) == provider_id:
                    client = getattr(base, 'llm_clients', {}).get(provider_id) or client
                if client is None:
                    endpoint, key = resolve_connection(read_yaml_config(setup_config_path()), provider_id, env_value)
                    if not key and preset['requires_key']:
                        raise ValueError(f"Add the {preset['label']} API key in Connections before using this role.")
                    client = get_llm_client(
                        provider=str(preset["adapter"]),
                        api_key=key,
                        base_url=endpoint,
                    )
                    client.provider_name = provider_id
                    client.usage_recorder = p.usage_store.record
                    client.budget = workspace_services.budget
                if role_name == 'hermes':
                    p.router.llm_client = client
                else:
                    role.llm_client = client
            if override.get("model"):
                if role_name == 'hermes':
                    p.router.hermes_model = override['model']
                else:
                    role.model = override["model"]
        return p

    def reset_pantheon() -> None:
        _pantheon["instance"] = None

    def memory_payload(query: str = "", kind: str = "", role: str = "") -> dict[str, Any]:
        return {
            "stats": memory_store.stats(),
            "items": memory_store.list(
                query=query.strip(),
                kind=kind.strip(),
                role=role.strip(),
                limit=50,
            ),
            "suggestions": memory_store.suggestions(limit=50),
            "kinds": sorted(DEFAULT_MEMORY_KINDS),
            "roles": sorted(DEFAULT_MEMORY_ROLES),
        }

    def memory_context_for_role(content: str, role_name: str) -> tuple[str, list[dict[str, Any]]]:
        return memory_store.context_block(content, role=role_name)

    def mcp_tool_executor(
        call: dict[str, Any],
        *,
        role_name: str = "",
        on_event: Any = None,
    ) -> dict[str, Any]:
        server_id = str(call.get("server_id") or "")
        tool_name = str(call.get("tool") or "")
        policy = mcp_manager.agent_tool_policy(server_id, tool_name, role_name)
        if policy.get("approval") == "ask":
            if not callable(on_event):
                raise MCPError(
                    "This MCP tool requires interactive approval in the Pantheon Web UI"
                )
            approval_id = secrets.token_urlsafe(12)
            approval_event = threading.Event()
            public_payload = {
                "approval_id": approval_id,
                "call_id": str(call.get("call_id") or ""),
                "server_id": server_id,
                "server_name": policy.get("server_name") or server_id,
                "tool": tool_name,
                "tool_title": policy.get("tool", {}).get("title") or tool_name,
                "role": role_name,
                "risk": policy.get("tool", {}).get("risk") or "unknown",
                "arguments": call.get("arguments") if isinstance(call.get("arguments"), dict) else {},
            }
            pending = {
                "event": approval_event,
                "approved": False,
                "payload": public_payload,
                "created_at": time.time(),
            }
            with mcp_approval_lock:
                pending_mcp_approvals[approval_id] = pending
            on_event("mcp_approval_required", public_payload)
            approval_deadline = time.monotonic() + 120
            resolved = False
            try:
                while time.monotonic() < approval_deadline:
                    cancellation = getattr(on_event, "cancel_event", None)
                    if cancellation is not None and cancellation.is_set():
                        raise MCPError("Task stopped before tool approval")
                    if approval_event.wait(timeout=0.25):
                        resolved = True
                        break
            finally:
                with mcp_approval_lock:
                    pending_mcp_approvals.pop(approval_id, None)
            if not resolved:
                on_event("mcp_approval_resolved", {
                    **public_payload,
                    "approved": False,
                    "reason": "Approval timed out",
                })
                raise MCPError("MCP approval timed out after 120 seconds")
            if not pending.get("approved"):
                on_event("mcp_approval_resolved", {
                    **public_payload,
                    "approved": False,
                    "reason": "Denied by user",
                })
                raise MCPError("MCP tool call was denied by the user")
            on_event("mcp_approval_resolved", {
                **public_payload,
                "approved": True,
                "reason": "Allowed once",
            })
        return mcp_manager.call_tool(
            server_id,
            tool_name,
            call.get("arguments") if isinstance(call.get("arguments"), dict) else {},
        )

    def mcp_servers_payload() -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for stored in mcp_manager.list():
            item = dict(stored)
            credential_names = set((item.get("env") or {}).values())
            credential_names.update((item.get("headers_env") or {}).values())
            bearer_env = str(item.get("bearer_token_env_var") or "").strip()
            if bearer_env:
                credential_names.add(bearer_env)
            sorted_names = sorted(str(name) for name in credential_names if str(name))
            item["credential_env_vars"] = sorted_names
            item["credentials_ready"] = all(env_value(name) for name in sorted_names)
            items.append(item)
        return {
            "available": mcp_available(),
            "items": items,
            "path": str(mcp_manager.path),
            "secrets_path": str(setup_env_path()),
            "pending_approvals": len(pending_mcp_approvals),
        }

    def save_mcp_request(
        req: MCPServerRequest,
        server_id: str = "",
    ) -> dict[str, Any]:
        data = req.model_dump()
        credential_env_var = str(data.pop("credential_env_var", "") or "").strip()
        credential_value = str(data.pop("credential_value", "") or "").strip()
        if credential_env_var:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", credential_env_var):
                raise ValueError("credential environment variable name is invalid")
            if credential_value:
                write_runtime_env(credential_env_var, credential_value)
            if data.get("transport") == "streamable_http":
                data["bearer_token_env_var"] = (
                    data.get("bearer_token_env_var") or credential_env_var
                )
            else:
                env = dict(data.get("env") or {})
                env.setdefault(credential_env_var, credential_env_var)
                data["env"] = env
        return mcp_manager.save(data, server_id=server_id)

    def integrations_payload() -> dict[str, Any]:
        sections: dict[str, list[dict[str, Any]]] = {}
        summary: dict[str, dict[str, int]] = {}
        for section, items in INTEGRATION_CATALOG.items():
            rendered_items = [dict(item) for item in items]
            if section == 'channels':
                rendered_items = [item for item in rendered_items if item['id'] != 'team-chat']
                rendered_items.extend({**workspace_services.channels.status(name),
                                       'status': 'ready' if workspace_services.channels.config(name)['enabled'] else 'not_connected',
                                       'summary': 'Verified incoming tasks with allowlists and optional replies.',
                                       'capabilities': ['text tasks', 'callback verification', 'deduplication', 'bot replies']} for name in CHANNELS)
            sections[section] = rendered_items
            summary[section] = {
                "total": len(rendered_items),
                "ready": sum(1 for item in rendered_items if item.get("status") == "ready"),
                "planned": sum(1 for item in rendered_items if item.get("status") == "planned"),
            }
        return {
            "summary": summary,
            "sections": sections,
            "runtime": {
                "mcp_available": mcp_available(),
                "mcp_servers": len(mcp_manager.list()),
                "mcp_ready": sum(
                    1 for item in mcp_manager.list()
                    if item.get("enabled", True) and (item.get("last_test") or {}).get("ok")
                ),
                "plugins": len(plugin_store.list()),
                "plugins_enabled": sum(1 for item in plugin_store.list() if item.get("enabled", True)),
                "skills": len(skill_store.list()),
                "skills_enabled": sum(1 for item in skill_store.list() if item.get("enabled", True)),
                "webhook_enabled": env_value("PANTHEON_WEBHOOK_ENABLED").strip().lower() in TRUE_VALUES,
            },
            "paths": {
                "config_path": str(setup_config_path()),
                "env_path": str(setup_env_path()),
                "plugins_path": str((workspace_root / "plugins").resolve()),
                "skills_path": str(skill_store.path.resolve()),
                "extension_state_path": str((data_paths.state).resolve()),
            },
        }

    def process_user_memory(user_text: str) -> dict[str, list[dict[str, Any]]]:
        return workspace_services.process_input(user_text)

    def maybe_auto_capture_memory(task: str, result: dict[str, Any], mode: str) -> None:
        workspace_services.capture_result(task, result, mode)

    def ask_with_memory(
        content: str,
        mode: str,
        skill: str | None = None,
        overrides: dict[str, dict[str, str]] | None = None,
        attachments: list[str] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        p = request_pantheon(overrides)
        result = p.ask(content, mode=mode, skill=skill,
                       **({'attachments': attachments} if attachments else {}),
                       **({'history': history} if history else {}))
        result["memory_matches"] = result.get("memory_matches", [])
        result["skill_matches"] = result.get("skill_matches", [])
        maybe_auto_capture_memory(content, result, mode)
        return result

    async def channel_loop():
        def execute(content, mode):
            p = request_pantheon()
            p.hermes.mcp_tool_executor = workspace_services.execute_tool
            def on_event(event, data):
                pass
            on_event.cancel_event = channel_cancel
            workspace_services.process_input(content)
            result = p.ask(content, mode=mode, on_event=on_event)
            workspace_services.capture_result(content, result, mode)
            return result
        while True:
            try:
                handled = await asyncio.to_thread(workspace_services.channels.process_next, execute)
                if not handled:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.warning('Channel worker paused after a local storage/configuration error')
                await asyncio.sleep(5)

    # ----- Static files -----
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    async def execute_chronos_job(job: dict[str, Any]) -> None:
        started = time.time()
        job_id = str(job.get("id") or "")
        try:
            def run_job() -> dict[str, Any]:
                return ask_with_memory(
                    str(job.get("prompt") or ""),
                    mode=str(job.get("mode") or "auto"),
                )

            result = await asyncio.to_thread(run_job)
            content = str(result.get("content") or "")
            chronos_scheduler.record_run(
                job_id,
                success=True,
                output=content,
                started_at=started,
                finished_at=time.time(),
                duration_ms=int((time.time() - started) * 1000),
            )
        except Exception as e:
            chronos_scheduler.record_run(
                job_id,
                success=False,
                error=str(e),
                started_at=started,
                finished_at=time.time(),
                duration_ms=int((time.time() - started) * 1000),
            )

    async def chronos_loop() -> None:
        try:
            while True:
                for job in chronos_scheduler.claim_due_jobs():
                    job_task = asyncio.create_task(execute_chronos_job(job))
                    chronos_job_tasks.add(job_task)
                    job_task.add_done_callback(chronos_job_tasks.discard)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise

    def workspace_error(status_code: int, detail: str) -> HTTPException:
        return HTTPException(status_code=status_code, detail=detail)

    def resolve_workspace_path(raw_path: str | None = "") -> Path:
        raw_path = raw_path or ""
        requested = Path(raw_path)
        if requested.is_absolute():
            raise workspace_error(400, "workspace paths must be relative")
        candidate = (workspace_root / requested).resolve()
        try:
            candidate.relative_to(workspace_root)
        except ValueError as e:
            raise workspace_error(403, "path escapes workspace root") from e
        return candidate

    def relative_workspace_path(path: Path) -> str:
        rel = path.resolve().relative_to(workspace_root)
        if str(rel) == ".":
            return ""
        return rel.as_posix()

    def describe_workspace_path(path: Path) -> dict[str, Any] | None:
        try:
            resolved = path.resolve()
            resolved.relative_to(workspace_root)
            stat = path.stat()
        except (OSError, ValueError):
            return None
        is_dir = path.is_dir()
        suffix = path.suffix.lower()
        return {
            "name": path.name or workspace_root.name,
            "path": relative_workspace_path(path),
            "kind": "directory" if is_dir else "file",
            "size": None if is_dir else stat.st_size,
            "modified": stat.st_mtime,
            "previewable": (not is_dir) and suffix in HTML_SUFFIXES,
            "text": is_dir or suffix in TEXT_SUFFIXES or stat.st_size <= MAX_WORKSPACE_FILE_BYTES,
        }

    def workspace_items(path: Path) -> list[dict[str, Any]]:
        items = []
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if child.name in IGNORED_WORKSPACE_NAMES:
                continue
            item = describe_workspace_path(child)
            if item is not None:
                items.append(item)
        return items

    def setup_config_path() -> Path:
        raw = config_path or os.environ.get("PANTHEON_CONFIG")
        if raw:
            path = Path(raw)
            return (workspace_root / path).resolve() if not path.is_absolute() else path.resolve()
        return data_paths.config

    def setup_env_path() -> Path:
        return data_paths.env

    def setup_model_cache_path() -> Path:
        return (data_paths.state / "model_catalog.json").resolve()

    def read_yaml_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def write_yaml_config(path: Path, data: dict[str, Any]) -> None:
        atomic_text(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False))

    def read_model_cache() -> dict[str, Any]:
        path = setup_model_cache_path()
        if not path.exists():
            return {"version": MODEL_CACHE_VERSION, "catalogs": {}}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"version": MODEL_CACHE_VERSION, "catalogs": {}}
        if not isinstance(payload, dict) or not isinstance(payload.get("catalogs"), dict):
            return {"version": MODEL_CACHE_VERSION, "catalogs": {}}
        return payload

    def model_cache_key(provider_id: str, base_url: str, api_key: str = "") -> str:
        identity = f"{base_url.rstrip('/')}\0{api_key}"
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        return f"{provider_id}:{digest}"

    def cached_model_catalog(
        provider_id: str,
        base_url: str,
        api_key: str = "",
    ) -> dict[str, Any] | None:
        key = model_cache_key(provider_id, base_url, api_key)
        entry = read_model_cache().get("catalogs", {}).get(key)
        if not isinstance(entry, dict) or not isinstance(entry.get("models"), list):
            return None
        return entry

    def write_model_cache(
        provider_id: str,
        base_url: str,
        models: list[dict[str, str]],
        api_key: str = "",
        *,
        documented: bool = False,
    ) -> dict[str, Any]:
        path = setup_model_cache_path()
        payload = read_model_cache()
        fetched_at = int(time.time())
        entry = {
            "provider": provider_id,
            "fetched_at": fetched_at,
            "models": models,
            "source": "documented" if documented else "account",
        }
        payload["version"] = MODEL_CACHE_VERSION
        payload.setdefault("catalogs", {})[
            f"{provider_id}:documented" if documented else model_cache_key(provider_id, base_url, api_key)
        ] = entry
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        temp_path.replace(path)
        return entry

    def parse_env_file(path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        if not path.exists():
            return values
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            if key:
                values[key] = value
        return values

    def format_env_line(key: str, value: str) -> str:
        if value and all(ch.isalnum() or ch in "_-.:/+=" for ch in value):
            rendered = value
        else:
            rendered = json.dumps(value)
        return f"{key}={rendered}"

    def write_env_value(path: Path, key: str, value: str) -> None:
        store = workspace_services.credentials
        storage = "system" if key in store.refs() else "env"
        store.save(key, value, storage=storage)

    def env_value(env_var: str) -> str:
        if not env_var:
            return ""
        return workspace_services.credentials.get(env_var)

    def write_runtime_env(key: str, value: str) -> None:
        write_env_value(setup_env_path(), key, value)

    # MCP subprocesses and HTTP headers resolve only explicitly referenced
    # secrets from Pantheon's local .env file.
    mcp_manager.env_lookup = env_value

    def normalize_username(username: str) -> str:
        clean = username.strip()
        if not clean:
            raise HTTPException(status_code=400, detail="username is required")
        if len(clean) > 64:
            raise HTTPException(status_code=400, detail="username is too long")
        if any(ch in clean for ch in ("\n", "\r", "|")):
            raise HTTPException(status_code=400, detail="username contains invalid characters")
        return clean

    def hash_password(password: str) -> str:
        salt = secrets.token_urlsafe(18)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            AUTH_PASSWORD_ITERATIONS,
        )
        encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return f"{AUTH_PASSWORD_SCHEME}${AUTH_PASSWORD_ITERATIONS}${salt}${encoded}"

    def verify_password_hash(password: str, stored_hash: str) -> bool:
        try:
            scheme, raw_iterations, salt, encoded = stored_hash.split("$", 3)
            if scheme != AUTH_PASSWORD_SCHEME:
                return False
            iterations = int(raw_iterations)
            expected = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
        except Exception:
            return False
        return hmac.compare_digest(actual, expected)

    def auth_config() -> dict[str, Any]:
        requested_enabled = env_value("PANTHEON_UI_AUTH_ENABLED").strip().lower() in TRUE_VALUES
        username = env_value("PANTHEON_UI_USERNAME").strip() or "admin"
        password_hash = env_value("PANTHEON_UI_PASSWORD_HASH").strip()
        plain_password = env_value("PANTHEON_UI_PASSWORD")
        configured = bool(password_hash or plain_password)
        return {
            "requested_enabled": requested_enabled,
            "enabled": bool(requested_enabled and configured),
            "configured": configured,
            "username": username,
            "password_hash": password_hash,
            "has_plain_password": bool(plain_password),
            "plain_password": plain_password,
            "session_secret": env_value("PANTHEON_UI_SESSION_SECRET"),
        }

    def auth_session_secret() -> str:
        secret = env_value("PANTHEON_UI_SESSION_SECRET")
        if secret:
            return secret
        return getattr(app.state, "auth_session_secret", "")

    def ensure_auth_session_secret() -> str:
        secret = auth_session_secret()
        if secret:
            return secret
        secret = secrets.token_urlsafe(32)
        app.state.auth_session_secret = secret
        return secret

    def password_matches(password: str, cfg: dict[str, Any]) -> bool:
        stored_hash = str(cfg.get("password_hash") or "")
        if stored_hash:
            return verify_password_hash(password, stored_hash)
        plain = str(cfg.get("plain_password") or "")
        return bool(plain) and hmac.compare_digest(password, plain)

    def make_auth_token(username: str) -> str:
        issued = str(int(time.time()))
        nonce = secrets.token_urlsafe(12)
        payload = f"{username}|{issued}|{nonce}"
        signature = hmac.new(
            ensure_auth_session_secret().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return base64.urlsafe_b64encode(f"{payload}|{signature}".encode()).decode("ascii")

    def request_is_authenticated(request: Request) -> bool:
        cfg = auth_config()
        if not cfg["enabled"]:
            return True
        token = request.cookies.get(AUTH_COOKIE_NAME, "")
        if not token:
            return False
        try:
            raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
            username, issued, nonce, signature = raw.split("|", 3)
            issued_at = int(issued)
        except Exception:
            return False
        if username != cfg["username"]:
            return False
        if int(time.time()) - issued_at > AUTH_MAX_AGE_SECONDS:
            return False
        payload = f"{username}|{issued}|{nonce}"
        expected = hmac.new(
            ensure_auth_session_secret().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def set_auth_cookie(response: JSONResponse, username: str, request: Request) -> None:
        response.set_cookie(
            AUTH_COOKIE_NAME,
            make_auth_token(username),
            max_age=AUTH_MAX_AGE_SECONDS,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
        )

    def clear_auth_cookie(response: JSONResponse) -> None:
        response.delete_cookie(AUTH_COOKIE_NAME)

    def auth_status_payload(request: Request, message: str = "") -> dict[str, Any]:
        cfg = auth_config()
        authenticated = request_is_authenticated(request)
        return {
            "message": message,
            "enabled": cfg["enabled"],
            "requested_enabled": cfg["requested_enabled"],
            "configured": cfg["configured"],
            "authenticated": authenticated,
            "username": cfg["username"],
            "env_path": str(setup_env_path()),
            "session_days": AUTH_MAX_AGE_SECONDS // (24 * 60 * 60),
        }

    def env_var_from_api_key(raw_api_key: Any) -> str:
        value = str(raw_api_key or "")
        match = re.search(r"\$\{([A-Z_][A-Z0-9_]*)(?::-[^}]*)?\}", value)
        return match.group(1) if match else ""

    def mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "••••"
        return f"{value[:4]}••••{value[-4:]}"

    def sanitize_error(message: str, secrets: list[str] | None = None) -> str:
        safe = str(message or "Request failed")
        for secret in secrets or []:
            if secret and len(secret) > 4:
                safe = safe.replace(secret, mask_secret(secret))
        return safe

    def setup_test_kwargs(adapter: str, base_url: str, model: str) -> dict[str, Any]:
        if adapter == "anthropic":
            return {"max_tokens": 8}
        if (
            adapter == "openai"
            and "api.openai.com" in (base_url or "").lower()
            and is_responses_api_model(model)
        ):
            return {"max_output_tokens": 8}
        return {"max_tokens": 8}

    def normalized_provider_api_key(provider_id: str, value: str) -> str:
        api_key = str(value or "").strip()
        if provider_id == "anthropic" and api_key.lower().startswith("bearer "):
            return api_key[7:].strip()
        return api_key

    def model_label_from_preset(provider_id: str, model_id: str) -> str:
        preset = SETUP_PROVIDER_PRESETS.get(provider_id, {})
        for item in preset.get("models", []):
            if item.get("id") == model_id:
                return str(item.get("label") or model_id)
        return model_id

    def merged_model_catalog(
        provider_id: str,
        discovered: list[dict[str, str]] | None = None,
        current_model: str = "",
    ) -> list[dict[str, Any]]:
        preset = SETUP_PROVIDER_PRESETS[provider_id]
        discovered_by_id = {
            str(item.get("id") or ""): item
            for item in discovered or []
            if str(item.get("id") or "")
        }
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in preset.get("models", []):
            model_id = str(item.get("id") or "")
            if not model_id or model_id in seen:
                continue
            dynamic = discovered_by_id.pop(model_id, None)
            if discovered is not None and dynamic is None and model_id != current_model:
                continue
            result.append({
                "id": model_id,
                "label": str(item.get("label") or model_id),
                "source": "current" if model_id == current_model else "recommended",
                "available": None if discovered is None else dynamic is not None,
            })
            seen.add(model_id)
        for model_id, item in discovered_by_id.items():
            if model_id in seen:
                continue
            result.append({
                "id": model_id,
                "label": str(item.get("label") or model_id),
                "source": "available",
                "available": True,
            })
            seen.add(model_id)
        if current_model and current_model not in seen:
            result.insert(0, {
                "id": current_model,
                "label": model_label_from_preset(provider_id, current_model),
                "source": "current",
                "available": None if discovered is None else False,
            })
        return result

    def provider_payload(
        provider_id: str,
        *,
        current_model: str = "",
        discovered: list[dict[str, str]] | None = None,
        source: str = "built-in",
        fetched_at: int | None = None,
        base_url: str = "",
        key_configured: bool | None = None,
    ) -> dict[str, Any]:
        preset = SETUP_PROVIDER_PRESETS[provider_id]
        if key_configured is None:
            key_configured = (
                not preset["requires_key"]
                or bool(env_value(str(preset.get("env_var") or "")))
            )
        models = merged_model_catalog(provider_id, discovered, current_model)
        # Catalog omission is not an API failure. Keep the saved custom test ID
        # assignable in both full status and explicit catalog refresh responses.
        saved_model = str(connection_config(read_yaml_config(setup_config_path()), provider_id).get('test_model') or '').strip()
        if saved_model and not any(item['id'] == saved_model for item in models):
            models.append({'id': saved_model, 'label': saved_model,
                           'source': 'saved', 'available': None})
        return {
            "id": provider_id,
            "label": preset["label"],
            "model": preset["model"],
            "models": models,
            "base_url": base_url or preset["base_url"],
            "env_var": preset["env_var"],
            "requires_key": preset["requires_key"],
            "key_configured": key_configured,
            "note": preset["note"],
            "catalog_source": source,
            "models_fetched_at": fetched_at,
            "catalog_stale": bool(
                fetched_at and int(time.time()) - fetched_at > MODEL_CACHE_TTL_SECONDS
            ),
        }

    def provider_status_payload(
        provider_id: str,
        *,
        current_provider: str,
        current_model: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        preset = SETUP_PROVIDER_PRESETS[provider_id]
        base_url, api_key = provider_catalog_connection(provider_id, config)
        key_configured = not preset["requires_key"] or bool(api_key)
        cached = cached_model_catalog(provider_id, base_url, api_key)
        documented = read_model_cache().get("catalogs", {}).get(f"{provider_id}:documented")
        if not isinstance(documented, dict) or not isinstance(documented.get("models"), list):
            documented = None
        payload = provider_payload(
            provider_id,
            current_model=current_model if provider_id == current_provider else "",
            discovered=cached.get("models") if cached else None,
            source=(
                "cache"
                if cached
                else str(preset.get("fallback_catalog_source") or "built-in")
            ),
            fetched_at=int(cached.get("fetched_at") or 0) if cached else None,
            base_url=base_url,
            key_configured=key_configured,
        )
        if not cached and documented:
            additions = [{**item, "label": model_label_from_preset(provider_id, item["id"])
                          if item.get("label") == item["id"] else item.get("label", item["id"]),
                          "source": "documented", "available": None}
                         for item in documented["models"]]
            ids = {item["id"] for item in additions}
            payload["models"] = additions + [item for item in payload["models"] if item["id"] not in ids]
            payload["catalog_source"] = "documented"
            payload["models_fetched_at"] = documented.get("fetched_at")
            payload["catalog_stale"] = int(time.time()) - int(documented.get("fetched_at") or 0) >= MODEL_DOCUMENTED_TTL_SECONDS
        payload["recommendations_error"] = model_catalog_errors.get(f"{provider_id}:documented", "")

        identity = model_cache_key(provider_id, base_url, api_key)
        error = model_catalog_errors.get(identity, "")
        status = "ready" if cached else "pending"
        if not key_configured:
            status = "missing_key"
        elif not official_catalog_base_url(provider_id, base_url):
            status = "manual_endpoint"
        elif error:
            status = "error"
        elif payload["catalog_stale"]:
            status = "stale"
        payload.update({
            "catalog_refresh_status": status,
            "catalog_error": error,
            "models_last_attempt_at": model_catalog_attempts.get(identity),
            "models_refresh_interval_seconds": MODEL_CACHE_TTL_SECONDS,
            "masked_key": mask_secret(api_key),
            "test_model": str(connection_config(config, provider_id).get('test_model') or preset['model']),
            "connection_saved": bool(connection_config(config, provider_id)),
            "credential_storage": 'system' if preset['env_var'] in workspace_services.credentials.refs() else 'env',
        })
        payload['api_health'] = readiness.health(provider_id, payload['test_model'], base_url, api_key)
        return payload

    def provider_key_from_adapter(provider: str, providers: dict[str, Any]) -> str:
        if not provider or provider == "none":
            return "none"
        identity = (providers.get(provider, {}) or {}).get("provider_id")
        if identity in SETUP_PROVIDER_PRESETS:
            return identity
        if provider == "openai":
            openai_cfg = providers.get("openai", {}) or {}
            base_url = str(openai_cfg.get("base_url", "")).lower()
            api_key = str(openai_cfg.get("api_key", ""))
            if "deepseek" in base_url or "DEEPSEEK_API_KEY" in api_key:
                return "deepseek"
            return "openai"
        if provider == "anthropic":
            return "anthropic"
        if provider in SETUP_PROVIDER_PRESETS:
            return provider
        return provider

    def provider_from_config(config: dict[str, Any]) -> str:
        config = normalized_config(config)
        hermes_cfg = config.get("pantheon", {}).get("hermes", {}) or {}
        provider = hermes_cfg.get("provider", "")
        providers = config.get("llm_providers", {}) or {}
        provider_key = provider_key_from_adapter(provider, providers) if provider else "deepseek"
        return provider_key if provider_key in SETUP_PROVIDER_PRESETS else "deepseek"

    def normalized_catalog_base_url(base_url: str) -> str:
        return str(base_url or "").strip().rstrip("/").lower()

    def official_catalog_base_url(provider_id: str, base_url: str) -> bool:
        normalized = normalized_catalog_base_url(base_url)
        return normalized in {
            normalized_catalog_base_url(item)
            for item in OFFICIAL_MODEL_CATALOG_BASE_URLS.get(provider_id, set())
        }

    def provider_catalog_connection(provider_id: str, config: dict[str, Any]) -> tuple[str, str]:
        return resolve_connection(config, provider_id, env_value)

    def configured_model_catalogs() -> list[dict[str, str]]:
        config = read_yaml_config(setup_config_path())
        providers = normalized_config(config).get("llm_providers", {}) or {}
        configured_ids = {provider_key_from_adapter(str(adapter), providers)
                          for adapter, value in providers.items() if isinstance(value, dict)}
        catalogs: list[dict[str, str]] = []
        for provider_id, preset in SETUP_PROVIDER_PRESETS.items():
            base_url, api_key = provider_catalog_connection(provider_id, config)
            if not official_catalog_base_url(provider_id, base_url):
                continue
            if preset["requires_key"] and not api_key:
                continue
            if not preset["requires_key"] and provider_id not in configured_ids:
                continue
            catalogs.append({
                "provider": provider_id,
                "discovery_provider": str(preset.get("discovery_provider") or provider_id),
                "base_url": base_url,
                "api_key": api_key,
            })
        return catalogs

    async def refresh_due_model_catalogs() -> dict[str, list[str]]:
        now = int(time.time())
        result: dict[str, list[str]] = {
            "refreshed": [],
            "fresh": [],
            "failed": [],
        }
        for catalog in configured_model_catalogs():
            provider_id = catalog["provider"]
            base_url = catalog["base_url"]
            api_key = catalog["api_key"]
            cached = cached_model_catalog(provider_id, base_url, api_key)
            fetched_at = int(cached.get("fetched_at") or 0) if cached else 0
            if fetched_at and now - fetched_at < MODEL_CACHE_TTL_SECONDS:
                result["fresh"].append(provider_id)
                continue
            attempt_key = model_cache_key(provider_id, base_url, api_key)
            last_attempt = model_catalog_attempts.get(attempt_key, 0)
            if last_attempt and now - last_attempt < MODEL_CATALOG_CHECK_INTERVAL_SECONDS:
                continue
            model_catalog_attempts[attempt_key] = now
            try:
                discovered = await discover_provider_models(
                    catalog["discovery_provider"],
                    base_url,
                    api_key,
                )
                write_model_cache(provider_id, base_url, discovered, api_key)
                model_catalog_errors.pop(attempt_key, None)
                result["refreshed"].append(provider_id)
            except (ModelDiscoveryError, OSError) as exc:
                model_catalog_errors[attempt_key] = sanitize_error(str(exc), [api_key])[:240]
                result["failed"].append(provider_id)
                LOGGER.warning(
                    "Could not refresh the %s model catalog: %s",
                    provider_id,
                    sanitize_error(str(exc), [api_key]),
                )
        return result

    async def refresh_due_documented_catalogs() -> None:
        if os.environ.get("PANTHEON_MODEL_DOCS_SYNC", "1") == "0":
            return
        for provider_id in ("openai", "anthropic"):
            identity = f"{provider_id}:documented"
            cached = read_model_cache().get("catalogs", {}).get(identity, {})
            now = int(time.time())
            if now - int(cached.get("fetched_at") or 0) < MODEL_DOCUMENTED_TTL_SECONDS:
                continue
            if now - model_catalog_attempts.get(identity, 0) < MODEL_CATALOG_CHECK_INTERVAL_SECONDS:
                continue
            model_catalog_attempts[identity] = now
            try:
                models = await discover_documented_models(provider_id)
                write_model_cache(provider_id, "", models, documented=True)
                model_catalog_errors.pop(identity, None)
            except (ModelDiscoveryError, OSError) as exc:
                model_catalog_errors[identity] = str(exc)[:240]
                LOGGER.warning("Could not refresh public %s model recommendations", provider_id)

    async def model_catalog_loop() -> None:
        try:
            while True:
                try:
                    await refresh_due_model_catalogs()
                    await refresh_due_documented_catalogs()
                except Exception:
                    LOGGER.exception("Unexpected model catalog refresh failure")
                await asyncio.sleep(MODEL_CATALOG_CHECK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise

    app.state.refresh_model_catalogs = refresh_due_model_catalogs
    app.state.refresh_documented_catalogs = refresh_due_documented_catalogs
    app.state.model_catalog_attempts = model_catalog_attempts

    def provider_label(provider_key: str) -> str:
        if provider_key == "none":
            return "None"
        return str(SETUP_PROVIDER_PRESETS.get(provider_key, {}).get("label") or provider_key or "Unknown")

    def role_config(config: dict[str, Any], role_name: str) -> dict[str, Any]:
        pantheon_cfg = config.get("pantheon", {}) or {}
        if role_name == "hermes":
            return pantheon_cfg.get("hermes", {}) or {}
        return (pantheon_cfg.get("roles", {}) or {}).get(role_name, {}) or {}

    def role_setup_statuses(config: dict[str, Any]) -> list[dict[str, Any]]:
        config = normalized_config(config)
        providers = config.get("llm_providers", {}) or {}
        statuses: list[dict[str, Any]] = []
        for role_name, label, purpose, counts_toward_ready in SETUP_ROLE_ORDER:
            health = {"state": "not_applicable", "checked_at": None}
            catalog_listed = None
            cfg = role_config(config, role_name)
            adapter = str(cfg.get("provider") or ("none" if role_name == "chronos" else ""))
            model = str(cfg.get("model") or ("none" if role_name == "chronos" else ""))
            enabled = bool(cfg.get("enabled", True))

            if not adapter:
                provider_key = "missing"
                provider_name = "Not configured"
                env_var = ""
                key_configured = False
                requires_key = True
                status = "not_configured"
                status_label = "not configured"
            elif adapter == "none" or role_name == "chronos":
                provider_key = "none"
                provider_name = "None"
                env_var = ""
                key_configured = True
                requires_key = False
                status = "no_key_needed"
                status_label = "no key needed"
            else:
                provider_key = provider_key_from_adapter(adapter, providers)
                preset = SETUP_PROVIDER_PRESETS.get(provider_key, {})
                llm_cfg = (providers.get(adapter, {}) or {})
                raw_api_key = llm_cfg.get("api_key", "")
                env_var = env_var_from_api_key(raw_api_key) or str(preset.get("env_var") or "")
                requires_key = bool(preset.get("requires_key", True))
                key_configured = (
                    not requires_key
                    or bool(env_value(env_var))
                    or (bool(raw_api_key) and "${" not in str(raw_api_key))
                )
                provider_name = provider_label(provider_key)
                status = "ready" if key_configured and enabled else "missing_key"
                status_label = "ready" if key_configured and enabled else "missing key"
                if not enabled:
                    status = "disabled"
                    status_label = "disabled"

                endpoint = str(llm_cfg.get("base_url") or preset.get("base_url") or "")
                key = str(raw_api_key) if raw_api_key and "${" not in str(raw_api_key) else env_value(env_var)
                key = normalized_provider_api_key(provider_key, key)
                health = readiness.health(provider_key, model, endpoint, key)
                catalog = cached_model_catalog(provider_key, endpoint, key)
                if catalog and time.time() - int(catalog.get("fetched_at") or 0) < MODEL_CACHE_TTL_SECONDS:
                    catalog_listed = any(entry.get("id") == model for entry in catalog.get("models", []))
                if key_configured and enabled:
                    status = health["state"]
                    status_label = {"verified": "API verified", "failed": "API test failed",
                                    "expired": "test expired", "untested": "configured · untested"}[status]

            statuses.append({
                "role": role_name,
                "label": label,
                "purpose": purpose,
                "provider": provider_key,
                "provider_label": provider_name,
                "adapter": adapter,
                "model": model,
                "env_var": env_var,
                "requires_key": requires_key,
                "key_configured": key_configured,
                "ready": bool(key_configured and enabled),
                "status": status,
                "status_label": status_label,
                "counts_toward_ready": counts_toward_ready,
                "api_health": health,
                "catalog_listed": catalog_listed,
            })
        return statuses

    def setup_status_payload(message: str = "") -> dict[str, Any]:
        config_file = setup_config_path()
        env_file = setup_env_path()
        config = read_yaml_config(config_file)
        provider_key = provider_from_config(config)
        preset = SETUP_PROVIDER_PRESETS[provider_key]
        adapter = preset["adapter"]
        endpoint, _connection_key = provider_catalog_connection(provider_key, config)
        hermes_cfg = config.get("pantheon", {}).get("hermes", {}) or {}
        env_var = preset["env_var"]
        key_value = env_value(env_var)
        role_statuses = role_setup_statuses(config)
        counted_roles = [item for item in role_statuses if item["counts_toward_ready"]]
        ready_count = sum(1 for item in counted_roles if item["ready"])
        role_count = len(counted_roles)
        provider_labels = {
            item["provider_label"]
            for item in counted_roles
            if item["provider"] not in {"none", "missing"}
        }
        summary_provider = (
            "Mixed providers"
            if len(provider_labels) > 1
            else next(iter(provider_labels), preset["label"])
        )
        setup_ready = bool(role_count and ready_count == role_count)
        verified_count = sum(item["api_health"]["state"] == "verified" for item in counted_roles)
        return {
            "message": message,
            "provider": provider_key,
            "provider_label": preset["label"],
            "adapter": adapter,
            "model": hermes_cfg.get("model") or preset["model"],
            "base_url": endpoint,
            "env_var": env_var,
            "key_configured": bool(key_value) or not preset["requires_key"],
            "masked_key": mask_secret(key_value),
            "requires_key": bool(preset["requires_key"]),
            "config_path": str(config_file),
            "env_path": str(env_file),
            "config_exists": config_file.exists(),
            "env_exists": env_file.exists(),
            "setup_ready": setup_ready,
            "ready_count": ready_count,
            "role_count": role_count,
            "summary_title": f"{summary_provider} · {ready_count}/{role_count} configured · {verified_count} verified",
            "summary_state": "verified" if verified_count == role_count and setup_ready else "configured" if setup_ready else "needs attention",
            "verified_count": verified_count,
            "credentials": workspace_services.credentials.status(),
            "onboarding": onboarding_status(setup_ready, verified_count > 0),
            "role_statuses": role_statuses,
            "providers": [
                provider_status_payload(
                    key,
                    current_provider=provider_key,
                    current_model=str(hermes_cfg.get("model") or ""),
                    config=config,
                )
                for key in SETUP_PROVIDER_PRESETS
            ],
        }

    def onboarding_status(configured: bool, verified: bool) -> dict:
        dismissed = readiness.preference("guide_dismissed", initially_configured)
        return {"show": not dismissed, "workspace": str(workspace_root),
                "steps": {"workspace": bool(readiness.preference("workspace_confirmed", False)),
                          "configured": configured, "verified": verified,
                          "first_task": any(item["status"] == "completed" for item in task_store.list())}}

    def sse(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    app.state.auth_enabled = lambda: auth_config()["enabled"]
    remote_bind = bind_host not in {"127.0.0.1", "localhost", "::1"}
    allowed_hosts = {"127.0.0.1", "localhost", "::1"}
    if bind_host not in {"0.0.0.0", "::"}:
        allowed_hosts.add(bind_host)
    allowed_hosts.update(value.strip().lower() for value in
                         os.environ.get("PANTHEON_ALLOWED_HOSTS", "").split(",") if value.strip())
    terminal_enabled = env_value("PANTHEON_TERMINAL_ENABLED").lower() not in {"0", "false", "no"}
    if remote_bind:
        terminal_enabled = env_value("PANTHEON_TERMINAL_ENABLED").lower() in TRUE_VALUES

    @app.middleware("http")
    async def require_ui_auth(request: Request, call_next):
        if (request.url.hostname or "").lower() not in allowed_hosts:
            return JSONResponse({"detail": "Host is not allowed"}, status_code=400)
        origin = request.headers.get("origin")
        callback_paths = {f'/api/channels/{name}/callback' for name in CHANNELS} | {'/api/channels/webhook'}
        if origin and request.url.path not in callback_paths:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or parsed.netloc != request.headers.get("host"):
                return JSONResponse({"detail": "Cross-origin access is not allowed"}, status_code=403)
        cfg = auth_config()
        if remote_bind and not cfg["enabled"]:
            return JSONResponse({"detail": "Remote access requires configured authentication"}, status_code=403)
        if not cfg["enabled"]:
            return await call_next(request)

        path = request.url.path
        public_paths = {
            "/",
            "/api/auth/status",
            "/api/auth/login",
            "/api/health",
            "/api/channels/webhook",
        }
        if path in public_paths | callback_paths or path.startswith("/static/"):
            return await call_next(request)
        if request_is_authenticated(request):
            return await call_next(request)
        return JSONResponse({"detail": "authentication required"}, status_code=401)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        index_file = STATIC_DIR / "index.html"
        if not index_file.exists():
            return HTMLResponse(
                "<h1>Pantheon Web UI</h1>"
                "<p>Static files missing. Please reinstall the package.</p>",
                status_code=500,
            )
        return HTMLResponse(index_file.read_text(encoding="utf-8"))

    # ----- Local UI authentication -----
    @app.get("/api/auth/status")
    async def auth_status(request: Request) -> dict[str, Any]:
        return auth_status_payload(request)

    @app.post("/api/auth/login")
    async def auth_login(req: AuthLoginRequest, request: Request) -> JSONResponse:
        cfg = auth_config()
        if not cfg["enabled"]:
            return JSONResponse(auth_status_payload(request, "Local login is not enabled."))
        username = req.username.strip()
        if username != cfg["username"] or not password_matches(req.password, cfg):
            raise HTTPException(status_code=401, detail="invalid username or password")
        response = JSONResponse({
            **auth_status_payload(request, "Logged in."),
            "authenticated": True,
        })
        set_auth_cookie(response, cfg["username"], request)
        return response

    @app.post("/api/auth/logout")
    async def auth_logout(request: Request) -> JSONResponse:
        response = JSONResponse({
            **auth_status_payload(request, "Logged out."),
            "authenticated": False,
        })
        clear_auth_cookie(response)
        return response

    @app.post("/api/security/save")
    async def security_save(req: SecuritySaveRequest, request: Request) -> JSONResponse:
        cfg = auth_config()
        if cfg["enabled"] and not request_is_authenticated(request):
            raise HTTPException(status_code=401, detail="authentication required")

        username = normalize_username(req.username or "admin")
        password = (req.password or "").strip()

        if req.enabled:
            if password and len(password) < 8:
                raise HTTPException(status_code=400, detail="password must be at least 8 characters")
            if not password and not cfg["configured"]:
                raise HTTPException(status_code=400, detail="password is required when enabling login")

            write_runtime_env("PANTHEON_UI_AUTH_ENABLED", "true")
            write_runtime_env("PANTHEON_UI_USERNAME", username)
            if password:
                write_runtime_env("PANTHEON_UI_PASSWORD_HASH", hash_password(password))
                write_runtime_env("PANTHEON_UI_PASSWORD", "")
            if not env_value("PANTHEON_UI_SESSION_SECRET"):
                write_runtime_env("PANTHEON_UI_SESSION_SECRET", secrets.token_urlsafe(32))

            response = JSONResponse({
                **auth_status_payload(request, "Local login enabled."),
                "enabled": True,
                "requested_enabled": True,
                "configured": True,
                "authenticated": True,
                "username": username,
            })
            set_auth_cookie(response, username, request)
            return response

        write_runtime_env("PANTHEON_UI_AUTH_ENABLED", "false")
        response = JSONResponse({
            **auth_status_payload(request, "Local login disabled."),
            "enabled": False,
            "requested_enabled": False,
            "authenticated": True,
        })
        clear_auth_cookie(response)
        return response

    # ----- Local setup -----
    @app.get("/api/setup/status")
    async def setup_status() -> dict[str, Any]:
        return setup_status_payload()

    @app.post("/api/setup/models")
    async def setup_models(req: SetupModelsRequest) -> dict[str, Any]:
        provider_id = req.provider.strip().lower()
        if provider_id not in SETUP_PROVIDER_PRESETS:
            raise HTTPException(status_code=400, detail="unsupported provider")

        preset = SETUP_PROVIDER_PRESETS[provider_id]
        saved_url, saved_key = provider_catalog_connection(provider_id, read_yaml_config(setup_config_path()))
        base_url = (req.base_url or saved_url).strip()
        api_key = normalized_provider_api_key(
            provider_id,
            (req.api_key or "").strip() or saved_key,
        )
        current_model = (req.current_model or "").strip()
        if not current_model:
            config = read_yaml_config(setup_config_path())
            if provider_from_config(config) == provider_id:
                current_model = str(
                    (config.get("pantheon", {}).get("hermes", {}) or {}).get("model") or ""
                )

        if preset["requires_key"] and not api_key:
            raise HTTPException(
                status_code=400,
                detail=f"{preset['env_var']} is required to refresh available models.",
            )

        try:
            discovered = await discover_provider_models(
                str(preset.get("discovery_provider") or provider_id),
                base_url,
                api_key,
            )
            cache_entry = write_model_cache(provider_id, base_url, discovered, api_key)
            identity = model_cache_key(provider_id, base_url, api_key)
            model_catalog_errors.pop(identity, None)
            model_catalog_attempts[identity] = int(time.time())
        except (ModelDiscoveryError, OSError) as exc:
            cached = cached_model_catalog(provider_id, base_url, api_key)
            problem = sanitize_error(str(exc), [api_key])
            return {
                "ok": False,
                "message": "Could not refresh models.",
                "problem": problem,
                "preserved_model": current_model,
                "provider": provider_payload(
                    provider_id,
                    current_model=current_model,
                    discovered=cached.get("models") if cached else None,
                    source=(
                        "cache"
                        if cached
                        else "built-in"
                    ),
                    fetched_at=int(cached.get("fetched_at") or 0) if cached else None,
                    base_url=base_url,
                ),
            }

        return {
            "ok": True,
            "message": f"Found {len(discovered)} compatible models.",
            "preserved_model": current_model,
            "provider": provider_payload(
                provider_id,
                current_model=current_model,
                discovered=discovered,
                source="live",
                fetched_at=int(cache_entry["fetched_at"]),
                base_url=base_url,
            ),
        }

    @app.get("/api/info")
    async def app_info() -> dict[str, Any]:
        return {
            "ui_version": app.version,
            "backend_version": app.version,
            "python_version": sys.version.split()[0],
            "workspace_path": str(workspace_root),
            "config_path": str(setup_config_path()),
            "env_path": str(setup_env_path()),
        }

    @app.get("/api/update")
    async def update_status() -> dict[str, Any]:
        return await update_checker.check()

    @app.post("/api/update/check")
    async def update_check_now() -> dict[str, Any]:
        return await update_checker.check(force=True)

    @app.get("/api/conversations")
    async def get_conversations() -> dict[str, Any]:
        try:
            return conversation_store.get()
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=500, detail=f"Conversation store unavailable: {exc}") from exc

    @app.put("/api/conversations")
    async def put_conversations(request: Request) -> dict[str, Any]:
        if int(request.headers.get("content-length", "0") or "0") > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Conversation backup exceeds 10 MB")
        body = await request.body()
        if len(body) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Conversation backup exceeds 10 MB")
        try:
            data = json.loads(body)
            if data.get("schema_version") != 1 or not isinstance(data.get("expected_revision"), str):
                raise ValueError("Unsupported conversation format")
            saved = conversation_store.replace(data.get("sessions"), data["expected_revision"])
        except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if saved is None:
            raise HTTPException(status_code=409, detail="Conversations changed in another tab; refresh and retry")
        return saved

    @app.delete("/api/conversations/{session_id}")
    async def delete_conversation(session_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session_id):
            raise HTTPException(status_code=400, detail="Invalid conversation ID")
        for _ in range(3):
            current = conversation_store.get()
            saved = conversation_store.replace(current["sessions"], current["revision"], deleted_id=session_id)
            if saved is not None:
                return saved
        raise HTTPException(status_code=409, detail="Conversations changed; retry deletion")

    @app.get("/api/tasks")
    async def task_list() -> dict[str, Any]:
        return {"tasks": task_store.list()}

    @app.post("/api/tasks/{task_id}/stop")
    async def task_stop(task_id: str) -> dict[str, Any]:
        return {"stop_requested": task_store.cancel(task_id)}

    @app.get("/api/tasks/{task_id}")
    async def task_details(task_id: str) -> dict[str, Any]:
        result = task_store.get(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return result

    @app.get('/api/tasks/{task_id}/archive')
    async def task_archive(task_id: str):
        path = task_store.archive_path(task_id)
        if task_store.get(task_id) is None or not path.is_file():
            raise HTTPException(404, 'Complete archive is unavailable for this older task')
        return FileResponse(path, media_type='application/json', filename='pantheon-task-' + path.name)

    @app.post('/api/tasks/{task_id}/resume')
    async def resume_task(task_id: str, req: ResumeRequest):
        try:
            result = await asyncio.to_thread(request_pantheon().resume, task_id, acknowledge_effects=req.acknowledge_effects)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {'task_id': result['task_id'], 'status': result.get('status'), 'content': result.get('content'), 'resumed_from': task_id}

    @app.get("/api/runtime")
    async def runtime_info() -> dict[str, Any]:
        return {"workspace": str(workspace_root), "data_directory": str(data_paths.state),
                "config_path": str(setup_config_path()), "legacy_data": data_paths.legacy,
                "host": bind_host, "port": bind_port, "version": __version__}

    @app.get("/api/usage")
    async def usage_summary() -> dict[str, Any]:
        return usage_store.summary()

    @app.get("/api/integrations")
    async def integrations_status() -> dict[str, Any]:
        return integrations_payload()

    # ----- Local Skills and Plugin packs -----
    def prompt_extension_payload(
        store: SkillStore | PluginStore,
        query: str = "",
    ) -> dict[str, Any]:
        return {
            "items": store.list(query=query),
            "roles": sorted(EXTENSION_ROLES),
            "path": str(store.path),
        }

    def save_prompt_extension(
        store: SkillStore | PluginStore,
        req: PromptExtensionRequest,
        item_id: str = "",
    ) -> dict[str, Any]:
        try:
            common = {
                "item_id": item_id,
                "name": req.name,
                "description": req.description,
                "instructions": req.instructions,
                "roles": req.roles,
                "enabled": req.enabled,
                "version": req.version,
            }
            if isinstance(store, SkillStore):
                item = store.save(
                    **common,
                    trigger_terms=req.trigger_terms,
                    kind=req.kind,
                    allow_implicit_invocation=req.allow_implicit_invocation,
                )
            else:
                item = store.save(**common)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"item": item, **prompt_extension_payload(store)}

    @app.get("/api/skills")
    async def skills_list(query: str = "") -> dict[str, Any]:
        return prompt_extension_payload(skill_store, query=query)

    @app.post("/api/skills")
    async def skills_create(req: PromptExtensionRequest) -> dict[str, Any]:
        return save_prompt_extension(skill_store, req)

    @app.put("/api/skills/{skill_id}")
    async def skills_update(skill_id: str, req: PromptExtensionRequest) -> dict[str, Any]:
        if skill_store.get(skill_id) is None:
            raise HTTPException(status_code=404, detail="skill not found")
        return save_prompt_extension(skill_store, req, item_id=skill_id)

    @app.post("/api/skills/{skill_id}/toggle")
    async def skills_toggle(skill_id: str, req: ExtensionToggleRequest) -> dict[str, Any]:
        item = skill_store.set_enabled(skill_id, req.enabled)
        if item is None:
            raise HTTPException(status_code=404, detail="skill not found")
        return {"item": item, **prompt_extension_payload(skill_store)}

    @app.delete("/api/skills/{skill_id}")
    async def skills_delete(skill_id: str) -> dict[str, Any]:
        try:
            if not skill_store.delete(skill_id):
                raise HTTPException(status_code=404, detail="skill not found")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return prompt_extension_payload(skill_store)

    @app.get("/api/plugins")
    async def plugins_list(query: str = "") -> dict[str, Any]:
        return prompt_extension_payload(plugin_store)

    @app.post("/api/plugins")
    async def plugins_create(req: PromptExtensionRequest) -> dict[str, Any]:
        return save_prompt_extension(plugin_store, req)

    @app.put("/api/plugins/{plugin_id}")
    async def plugins_update(plugin_id: str, req: PromptExtensionRequest) -> dict[str, Any]:
        if plugin_store.get(plugin_id) is None:
            raise HTTPException(status_code=404, detail="plugin not found")
        return save_prompt_extension(plugin_store, req, item_id=plugin_id)

    @app.post("/api/plugins/{plugin_id}/toggle")
    async def plugins_toggle(plugin_id: str, req: ExtensionToggleRequest) -> dict[str, Any]:
        item = plugin_store.set_enabled(plugin_id, req.enabled)
        if item is None:
            raise HTTPException(status_code=404, detail="plugin not found")
        return {"item": item, **prompt_extension_payload(plugin_store)}

    @app.delete("/api/plugins/{plugin_id}")
    async def plugins_delete(plugin_id: str) -> dict[str, Any]:
        if not plugin_store.delete(plugin_id):
            raise HTTPException(status_code=404, detail="plugin not found")
        return prompt_extension_payload(plugin_store)

    # ----- MCP servers -----
    @app.get("/api/mcp/servers")
    async def mcp_servers_list() -> dict[str, Any]:
        return mcp_servers_payload()

    @app.post("/api/mcp/servers")
    async def mcp_server_create(req: MCPServerRequest) -> dict[str, Any]:
        try:
            item = save_mcp_request(req)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"item": item, **mcp_servers_payload()}

    @app.put("/api/mcp/servers/{server_id}")
    async def mcp_server_update(server_id: str, req: MCPServerRequest) -> dict[str, Any]:
        if mcp_manager.get(server_id) is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        try:
            item = save_mcp_request(req, server_id=server_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"item": item, **mcp_servers_payload()}

    @app.delete("/api/mcp/servers/{server_id}")
    async def mcp_server_delete(server_id: str) -> dict[str, Any]:
        if not mcp_manager.delete(server_id):
            raise HTTPException(status_code=404, detail="MCP server not found")
        return mcp_servers_payload()

    @app.post("/api/mcp/servers/{server_id}/test")
    async def mcp_server_test(server_id: str) -> dict[str, Any]:
        if mcp_manager.get(server_id) is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        return await asyncio.to_thread(mcp_manager.inspect, server_id)

    @app.put("/api/mcp/servers/{server_id}/tools/{tool_name}/policy")
    async def mcp_tool_policy_update(
        server_id: str,
        tool_name: str,
        req: MCPToolPolicyRequest,
    ) -> dict[str, Any]:
        try:
            item = mcp_manager.set_tool_policy(
                server_id,
                tool_name,
                enabled=req.enabled,
                roles=req.roles,
                approval=req.approval,
            )
        except MCPError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"item": item, **mcp_servers_payload()}

    @app.post("/api/mcp/servers/{server_id}/call")
    async def mcp_server_call(server_id: str, req: MCPToolCallRequest) -> dict[str, Any]:
        try:
            result = await asyncio.to_thread(
                mcp_manager.call_tool,
                server_id,
                req.tool.strip(),
                req.arguments,
            )
        except MCPError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"server_id": server_id, "tool": req.tool, "result": result}

    @app.post("/api/mcp/approvals/{approval_id}")
    async def mcp_approval_decide(
        approval_id: str,
        req: MCPApprovalDecisionRequest,
    ) -> dict[str, Any]:
        with mcp_approval_lock:
            pending = pending_mcp_approvals.get(approval_id)
            if pending is None:
                raise HTTPException(
                    status_code=404,
                    detail="MCP approval request expired or was already resolved",
                )
            pending["approved"] = req.approved
            pending["event"].set()
            payload = dict(pending.get("payload") or {})
        return {
            "ok": True,
            "approved": req.approved,
            "approval": payload,
        }

    # ----- Channels -----
    def webhook_token() -> str:
        return env_value("PANTHEON_WEBHOOK_TOKEN").strip()

    def webhook_payload(token: str = "", reveal_token: bool = False) -> dict[str, Any]:
        current = token or webhook_token()
        return {
            "id": "webhook",
            "enabled": env_value("PANTHEON_WEBHOOK_ENABLED").strip().lower() in TRUE_VALUES,
            "endpoint": "/api/channels/webhook",
            "token_configured": bool(current),
            "token": current if reveal_token else "",
            "token_masked": mask_secret(current),
            "payload": {
                "task": "Your task for Pantheon",
                "mode": "auto",
                "role": "",
            },
        }

    @app.get("/api/channels")
    async def channels_list() -> dict[str, Any]:
        return {'items': [webhook_payload(), *(workspace_services.channels.status(name) for name in CHANNELS)],
                'events': workspace_services.channels.history(), 'path': str(setup_env_path())}

    @app.post("/api/channels/webhook/config")
    async def webhook_config_save(req: WebhookConfigRequest) -> dict[str, Any]:
        current = webhook_token()
        token = req.token.strip() or current
        if req.enabled and (req.rotate_token or not token):
            token = secrets.token_urlsafe(32)
        if req.enabled and not token:
            raise HTTPException(status_code=400, detail="webhook token is required")
        write_runtime_env("PANTHEON_WEBHOOK_ENABLED", "true" if req.enabled else "false")
        if token:
            write_runtime_env("PANTHEON_WEBHOOK_TOKEN", token)
        return webhook_payload(token, reveal_token=True)

    @app.post('/api/channels/{platform}/config')
    async def channel_config(platform: str, value: dict):
        try:
            return workspace_services.channels.save(platform, value.get('config') or {}, value.get('secrets') or {}, storage=str(value.get('storage') or 'env'))
        except (ValueError, CredentialError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post('/api/channels/{platform}/callback')
    async def channel_callback(platform: str, request: Request):
        if platform not in CHANNELS:
            raise HTTPException(404, 'Unknown platform')
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 65536:
                raise HTTPException(413, 'Callback exceeds 64 KiB')
        try:
            return workspace_services.channels.receive(platform, request.headers, bytes(data))
        except ChannelAuthError as exc:
            raise HTTPException(401, str(exc)) from exc
        except ChannelQueueFullError as exc:
            raise HTTPException(429, str(exc)) from exc
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(400, 'Invalid chat callback payload') from exc

    @app.post("/api/channels/webhook")
    async def webhook_receive(request: Request) -> JSONResponse:
        if env_value("PANTHEON_WEBHOOK_ENABLED").strip().lower() not in TRUE_VALUES:
            raise HTTPException(status_code=404, detail="webhook channel is disabled")
        expected = webhook_token()
        authorization = request.headers.get("authorization", "")
        supplied = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
        supplied = supplied or request.headers.get("x-pantheon-webhook-token", "").strip()
        if not expected or not supplied or not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail="invalid webhook token")
        try:
            payload = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="JSON body required") from exc
        task = str(payload.get("task") or payload.get("message") or "").strip()
        if not task:
            raise HTTPException(status_code=400, detail="task or message is required")
        mode = str(payload.get("mode") or "auto")
        role = str(payload.get("role") or "").strip() or None
        result = await asyncio.to_thread(
            ask_with_memory,
            task,
            f"role:{role}" if role else mode,
        )
        steps = [
            {
                "role": getattr(step, "role", "?"),
                "content": getattr(step, "content", ""),
                "success": getattr(step, "success", True),
                "error": getattr(step, "error", None),
                "duration_ms": getattr(step, "duration_ms", 0),
            }
            for step in result.get("steps", [])
        ]
        return JSONResponse({
            "ok": True,
            "mode": result.get("mode", "single"),
            "content": result.get("content", ""),
            "plan": result.get("plan", ""),
            "steps": steps,
            "memory_matches": result.get("memory_matches", []),
        })

    @app.post("/api/setup/check")
    async def setup_check() -> dict[str, Any]:
        status = setup_status_payload()
        problems: list[str] = []
        if not status["config_exists"]:
            problems.append("config/pantheon.yaml does not exist yet.")
        missing_env_vars: set[str] = set()
        for item in status.get("role_statuses", []):
            if item.get("counts_toward_ready") and item.get("requires_key") and not item.get("key_configured"):
                env_var = item.get("env_var") or f"{item.get('provider_label', 'Provider')} API key"
                missing_env_vars.add(str(env_var))
        for env_var in sorted(missing_env_vars):
            problems.append(f"{env_var} is not configured.")
        try:
            if status["config_exists"]:
                Pantheon(
                    config_path=str(setup_config_path()),
                    env_path=str(setup_env_path()),
                )
        except Exception as e:
            problems.append(str(e))
        return {
            **setup_status_payload(
                "Local configuration is valid. Use Test API to check provider access." if not problems else "Config needs attention."
            ),
            "ok": not problems,
            "problems": problems,
        }

    @app.post("/api/setup/test")
    async def setup_test(req: SetupTestRequest) -> dict[str, Any]:
        provider_id = req.provider.strip().lower()
        if provider_id not in SETUP_PROVIDER_PRESETS:
            raise HTTPException(status_code=400, detail="unsupported provider")

        preset = SETUP_PROVIDER_PRESETS[provider_id]
        adapter = str(preset["adapter"])
        env_var = str(preset["env_var"])
        model = req.model.strip() if req.model else str(preset["model"])
        saved_url, saved_key = provider_catalog_connection(provider_id, read_yaml_config(setup_config_path()))
        base_url = (req.base_url or saved_url).strip()
        api_key = normalized_provider_api_key(
            provider_id,
            (req.api_key or "").strip() or saved_key,
        )

        if preset["requires_key"] and not api_key:
            return {
                **setup_status_payload("API test needs an API key."),
                "ok": False,
                "tested": False,
                "problem": f"{env_var} is not configured.",
                "tested_provider": provider_id,
                "tested_model": model,
            }

        def run_test() -> str:
            client = get_llm_client(
                provider=adapter,
                api_key=api_key,
                base_url=base_url,
            )
            client.budget = workspace_services.budget
            client.provider_name = provider_id
            client.usage_recorder = usage_store.record
            return client.complete(
                [{"role": "user", "content": "Reply with exactly: ok"}],
                model=model,
                system="You are testing an API connection. Reply with exactly: ok",
                temperature=0,
                **setup_test_kwargs(adapter, base_url, model),
            )

        started = time.monotonic()
        try:
            response_text = await asyncio.wait_for(
                asyncio.to_thread(run_test),
                timeout=25,
            )
        except Exception as e:
            tested = not isinstance(e, BudgetExceededError)
            if tested:
                readiness.record(provider_id, model, base_url, api_key, False)
            return {
                **setup_status_payload("API test failed."),
                "ok": False,
                "tested": tested,
                "problem": sanitize_error(str(e), [api_key]),
                "tested_provider": provider_id,
                "tested_model": model,
            }

        readiness.record(provider_id, model, base_url, api_key, True)
        return {
            **setup_status_payload("API connection works."),
            "ok": True,
            "tested": True,
            "tested_provider": provider_id,
            "tested_model": model,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "response_preview": sanitize_error(response_text[:120], [api_key]),
        }

    @app.post("/api/onboarding")
    async def update_onboarding(req: OnboardingRequest) -> dict:
        if req.action == "confirm_workspace":
            readiness.set_preference("workspace_confirmed", True)
        elif req.action in {"skip", "reopen"}:
            readiness.set_preference("guide_dismissed", req.action == "skip")
        else:
            raise HTTPException(400, "unknown guide action")
        return setup_status_payload()

    @app.post("/api/credentials/migrate")
    async def migrate_credentials() -> dict:
        try:
            migrated = workspace_services.credentials.migrate()
        except CredentialError as exc:
            raise HTTPException(400, str(exc)) from exc
        reset_pantheon()
        return {**setup_status_payload("Credentials migrated to system storage."), "migrated": migrated}

    @app.get("/api/budgets")
    async def budget_status() -> dict:
        return workspace_services.budget.summary()

    @app.get('/api/media')
    async def media_status():
        get_pantheon()
        return workspace_services.media.status()

    @app.post('/api/media/settings')
    async def save_media_settings(value: dict):
        try:
            return workspace_services.media.save_settings(value)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post('/api/media/upload')
    async def upload_media(request: Request, filename: str):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_INPUT_BYTES:
                raise HTTPException(413, 'File exceeds 24 MiB')
        try:
            return workspace_services.media.upload(filename, bytes(data))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get('/api/media/{media_id}/file')
    async def media_file(media_id: str, download: bool = False):
        try:
            meta, path = workspace_services.media.get(media_id)
            return FileResponse(path, media_type=meta['type'], filename=meta['name'] if download else None,
                                headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store'})
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post('/api/media/generate')
    async def generate_media(value: dict):
        get_pantheon()
        try:
            return await asyncio.to_thread(workspace_services.media.generate_image, str(value.get('prompt') or ''), size=str(value.get('size') or '1024x1024'))
        except (ValueError, BudgetExceededError) as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(502, 'Image provider request failed. Check the API key, model access and provider status.') from exc

    @app.post('/api/media/transcribe')
    async def transcribe_media(value: dict):
        get_pantheon()
        try:
            return await asyncio.to_thread(workspace_services.media.transcribe, str(value.get('id') or ''))
        except (ValueError, BudgetExceededError) as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(502, 'Audio provider request failed. Check the API key, model access and provider status.') from exc

    @app.get('/api/workflow')
    async def workflow_status():
        return workspace_services.workflow_policy()

    @app.post('/api/workflow')
    async def save_workflow(req: WorkflowRequest):
        try:
            value = workspace_services.save_workflow_policy(req.parallel_workers, req.replan_attempts)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        reset_pantheon()
        return value

    @app.post("/api/budgets")
    async def save_budgets(policy: dict) -> dict:
        try:
            workspace_services.budget.save_policy(policy)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return workspace_services.budget.summary()

    @app.post("/api/setup/save")
    async def setup_save(req: SetupSaveRequest) -> dict[str, Any]:
        provider_id = req.provider.strip().lower()
        if provider_id not in SETUP_PROVIDER_PRESETS:
            raise HTTPException(status_code=400, detail="unsupported provider")

        preset = SETUP_PROVIDER_PRESETS[provider_id]
        adapter = str(preset["adapter"])
        env_var = str(preset["env_var"])
        model = req.model.strip() if req.model else str(preset["model"])
        base_url = (req.base_url or str(preset["base_url"])).strip()
        api_key = normalized_provider_api_key(provider_id, req.api_key or "")

        if env_var:
            if api_key:
                try:
                    workspace_services.credentials.save(env_var, api_key, storage=req.credential_storage)
                except CredentialError as exc:
                    raise HTTPException(400, str(exc)) from exc
            else:
                existing_key = env_value(env_var)
                if preset["requires_key"] and not existing_key:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{env_var} is required. Paste the key once, then save.",
                    )

        config_file = setup_config_path()
        config = read_yaml_config(config_file)
        pantheon_cfg = config.setdefault("pantheon", {})
        hermes_cfg = pantheon_cfg.setdefault("hermes", {})
        hermes_cfg["model"] = model
        hermes_cfg["provider"] = adapter
        hermes_cfg['provider_id'] = provider_id
        hermes_cfg.setdefault("temperature", 0.2)
        hermes_cfg.setdefault("max_tokens", 4096)

        if req.apply_to_roles:
            roles_cfg = pantheon_cfg.setdefault("roles", {})
            role_defaults = {
                "hephaestus": {
                    "name": "Hephaestus (锻造之神)",
                    "description": "Writes and refactors code",
                    "temperature": 0.1,
                },
                "athena": {
                    "name": "Athena (智慧之神)",
                    "description": "Researches and gathers information",
                    "temperature": 0.3,
                },
                "apollo": {
                    "name": "Apollo (艺术之神)",
                    "description": "Writes image prompts, lyrics, and storyboards",
                    "temperature": 0.7,
                },
            }
            for role_name in CONFIGURED_ROLE_NAMES:
                role_cfg = roles_cfg.setdefault(role_name, {})
                defaults = role_defaults[role_name]
                role_cfg.setdefault("name", defaults["name"])
                role_cfg.setdefault("description", defaults["description"])
                role_cfg.setdefault("temperature", defaults["temperature"])
                role_cfg.setdefault("tools", [])
                role_cfg.setdefault("enabled", True)
                role_cfg["model"] = model
                role_cfg["provider"] = adapter
                role_cfg['provider_id'] = provider_id
            chronos_cfg = roles_cfg.setdefault("chronos", {})
            chronos_cfg.setdefault("name", "Chronos (时间之神)")
            chronos_cfg.setdefault("description", "Schedules and runs periodic tasks")
            chronos_cfg["model"] = "none"
            chronos_cfg["provider"] = "none"
            chronos_cfg.setdefault("tools", [])
            chronos_cfg.setdefault("enabled", True)

        providers_cfg = config.setdefault("llm_providers", {})
        active_cfg = providers_cfg.setdefault(adapter, {})
        active_cfg["provider_id"] = provider_id
        active_cfg["api_key"] = f"${{{env_var}}}" if env_var else ""
        active_cfg["base_url"] = base_url
        active_cfg["enabled"] = True
        config.setdefault('provider_connections', {})[provider_id] = {
            'base_url': base_url, 'api_key': f'${{{env_var}}}' if env_var else '', 'test_model': model,
        }
        for provider_name in ("openai", "anthropic", "ollama"):
            if provider_name != adapter and provider_name in providers_cfg:
                providers_cfg[provider_name]["enabled"] = False

        config.setdefault("web", {"host": "127.0.0.1", "port": 8000, "reload": False})
        config.setdefault("logging", {
            "level": "INFO",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        })
        write_yaml_config(config_file, config)
        reset_pantheon()
        return setup_status_payload("Saved. Pantheon will use this config on the next request.")

    @app.post('/api/connections/save')
    async def save_connection(req: ConnectionSaveRequest) -> dict:
        provider = req.provider.strip().lower()
        if provider not in SETUP_PROVIDER_PRESETS:
            raise HTTPException(400, 'Unknown provider')
        preset = SETUP_PROVIDER_PRESETS[provider]
        endpoint = (req.base_url or preset['base_url']).strip().rstrip('/')
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HTTPException(400, 'Use an HTTP(S) API base URL without credentials, query or fragment.')
        model = req.model.strip() or preset['model']
        if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', model):
            raise HTTPException(400, 'Provide a valid test model ID')
        key = normalized_provider_api_key(provider, req.api_key or '')
        config_path = setup_config_path()
        with file_mutex(config_path.with_suffix('.lock')):
            config = read_yaml_config(config_path)
            _old_endpoint, old_key = provider_catalog_connection(provider, config)
            if preset['requires_key'] and not key and not old_key:
                raise HTTPException(400, f"Add the {preset['label']} API key before saving.")
            env_var = preset['env_var']
            # A blank edit preserves an existing literal legacy credential too.
            if env_var and (key or old_key):
                try:
                    workspace_services.credentials.save(env_var, key or old_key, storage=req.credential_storage)
                except CredentialError as exc:
                    raise HTTPException(400, str(exc)) from exc
            config.setdefault('provider_connections', {})[provider] = {
                'base_url': endpoint, 'api_key': f'${{{env_var}}}' if env_var else '', 'test_model': model,
            }
            write_yaml_config(config_path, config)
        reset_pantheon()
        return setup_status_payload(f"{preset['label']} connection saved. Role models were not changed.")

    @app.post('/api/models/defaults')
    async def save_default_models(req: DefaultModelsRequest) -> dict:
        required = {'hermes', 'hephaestus', 'athena', 'apollo'}
        if set(req.models) != required:
            raise HTTPException(400, 'Provide a model for each of the four AI roles.')
        config_path = setup_config_path()
        with file_mutex(config_path.with_suffix('.lock')):
            config = read_yaml_config(config_path)
            for name, choice in req.models.items():
                provider, model = choice.get('provider', ''), choice.get('model', '')
                if provider not in SETUP_PROVIDER_PRESETS or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', model):
                    raise HTTPException(400, f'Choose a provider and model for {name}.')
                _endpoint, key = provider_catalog_connection(provider, config)
                if SETUP_PROVIDER_PRESETS[provider]['requires_key'] and not key:
                    raise HTTPException(400, f"Add the {SETUP_PROVIDER_PRESETS[provider]['label']} API key in Connections first.")
            # Pin legacy chats before changing defaults, including chats from other tabs.
            previous = {item['role']: {'provider': item['provider'], 'model': item['model']}
                        for item in role_setup_statuses(config)
                        if item['role'] in required and item['provider'] in SETUP_PROVIDER_PRESETS}
            for _ in range(3):
                snapshot = conversation_store.get()
                sessions = copy.deepcopy(snapshot['sessions'])
                for session in sessions:
                    session['overrides'] = {**previous, **session.get('overrides', {})}
                if sessions == snapshot['sessions']:
                    break
                if conversation_store.replace(sessions, snapshot['revision']) is not None:
                    break
            else:
                raise HTTPException(409, 'Chats changed while saving defaults. Please try again.')
            pantheon = config.setdefault('pantheon', {})
            for name, choice in req.models.items():
                cfg = pantheon.setdefault('hermes', {}) if name == 'hermes' else pantheon.setdefault('roles', {}).setdefault(name, {})
                cfg.update({'provider': choice['provider'], 'provider_id': choice['provider'], 'model': choice['model']})
                provider = choice['provider']
                if provider not in config.get('provider_connections', {}):
                    preset = SETUP_PROVIDER_PRESETS[provider]
                    existing = connection_config(config, provider)
                    endpoint, _key = provider_catalog_connection(provider, config)
                    config.setdefault('provider_connections', {})[provider] = {
                        'base_url': endpoint,
                        'api_key': existing.get('api_key') or (f"${{{preset['env_var']}}}" if preset['env_var'] else ''),
                        'test_model': choice['model'],
                    }
            write_yaml_config(config_path, config)
        reset_pantheon()
        return setup_status_payload('New chat defaults saved. Existing chat model choices were preserved.')

    @app.post('/api/models/status')
    async def current_model_status(req: RoleStatusRequest) -> dict:
        config = normalized_config(read_yaml_config(setup_config_path()))
        for name, choice in req.overrides.items():
            if name not in {'hermes', 'hephaestus', 'athena', 'apollo'}:
                continue
            cfg = role_config(config, name)
            if choice.get('provider') in SETUP_PROVIDER_PRESETS:
                cfg.update({'provider': choice['provider'], 'provider_id': choice['provider']})
            if choice.get('model'):
                cfg['model'] = choice['model']
        return {'role_statuses': role_setup_statuses(config)}

    # ----- Local memory -----
    @app.get("/api/memory")
    async def memory_list(
        query: str = "",
        kind: str = "",
        role: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        if kind and kind not in DEFAULT_MEMORY_KINDS:
            raise HTTPException(status_code=400, detail="unsupported memory kind")
        payload = memory_payload(query=query, kind=kind, role=role)
        if limit != 50:
            payload["items"] = memory_store.list(
                query=query.strip(),
                kind=kind.strip(),
                role=role.strip(),
                limit=limit,
            )
        return payload

    @app.post("/api/memory")
    async def memory_add(req: MemorySaveRequest) -> dict[str, Any]:
        if req.kind not in DEFAULT_MEMORY_KINDS:
            raise HTTPException(status_code=400, detail="unsupported memory kind")
        kind = req.kind
        role = req.role or ""
        if not role and kind == "note":
            kind, role = classify_memory_text(req.content)
        try:
            item = memory_store.add(
                req.content,
                kind=kind,
                source=req.source or "manual",
                role=role,
                tags=req.tags or [],
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        payload = memory_payload()
        payload["item"] = item
        return payload

    @app.post("/api/memory/settings")
    async def memory_settings(req: MemorySettingsRequest) -> dict[str, Any]:
        settings = memory_store.set_settings(
            enabled=req.enabled,
            auto_capture=req.auto_capture,
        )
        payload = memory_payload()
        payload["settings"] = settings
        return payload

    @app.post("/api/memory/suggestions/{suggestion_id}/accept")
    async def memory_accept_suggestion(suggestion_id: str) -> dict[str, Any]:
        try:
            item, suggestion = memory_store.accept_suggestion(suggestion_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail="suggestion not found") from e
        payload = memory_payload()
        payload["item"] = item
        payload["suggestion"] = suggestion
        return payload

    @app.post("/api/memory/suggestions/{suggestion_id}/ignore")
    async def memory_ignore_suggestion(suggestion_id: str) -> dict[str, Any]:
        if not memory_store.ignore_suggestion(suggestion_id):
            raise HTTPException(status_code=404, detail="suggestion not found")
        return memory_payload()

    @app.delete("/api/memory/{memory_id}")
    async def memory_delete(memory_id: str) -> dict[str, Any]:
        if not memory_store.delete(memory_id):
            raise HTTPException(status_code=404, detail="memory not found")
        return memory_payload()

    @app.delete("/api/memory")
    async def memory_clear() -> dict[str, Any]:
        removed = memory_store.clear()
        payload = memory_payload()
        payload["removed"] = removed
        return payload

    # ----- Role listing -----
    @app.get("/api/roles")
    async def list_roles() -> dict[str, Any]:
        try:
            p = get_pantheon()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        roles = []
        configured_providers = p.config.get("llm_providers", {}) or {}
        for name in p.list_roles():
            role = p.get_role(name)
            role_cfg = role_config(p.config, name)
            adapter = str(role_cfg.get("provider") or "")
            provider = provider_key_from_adapter(adapter, configured_providers)
            if not provider:
                # Fall back to model name hints
                m = (getattr(role, "model", "") or "").lower()
                if "claude" in m:
                    provider = "anthropic"
                elif "gpt" in m or "dall" in m or "image" in m:
                    provider = "openai"
                elif "deepseek" in m:
                    provider = "deepseek"
                elif m in ("none", "", "placeholder"):
                    provider = "none"
            # Special-case: Chronos is a scheduling role (no LLM by design)
            note = ""
            if name == "chronos":
                note = "⏰ scheduling role — handles cron / recurring tasks. No LLM by design."
            roles.append({
                "name": name,
                "description": getattr(role, "description", ""),
                "model": getattr(role, "model", ""),
                "provider": provider,
                "note": note,
            })
        return {"roles": roles}

    @app.post("/api/prompt/enhance")
    async def prompt_enhance(req: PromptEnhanceRequest) -> dict[str, str]:
        prompt = req.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")
        if len(prompt) > 12_000:
            raise HTTPException(
                status_code=400,
                detail="prompt is too long to enhance (maximum 12,000 characters)",
            )

        try:
            # Enhancing a draft calls Hermes only. An unrelated role with a
            # missing connection must not block the selected Hermes client.
            overrides = {'hermes': req.overrides['hermes']} if req.overrides and 'hermes' in req.overrides else None
            p = request_pantheon(overrides)
            enhanced = await asyncio.to_thread(p.router.enhance_prompt, prompt, req.mode)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.warning("Prompt enhancement failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail=(
                    "Could not enhance the prompt with the configured Hermes model. "
                    "Check Setup or Test API, then try again."
                ),
            ) from exc
        return {"prompt": enhanced,
                "provider": str(getattr(getattr(p.router, 'llm_client', None), 'provider_name', '') or ''),
                "model": str(getattr(p.router, 'hermes_model', '') or getattr(getattr(p.router, 'llm_client', None), 'default_model', '') or '')}

    # ----- Non-streaming ask (kept for backwards compatibility) -----
    @app.post("/api/ask")
    async def ask(req: AskRequest) -> JSONResponse:
        try:
            get_pantheon()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        mode = req.mode
        if req.role:
            mode = f"role:{req.role}"
        memory_events = process_user_memory(req.user_task or req.task)

        try:
            result = await asyncio.to_thread(
                ask_with_memory, req.task, mode=mode, skill=req.skill, overrides=req.overrides,
                attachments=req.attachments, history=[item.model_dump() for item in req.history]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ask failed: {e}") from e

        # Serialize TaskResult objects
        steps = []
        for s in result.get("steps", []):
            metadata = getattr(s, "metadata", {}) or {}
            steps.append({
                "role": getattr(s, "role", "?"),
                "content": getattr(s, "content", ""),
                "success": getattr(s, "success", True),
                "error": getattr(s, "error", None),
                "duration_ms": getattr(s, "duration_ms", 0),
                "provider": metadata.get("provider", ""),
                "model": metadata.get("model", ""),
                "skills": metadata.get("skill_matches", []),
                "kind": metadata.get("kind", "work"),
                "deliverable": metadata.get("deliverable", ""),
                "acceptance_criteria": metadata.get("acceptance_criteria", []),
                "incoming_messages": metadata.get("incoming_messages", []),
            })

        return JSONResponse({
            "task_id": result.get("task_id"),
            "mode": result.get("mode", "single"),
            "content": result.get("content", ""),
            "plan": result.get("plan", ""),
            "steps": steps,
            "communications": result.get("communications", []),
            "memory_matches": result.get("memory_matches", []),
            "skill_matches": result.get("skill_matches", []),
            "memory_events": memory_events,
        })

    # ----- Streaming ask (SSE) -----
    @app.post("/api/ask/stream")
    async def ask_stream(req: AskRequest):
        """
        Server-Sent Events stream. Emits events:

          event: start
          data: {"task": "...", "mode": "..."}

          event: phase
          data: {"stage": "planning|executing|synthesizing", "role": "hermes", "detail": "..."}

          event: progress
          data: {"stage": "...", "role": "...", "waiting_seconds": 15.0}

          event: plan
          data: {"plan": "...", "steps": [{"role": "athena", "task": "..."}]}

          event: step_start
          data: {"index": 0, "role": "athena"}

          event: step_done
          data: {"index": 0, "role": "athena", "content": "...", "duration_ms": 2300, "success": true}

          event: step_error
          data: {"index": 0, "role": "athena", "error": "..."}

          event: agent_message
          data: {"type": "handoff", "from_role": "athena", "to_role": "hephaestus", "summary": "..."}

          event: summary_start
          data: {}

          event: summary_chunk
          data: {"text": "..."}  (incremental)

          event: summary_done
          data: {"content": "..."}

          event: done
          data: {"mode": "single|multi", "content": "..."}

          event: error
          data: {"message": "..."}
        """
        try:
            p = request_pantheon(req.overrides)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        mode = req.mode
        if req.role:
            mode = f"role:{req.role}"

        async def event_generator():
            # We run Hermes in a thread so the SSE loop stays responsive
            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def emit(event: str, data: dict) -> None:
                if not p.hermes.cancel_event.is_set() and not loop.is_closed():
                    loop.call_soon_threadsafe(queue.put_nowait, (event, data))

            def run_sync() -> None:
                """Run Hermes dispatch with streaming instrumentation."""
                try:
                    from pantheon.core.base import Task
                    workspace_services.media.validate_attachments(req.attachments)
                    task = Task(content=req.task, mode=mode, skill=req.skill, attachments=req.attachments,
                                history=[item.model_dump() for item in req.history])
                    emit("start", {
                        "task_id": task.task_id,
                        "task": req.task,
                        "mode": mode,
                        "requested_skill": req.skill or "",
                    })
                    emit("phase", {
                        "task_id": task.task_id,
                        "stage": "preparing",
                        "role": "hermes",
                        "detail": "Preparing memory, Skills, and task context",
                    })
                    memory_events = process_user_memory(req.user_task or req.task)
                    hermes = p.hermes
                    streamed = {"plan": False, "step": False, "summary": False}

                    def stream_event(event: str, data: dict[str, Any]) -> None:
                        payload = dict(data)
                        if event == "plan_start":
                            emit("phase", {
                                "stage": "planning",
                                "task_id": payload.get("task_id"),
                                "role": payload.get("role", "hermes"),
                                "detail": payload.get("description") or "Building the execution plan",
                            })
                        elif event == "plan_ready":
                            streamed["plan"] = True
                            emit("plan", payload)
                        elif event == "step_start":
                            streamed["step"] = True
                            emit("phase", {
                                "stage": "executing",
                                "task_id": payload.get("task_id"),
                                "role": payload.get("role", ""),
                                "detail": payload.get("task") or payload.get("description") or "Working",
                                "index": payload.get("index", 0),
                                "total": payload.get("total", 1),
                            })
                            emit("step_start", payload)
                        elif event == "step_done":
                            content = str(payload.get("content") or "")
                            if content:
                                emit("step_chunk", {
                                    "index": payload.get("index", 0),
                                    "role": payload.get("role", ""),
                                    "text": content,
                                })
                            emit("step_done", payload)
                        elif event == "step_error":
                            emit("step_error", payload)
                        elif event == "summary_start":
                            streamed["summary"] = True
                            emit("phase", {
                                "stage": "synthesizing",
                                "role": "hermes",
                                "detail": payload.get("description") or "Preparing the final answer",
                            })
                            emit("summary_start", payload)
                        elif event == "summary_done":
                            content = str(payload.get("content") or "")
                            if content:
                                emit("summary_chunk", {"text": content})
                            emit("summary_done", payload)
                        else:
                            emit(event, payload)

                    stream_event.cancel_event = p.hermes.cancel_event
                    result = (p.resume(req.resume_task_id, acknowledge_effects=req.acknowledge_effects, on_event=stream_event)
                              if req.resume_task_id else hermes.dispatch(task, on_event=stream_event))
                    memory_matches = result.get("memory_matches", [])
                    maybe_auto_capture_memory(req.task, result, mode)

                    # Validation failures and custom Hermes implementations may not
                    # emit callbacks. Keep the stream useful in that case.
                    if not streamed["plan"]:
                        emit("plan", {
                            "plan": result.get("plan", ""),
                            "mode": result.get("mode", "single"),
                            "memory_count": len(memory_matches),
                            "skills": result.get("skill_matches", []),
                        })
                    if not streamed["step"] and result.get("content"):
                        fallback_role = (
                            mode.replace("role:", "")
                            if mode.startswith("role:")
                            else "hermes"
                        )
                        fallback = {
                            "index": 0,
                            "total": 1,
                            "role": fallback_role,
                            "task": req.task,
                            "content": result.get("content", ""),
                            "duration_ms": 0,
                            "success": True,
                            "skills": result.get("skill_matches", []),
                        }
                        emit("step_start", fallback)
                        emit("step_chunk", {
                            "index": 0,
                            "role": fallback_role,
                            "text": result.get("content", ""),
                        })
                        emit("step_done", fallback)

                    emit("done", {
                        "mode": result.get("mode", "single"),
                        "content": result.get("content", ""),
                        "success": result.get("success", True),
                        "status": result.get("status", "completed"),
                        "skills": result.get("skill_matches", []),
                        "memory_count": len(memory_matches),
                        "memory_saved_count": len(memory_events["saved"]),
                        "memory_suggestion_count": len(memory_events["suggestions"]),
                    })

                except Exception as e:
                    emit("error", {"message": str(e)})
                finally:
                    if not p.hermes.cancel_event.is_set() and not loop.is_closed():
                        loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

            # Run the blocking work in a thread
            fut = loop.run_in_executor(None, run_sync)

            # Drain the queue, yielding SSE-formatted lines
            stream_started = time.monotonic()
            phase_started = stream_started
            last_heartbeat = stream_started
            live_phase: dict[str, Any] = {
                "stage": "connecting",
                "role": "hermes",
                "detail": "Connecting to Pantheon",
            }
            try:
                while True:
                    try:
                        item = await asyncio.wait_for(
                            queue.get(),
                            timeout=min(1.0, STREAM_HEARTBEAT_SECONDS),
                        )
                    except asyncio.TimeoutError:
                        now = time.monotonic()
                        if now >= p.hermes.deadline:
                            yield 'event: error\ndata: {"message": "Task exceeded its 10 minute execution budget"}\n\n'
                            return
                        if now - last_heartbeat >= STREAM_HEARTBEAT_SECONDS:
                            progress = {
                                **live_phase,
                                "elapsed_seconds": round(now - stream_started, 1),
                                "waiting_seconds": round(now - phase_started, 1),
                            }
                            yield (
                                "event: progress\n"
                                f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
                            )
                            last_heartbeat = now
                        continue
                    if item is None:
                        break
                    event, data = item
                    if event == "phase":
                        live_phase = dict(data)
                        phase_started = time.monotonic()
                        last_heartbeat = phase_started
                    elif event == "step_start":
                        live_phase = {
                            "stage": "executing",
                            "role": data.get("role", ""),
                            "detail": data.get("task") or data.get("description") or "Working",
                            "index": data.get("index", 0),
                            "total": data.get("total", 1),
                        }
                        phase_started = time.monotonic()
                        last_heartbeat = phase_started
                    elif event == "summary_start":
                        live_phase = {
                            "stage": "synthesizing",
                            "role": "hermes",
                            "detail": data.get("description") or "Preparing the final answer",
                        }
                        phase_started = time.monotonic()
                        last_heartbeat = phase_started
                    yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

                # Ensure the executor finished (no exception swallowed)
                try:
                    await fut
                except Exception as e:
                    yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            finally:
                p.hermes.cancel_event.set()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # for nginx compat
            },
        )

    # ----- Local workspace tools -----
    @app.get("/api/workspace")
    async def workspace_info() -> dict[str, Any]:
        return {
            "root": str(workspace_root),
            "name": workspace_root.name,
            "path": "",
            "terminal": terminal_enabled,
        }

    @app.get("/api/workspace/files")
    async def list_workspace_files(path: str = "") -> dict[str, Any]:
        target = resolve_workspace_path(path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="path not found")
        if not target.is_dir():
            raise HTTPException(status_code=400, detail="path is not a directory")
        return {
            "root": str(workspace_root),
            "cwd": relative_workspace_path(target),
            "parent": relative_workspace_path(target.parent) if target != workspace_root else None,
            "items": workspace_items(target),
        }

    @app.get("/api/workspace/file")
    async def read_workspace_file(path: str) -> dict[str, Any]:
        target = resolve_workspace_path(path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="file not found")
        if not target.is_file():
            raise HTTPException(status_code=400, detail="path is not a file")

        size = target.stat().st_size
        if size > MAX_WORKSPACE_FILE_BYTES:
            raise HTTPException(status_code=413, detail="file is too large to preview")

        raw = target.read_bytes()
        try:
            content = raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            content = raw.decode("utf-8", errors="replace")
            encoding = "binary-replaced"

        return {
            "name": target.name,
            "path": relative_workspace_path(target),
            "size": size,
            "modified": target.stat().st_mtime,
            "encoding": encoding,
            "previewable": target.suffix.lower() in HTML_SUFFIXES,
            "content": content,
        }

    @app.post("/api/workspace/file")
    async def save_workspace_file(req: WorkspaceFileSaveRequest) -> dict[str, Any]:
        raw_path = (req.path or "").strip()
        if not raw_path:
            raise HTTPException(status_code=400, detail="path is required")
        if raw_path.endswith("/"):
            raise HTTPException(status_code=400, detail="path must point to a file")

        target = resolve_workspace_path(raw_path)
        if target.exists() and target.is_dir():
            raise HTTPException(status_code=400, detail="path is a directory")
        if target.exists() and not req.overwrite:
            raise HTTPException(status_code=409, detail="file already exists")

        raw = req.content.encode("utf-8")
        if len(raw) > MAX_WORKSPACE_FILE_BYTES:
            raise HTTPException(status_code=413, detail="file is too large to save")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        stat = target.stat()
        return {
            "name": target.name,
            "path": relative_workspace_path(target),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "encoding": "utf-8",
            "previewable": target.suffix.lower() in HTML_SUFFIXES,
        }

    @app.get("/api/workspace/preview", response_class=HTMLResponse)
    async def preview_workspace_file(path: str) -> HTMLResponse:
        target = resolve_workspace_path(path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="file not found")
        if not target.is_file() or target.suffix.lower() not in HTML_SUFFIXES:
            raise HTTPException(status_code=400, detail="path is not an HTML file")
        if target.stat().st_size > MAX_WORKSPACE_FILE_BYTES:
            raise HTTPException(status_code=413, detail="file is too large to preview")

        return HTMLResponse(
            target.read_text(encoding="utf-8", errors="replace"),
            headers={
                "Content-Security-Policy": (
                    "sandbox allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox; "
                    "default-src 'self' data: blob: https: http:; "
                    "img-src 'self' data: blob: https: http:; "
                    "style-src 'self' 'unsafe-inline' https: http:; "
                    "script-src 'self' 'unsafe-inline' https: http:"
                )
            },
        )

    @app.post("/api/workspace/terminal/stream")
    async def terminal_stream(req: TerminalRequest):
        if not terminal_enabled:
            raise HTTPException(status_code=403, detail="Terminal execution is disabled by the server")
        command = req.command.strip()
        if not command:
            raise HTTPException(status_code=400, detail="command is required")
        if len(command) > 2000:
            raise HTTPException(status_code=400, detail="command is too long")

        cwd = resolve_workspace_path(req.cwd)
        if not cwd.exists() or not cwd.is_dir():
            raise HTTPException(status_code=400, detail="cwd is not a directory")
        timeout = max(1, min(req.timeout_seconds, 600))

        if os.name == 'nt':
            from pantheon.web.windows_terminal import command_events
            async def windows_generator():
                async for event, payload in command_events(command, cwd, timeout):
                    payload['cwd'] = relative_workspace_path(cwd)
                    yield sse(event, payload)
            return StreamingResponse(windows_generator(), media_type='text/event-stream',
                                     headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

        async def event_generator():
            queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
            proc: asyncio.subprocess.Process | None = None
            tasks: list[asyncio.Task] = []

            async def pump(reader: asyncio.StreamReader | None, event: str) -> None:
                if reader is None:
                    return
                while True:
                    chunk = await reader.read(4096)
                    if not chunk:
                        break
                    await queue.put((event, {"text": chunk.decode("utf-8", errors="replace")}))

            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(cwd),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "TERM": "dumb"},
                    start_new_session=True,
                )
                yield sse("start", {
                    "command": command,
                    "cwd": relative_workspace_path(cwd),
                    "pid": proc.pid,
                })

                stdout_task = asyncio.create_task(pump(proc.stdout, "stdout"))
                stderr_task = asyncio.create_task(pump(proc.stderr, "stderr"))
                wait_task = asyncio.create_task(proc.wait())
                tasks = [stdout_task, stderr_task, wait_task]
                deadline = asyncio.get_running_loop().time() + timeout

                while True:
                    if asyncio.get_running_loop().time() > deadline and wait_task.done() is False:
                        os.killpg(proc.pid, signal.SIGKILL)
                        yield sse("error", {"message": f"command timed out after {timeout}s"})
                        break

                    if wait_task.done() and stdout_task.done() and stderr_task.done() and queue.empty():
                        break

                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    except asyncio.TimeoutError:
                        continue
                    if item is None:
                        continue
                    event, data = item
                    yield sse(event, data)

                await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
                return_code = await wait_task
                yield sse("exit", {
                    "returncode": return_code,
                    "cwd": relative_workspace_path(cwd),
                })
            except Exception as e:
                if proc and proc.returncode is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                yield sse("error", {"message": str(e)})
            finally:
                if proc is not None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    await proc.wait()
                for task in tasks:
                    task.cancel()
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # ----- Chronos local scheduler -----
    @app.get("/api/chronos/jobs")
    async def chronos_jobs() -> dict[str, Any]:
        return {
            "store_path": str(chronos_scheduler.store_path),
            "jobs": chronos_scheduler.list_jobs(),
            "runs": chronos_scheduler.list_runs(limit=12),
        }

    @app.post("/api/chronos/jobs")
    async def chronos_create_job(req: ChronosScheduleRequest) -> dict[str, Any]:
        try:
            spec = parse_schedule_request(req.text)
            job = chronos_scheduler.add_job(spec)
        except ScheduleParseError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {
            "job": job,
            "jobs": chronos_scheduler.list_jobs(),
            "runs": chronos_scheduler.list_runs(limit=12),
        }

    @app.post("/api/chronos/jobs/{job_id}/pause")
    async def chronos_pause_job(job_id: str) -> dict[str, Any]:
        try:
            job = chronos_scheduler.set_enabled(job_id, False)
        except KeyError as e:
            raise HTTPException(status_code=404, detail="job not found") from e
        return {"job": job, "jobs": chronos_scheduler.list_jobs()}

    @app.post("/api/chronos/jobs/{job_id}/resume")
    async def chronos_resume_job(job_id: str) -> dict[str, Any]:
        try:
            job = chronos_scheduler.set_enabled(job_id, True)
        except KeyError as e:
            raise HTTPException(status_code=404, detail="job not found") from e
        return {"job": job, "jobs": chronos_scheduler.list_jobs()}

    @app.delete("/api/chronos/jobs/{job_id}")
    async def chronos_delete_job(job_id: str) -> dict[str, Any]:
        if not chronos_scheduler.delete_job(job_id):
            raise HTTPException(status_code=404, detail="job not found")
        return {"jobs": chronos_scheduler.list_jobs(), "runs": chronos_scheduler.list_runs(limit=12)}

    @app.post("/api/chronos/jobs/{job_id}/run")
    async def chronos_run_job(job_id: str) -> dict[str, Any]:
        job = chronos_scheduler.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        await execute_chronos_job(job)
        return {
            "job": chronos_scheduler.get_job(job_id),
            "jobs": chronos_scheduler.list_jobs(),
            "runs": chronos_scheduler.list_runs(job_id=job_id, limit=12),
        }

    # ----- Health -----
    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
