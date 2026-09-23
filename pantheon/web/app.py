"""FastAPI app serving the Pantheon Web UI."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pantheon import __version__
from pantheon.core.extensions import (
    EXTENSION_ROLES,
    MCPError,
    MCPManager,
    PluginStore,
    SkillStore,
    mcp_available,
)
from pantheon.core.memory import (
    DEFAULT_MEMORY_KINDS,
    DEFAULT_MEMORY_ROLES,
    MemoryStore,
    classify_memory_text,
    detect_memory_candidate,
    normalize_memory_role,
)
from pantheon.core.pantheon import Pantheon
from pantheon.core.scheduler import ChronosScheduler, ScheduleParseError, parse_schedule_request
from pantheon.llm import get_llm_client
from pantheon.llm.openai_client import is_responses_api_model
from pantheon.web.model_catalog import ModelDiscoveryError, discover_provider_models

STATIC_DIR = Path(__file__).parent / "static"
STREAM_HEARTBEAT_SECONDS = 5.0
MODEL_CACHE_TTL_SECONDS = 24 * 60 * 60
MODEL_CATALOG_CHECK_INTERVAL_SECONDS = 60 * 60
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


class AskRequest(BaseModel):
    task: str
    user_task: str | None = None
    mode: str = "auto"          # "auto" | "role:<name>" | "multi"
    role: str | None = None     # convenience: --role foo → mode = "role:foo"
    skill: str | None = None    # optional explicit installed skill id
    overrides: dict[str, dict[str, str]] | None = None  # {role_name: {provider, model}}


class PromptEnhanceRequest(BaseModel):
    prompt: str
    mode: str = "auto"


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


class SetupTestRequest(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None


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
            {"id": "claude-opus-5-5", "label": "Claude Opus 5.5"},
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


def create_app(config_path: str | None = None) -> FastAPI:
    """Build the FastAPI app. Pantheon instance is created lazily."""
    _pantheon: dict[str, Pantheon | None] = {"instance": None}
    workspace_root = Path(os.environ.get("PANTHEON_WORKSPACE", Path.cwd())).resolve()
    chronos_scheduler = ChronosScheduler(workspace_root / ".pantheon" / "chronos_jobs.json")
    memory_store = MemoryStore(workspace_root / ".pantheon" / "memory.sqlite")
    skill_store = SkillStore(
        workspace_root / ".pantheon" / "skills",
        legacy_path=workspace_root / ".pantheon" / "skills.json",
    )
    plugin_store = PluginStore(workspace_root / ".pantheon" / "plugins.json")
    mcp_manager = MCPManager(workspace_root / ".pantheon" / "mcp_servers.json")
    mcp_approval_lock = threading.Lock()
    pending_mcp_approvals: dict[str, dict[str, Any]] = {}
    chronos_runner: dict[str, asyncio.Task | None] = {"task": None}
    chronos_job_tasks: set[asyncio.Task[None]] = set()
    model_catalog_runner: dict[str, asyncio.Task | None] = {"task": None}
    model_catalog_attempts: dict[str, int] = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if chronos_runner["task"] is None or chronos_runner["task"].done():
            chronos_runner["task"] = asyncio.create_task(chronos_loop())
        if model_catalog_runner["task"] is None or model_catalog_runner["task"].done():
            model_catalog_runner["task"] = asyncio.create_task(model_catalog_loop())
        try:
            yield
        finally:
            runner_tasks = [
                chronos_runner.get("task"),
                model_catalog_runner.get("task"),
            ]
            for task in runner_tasks:
                if task is None:
                    continue
                task.cancel()
            for task in runner_tasks:
                if task is None:
                    continue
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            active_jobs = tuple(chronos_job_tasks)
            for job_task in active_jobs:
                job_task.cancel()
            if active_jobs:
                await asyncio.gather(*active_jobs, return_exceptions=True)
            chronos_job_tasks.clear()
            chronos_runner["task"] = None
            model_catalog_runner["task"] = None

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
            resolved = approval_event.wait(timeout=120)
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
                    if item.get("enabled", True) and item.get("last_test", {}).get("ok")
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
                "extension_state_path": str((workspace_root / ".pantheon").resolve()),
            },
        }

    def process_user_memory(user_text: str) -> dict[str, list[dict[str, Any]]]:
        detected = detect_memory_candidate(user_text)
        if not detected:
            return {"saved": [], "suggestions": []}
        if detected["action"] == "save":
            item = memory_store.add(
                detected["content"],
                kind=detected["kind"],
                source=detected["source"],
                role=detected["role"],
            )
            return {"saved": [item], "suggestions": []}
        suggestion = memory_store.suggest(
            detected["content"],
            kind=detected["kind"],
            source=detected["source"],
            role=detected["role"],
            reason=detected["reason"],
        )
        suggestions = [suggestion] if suggestion.get("status") == "pending" else []
        return {"saved": [], "suggestions": suggestions}

    def maybe_auto_capture_memory(task: str, result: dict[str, Any], mode: str) -> None:
        settings = memory_store.settings()
        if not settings["enabled"] or not settings["auto_capture"]:
            return
        content = str(result.get("content") or "").strip()
        if not task.strip() or not content:
            return
        if mode.startswith("role:chronos"):
            return
        compact_content = re.sub(r"\s+", " ", content)
        summary = (
            f"Task: {task.strip()[:500]}\n"
            f"Result: {compact_content[:1000]}"
        )
        memory_store.add(summary, kind="task", source="auto", role=normalize_memory_role(mode))

    def ask_with_memory(
        content: str,
        mode: str,
        skill: str | None = None,
    ) -> dict[str, Any]:
        result = get_pantheon().ask(content, mode=mode, skill=skill)
        result["memory_matches"] = result.get("memory_matches", [])
        result["skill_matches"] = result.get("skill_matches", [])
        maybe_auto_capture_memory(content, result, mode)
        return result

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
        return (workspace_root / "config" / "pantheon.yaml").resolve()

    def setup_env_path() -> Path:
        return (workspace_root / ".env").resolve()

    def setup_model_cache_path() -> Path:
        return (workspace_root / ".pantheon" / "model_catalog.json").resolve()

    def read_yaml_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def write_yaml_config(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

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
    ) -> dict[str, Any]:
        path = setup_model_cache_path()
        payload = read_model_cache()
        fetched_at = int(time.time())
        entry = {
            "provider": provider_id,
            "fetched_at": fetched_at,
            "models": models,
        }
        payload["version"] = MODEL_CACHE_VERSION
        payload.setdefault("catalogs", {})[
            model_cache_key(provider_id, base_url, api_key)
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
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        new_line = format_env_line(key, value)
        replaced = False
        next_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                current_key = stripped.split("=", 1)[0].strip()
                if current_key == key:
                    next_lines.append(new_line)
                    replaced = True
                    continue
            next_lines.append(line)
        if not replaced:
            if next_lines and next_lines[-1].strip():
                next_lines.append("")
            next_lines.append(new_line)
        path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")

    def env_value(env_var: str) -> str:
        if not env_var:
            return ""
        return parse_env_file(setup_env_path()).get(env_var) or os.environ.get(env_var, "")

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
        return {
            "id": provider_id,
            "label": preset["label"],
            "model": preset["model"],
            "models": merged_model_catalog(provider_id, discovered, current_model),
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
        base_url = str(preset["base_url"])
        raw_api_key = ""
        if provider_id == current_provider:
            adapter = str(preset["adapter"])
            llm_cfg = (config.get("llm_providers", {}) or {}).get(adapter, {}) or {}
            base_url = str(llm_cfg.get("base_url") or base_url)
            raw_api_key = str(llm_cfg.get("api_key") or "")
        env_var = env_var_from_api_key(raw_api_key) or str(preset.get("env_var") or "")
        api_key = env_value(env_var)
        if not api_key and raw_api_key and "${" not in raw_api_key:
            api_key = raw_api_key
        key_configured = not preset["requires_key"] or bool(api_key)
        cached = cached_model_catalog(provider_id, base_url, api_key)
        return provider_payload(
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

    def provider_key_from_adapter(provider: str, providers: dict[str, Any]) -> str:
        if not provider or provider == "none":
            return "none"
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

    def configured_model_catalogs() -> list[dict[str, str]]:
        config = read_yaml_config(setup_config_path())
        providers = config.get("llm_providers", {}) or {}
        catalogs: list[dict[str, str]] = []
        for adapter, raw_config in providers.items():
            if not isinstance(raw_config, dict):
                continue
            provider_id = provider_key_from_adapter(str(adapter), providers)
            preset = SETUP_PROVIDER_PRESETS.get(provider_id)
            if not preset:
                continue
            base_url = str(raw_config.get("base_url") or preset["base_url"]).strip()
            if not official_catalog_base_url(provider_id, base_url):
                continue
            raw_api_key = str(raw_config.get("api_key") or "")
            env_var = env_var_from_api_key(raw_api_key) or str(preset.get("env_var") or "")
            api_key = env_value(env_var)
            if not api_key and raw_api_key and "${" not in raw_api_key:
                api_key = raw_api_key
            api_key = normalized_provider_api_key(provider_id, api_key)
            if preset["requires_key"] and not api_key:
                continue
            catalogs.append({
                "provider": provider_id,
                "discovery_provider": str(
                    preset.get("discovery_provider") or provider_id
                ),
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
                result["refreshed"].append(provider_id)
            except (ModelDiscoveryError, OSError) as exc:
                result["failed"].append(provider_id)
                LOGGER.warning(
                    "Could not refresh the %s model catalog: %s",
                    provider_id,
                    sanitize_error(str(exc), [api_key]),
                )
        return result

    async def model_catalog_loop() -> None:
        try:
            while True:
                try:
                    await refresh_due_model_catalogs()
                except Exception:
                    LOGGER.exception("Unexpected model catalog refresh failure")
                await asyncio.sleep(MODEL_CATALOG_CHECK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise

    app.state.refresh_model_catalogs = refresh_due_model_catalogs
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
        providers = config.get("llm_providers", {}) or {}
        statuses: list[dict[str, Any]] = []
        for role_name, label, purpose, counts_toward_ready in SETUP_ROLE_ORDER:
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
            })
        return statuses

    def setup_status_payload(message: str = "") -> dict[str, Any]:
        config_file = setup_config_path()
        env_file = setup_env_path()
        config = read_yaml_config(config_file)
        provider_key = provider_from_config(config)
        preset = SETUP_PROVIDER_PRESETS[provider_key]
        adapter = preset["adapter"]
        llm_cfg = (config.get("llm_providers", {}) or {}).get(adapter, {}) or {}
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
        return {
            "message": message,
            "provider": provider_key,
            "provider_label": preset["label"],
            "adapter": adapter,
            "model": hermes_cfg.get("model") or preset["model"],
            "base_url": llm_cfg.get("base_url") or preset["base_url"],
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
            "summary_title": f"{summary_provider} · {ready_count}/{role_count} ready",
            "summary_state": "ready" if setup_ready else "needs attention",
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

    def sse(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    @app.middleware("http")
    async def require_ui_auth(request: Request, call_next):
        cfg = auth_config()
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
        if path in public_paths or path.startswith("/static/"):
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
        base_url = (req.base_url or str(preset["base_url"])).strip()
        api_key = normalized_provider_api_key(
            provider_id,
            (req.api_key or "").strip() or env_value(str(preset["env_var"])),
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
        return {"items": [webhook_payload()], "path": str(setup_env_path())}

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
                "Config looks ready." if not problems else "Config needs attention."
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
        base_url = (req.base_url or str(preset["base_url"])).strip()
        api_key = normalized_provider_api_key(
            provider_id,
            (req.api_key or "").strip() or env_value(env_var),
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
            return {
                **setup_status_payload("API test failed."),
                "ok": False,
                "tested": True,
                "problem": sanitize_error(str(e), [api_key]),
                "tested_provider": provider_id,
                "tested_model": model,
            }

        return {
            **setup_status_payload("API connection works."),
            "ok": True,
            "tested": True,
            "tested_provider": provider_id,
            "tested_model": model,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "response_preview": sanitize_error(response_text[:120], [api_key]),
        }

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
        env_file = setup_env_path()

        if env_var:
            if api_key:
                write_env_value(env_file, env_var, api_key)
                os.environ[env_var] = api_key
            else:
                existing_key = env_value(env_var)
                if preset["requires_key"] and not existing_key:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{env_var} is required. Paste the key once, then save.",
                    )
                if existing_key:
                    os.environ[env_var] = existing_key

        config_file = setup_config_path()
        config = read_yaml_config(config_file)
        pantheon_cfg = config.setdefault("pantheon", {})
        hermes_cfg = pantheon_cfg.setdefault("hermes", {})
        hermes_cfg["model"] = model
        hermes_cfg["provider"] = adapter
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
                    "description": "Generates images, audio, video",
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
            chronos_cfg = roles_cfg.setdefault("chronos", {})
            chronos_cfg.setdefault("name", "Chronos (时间之神)")
            chronos_cfg.setdefault("description", "Schedules and runs periodic tasks")
            chronos_cfg["model"] = "none"
            chronos_cfg["provider"] = "none"
            chronos_cfg.setdefault("tools", [])
            chronos_cfg.setdefault("enabled", True)

        providers_cfg = config.setdefault("llm_providers", {})
        active_cfg = providers_cfg.setdefault(adapter, {})
        active_cfg["api_key"] = f"${{{env_var}}}" if env_var else ""
        active_cfg["base_url"] = base_url
        active_cfg["enabled"] = True
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
            p = get_pantheon()
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
        return {"prompt": enhanced}

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
            result = ask_with_memory(req.task, mode=mode, skill=req.skill)
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
                "skills": metadata.get("skill_matches", []),
                "kind": metadata.get("kind", "work"),
                "deliverable": metadata.get("deliverable", ""),
                "acceptance_criteria": metadata.get("acceptance_criteria", []),
                "incoming_messages": metadata.get("incoming_messages", []),
            })

        return JSONResponse({
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
            p = get_pantheon()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        mode = req.mode
        if req.role:
            mode = f"role:{req.role}"

        # Apply UI overrides (settings panel): change model on the role's llm client.
        if req.overrides:
            for role_name, override in req.overrides.items():
                try:
                    role = p.get_role(role_name)
                except Exception:
                    continue
                provider_id = str(override.get("provider") or "").strip().lower()
                if provider_id in SETUP_PROVIDER_PRESETS:
                    preset = SETUP_PROVIDER_PRESETS[provider_id]
                    adapter = str(preset["adapter"])
                    api_key = env_value(str(preset.get("env_var") or ""))
                    try:
                        role.llm_client = get_llm_client(
                            provider=adapter,
                            api_key=api_key,
                            base_url=str(preset.get("base_url") or "") or None,
                        )
                    except Exception:
                        pass
                if "model" in override and override["model"]:
                    try:
                        role.model = override["model"]
                    except Exception:
                        pass

        async def event_generator():
            # We run Hermes in a thread so the SSE loop stays responsive
            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def emit(event: str, data: dict) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, (event, data))

            def run_sync() -> None:
                """Run Hermes dispatch with streaming instrumentation."""
                try:
                    from pantheon.core.base import Task
                    emit("start", {
                        "task": req.task,
                        "mode": mode,
                        "requested_skill": req.skill or "",
                    })
                    emit("phase", {
                        "stage": "preparing",
                        "role": "hermes",
                        "detail": "Preparing memory, Skills, and task context",
                    })
                    memory_events = process_user_memory(req.user_task or req.task)
                    task = Task(content=req.task, mode=mode, skill=req.skill)
                    hermes = p.hermes
                    streamed = {"plan": False, "step": False, "summary": False}

                    def stream_event(event: str, data: dict[str, Any]) -> None:
                        payload = dict(data)
                        if event == "plan_start":
                            emit("phase", {
                                "stage": "planning",
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

                    result = hermes.dispatch(task, on_event=stream_event)
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
                        "skills": result.get("skill_matches", []),
                        "memory_count": len(memory_matches),
                        "memory_saved_count": len(memory_events["saved"]),
                        "memory_suggestion_count": len(memory_events["suggestions"]),
                    })

                except Exception as e:
                    emit("error", {"message": str(e)})
                finally:
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
            while True:
                try:
                    item = await asyncio.wait_for(
                        queue.get(),
                        timeout=min(1.0, STREAM_HEARTBEAT_SECONDS),
                    )
                except asyncio.TimeoutError:
                    now = time.monotonic()
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
            "terminal": True,
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
        command = req.command.strip()
        if not command:
            raise HTTPException(status_code=400, detail="command is required")
        if len(command) > 2000:
            raise HTTPException(status_code=400, detail="command is too long")

        cwd = resolve_workspace_path(req.cwd)
        if not cwd.exists() or not cwd.is_dir():
            raise HTTPException(status_code=400, detail="cwd is not a directory")
        timeout = max(1, min(req.timeout_seconds, 600))

        async def event_generator():
            queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
            proc: asyncio.subprocess.Process | None = None

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
                )
                yield sse("start", {
                    "command": command,
                    "cwd": relative_workspace_path(cwd),
                    "pid": proc.pid,
                })

                stdout_task = asyncio.create_task(pump(proc.stdout, "stdout"))
                stderr_task = asyncio.create_task(pump(proc.stderr, "stderr"))
                wait_task = asyncio.create_task(proc.wait())
                deadline = asyncio.get_running_loop().time() + timeout

                while True:
                    if asyncio.get_running_loop().time() > deadline and wait_task.done() is False:
                        proc.kill()
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
                    proc.kill()
                yield sse("error", {"message": str(e)})

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
        return {"status": "ok"}

    return app
