"""Pantheon: the unified entry point used by CLI, Web, and SDK."""

from __future__ import annotations

import copy
import logging
import os
import threading
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from pantheon.core.base import Task
from pantheon.core.connections import normalized_config
from pantheon.core.hermes import Hermes
from pantheon.core.paths import DataPaths
from pantheon.core.router import Router
from pantheon.core.services import WorkspaceServices
from pantheon.core.usage import UsageStore
from pantheon.llm import get_llm_client
from pantheon.roles import register_default_roles


class Pantheon:
    """The unified facade.

    Whether you come in via CLI, Web, or Python SDK, you end up here.
    """

    def __init__(
        self,
        config_path: str | None = None,
        env_path: str | None = None,
        verbose: bool = False,
    ) -> None:
        self.paths = DataPaths.for_workspace()
        env_path = env_path or str(self.paths.env)
        self.paths = replace(self.paths, env=Path(env_path).resolve())
        self.services = WorkspaceServices(self.paths)

        # Load YAML config (do this first; needed before logging init)
        config_path = config_path or self._find_config()
        self.config = self._load_config(config_path, self.services.env_value)

        # Logging
        log_cfg = self.config.get("logging", {})
        logging.basicConfig(
            level=log_cfg.get("level", "INFO"),
            format=log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
        )
        self.log = logging.getLogger("pantheon")
        if verbose:
            self.log.setLevel("DEBUG")

        self.usage_store = UsageStore(self.paths.state / "usage.sqlite")

        # Build LLM clients (one per provider)
        self.llm_clients: dict[str, Any] = self._build_llm_clients()

        # Build Router (Hermes's planner)
        hermes_cfg = self.config.get("pantheon", {}).get("hermes", {})
        hermes_model = hermes_cfg.get("model")
        # The router uses the hermes model's provider
        hermes_provider = hermes_cfg.get("provider", "anthropic")
        hermes_llm = self.llm_clients.get(hermes_provider)
        if hermes_llm is None and self.config.get("llm_providers", {}).get(hermes_provider, {}).get("enabled", True):
            # fall back to any available provider
            hermes_llm = next(iter(self.llm_clients.values()), None)
        if hermes_llm is not None:
            hermes_llm.default_model = hermes_model or hermes_llm.default_model
        self.router = Router(llm_client=hermes_llm, hermes_model=hermes_model)

        # Build roles
        self.roles = self._build_roles()

        # Hermes (the orchestrator)
        self.hermes = Hermes(roles=self.roles, router=self.router)
        self.hermes.task_store = self.services.tasks
        self.skill_store = self.services.skills
        self.services.attach(self)
        self.handle_memory = True

    # ---------- public API ----------

    def ask(
        self,
        content: str,
        mode: str = "auto",
        skill: str | None = None,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
        attachments: list[str | Path] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Ask the Pantheon to do something.

        Args:
            content: The task description.
            mode:
              - "auto" (default): Hermes picks the right role(s).
              - "role:<name>": Force a specific role.
              - "multi": Force multi-role decomposition.
            skill: Optional installed skill id to invoke explicitly.
            on_event: Optional callback for orchestration progress events.
            history: Prior user/assistant messages for this conversation only.
                Recent text is bounded to 16 messages and 24,000 characters;
                no extra summarization call is made.

        Returns:
            Dict with keys: mode, plan, content, steps.
        """
        identities = [self.services.media.upload_path(item)['id'] if isinstance(item, Path) or Path(item).is_file() else str(item)
                      for item in (attachments or [])]
        if identities:
            self.services.media.validate_attachments(identities)
        task = Task(content=content, mode=mode, skill=skill, attachments=identities, history=history or [])
        memory_events = self.services.process_input(content) if self.handle_memory else {'saved': [], 'suggestions': []}
        result = self._execution_hermes(on_event).dispatch(task, on_event=on_event)
        if self.handle_memory:
            self.services.capture_result(content, result, mode)
        result['memory_events'] = memory_events
        return result

    def list_roles(self) -> list[str]:
        """Return names of all enabled roles."""
        return list(self.roles.keys())

    def resume(self, task_id: str, *, acknowledge_effects: bool = False, on_event=None) -> dict:
        """Reuse completed checkpoints; retry failed steps with current model configuration."""
        store = self.hermes.task_store
        store.list()
        record = store.get(task_id)
        if not record or record['status'] not in {'failed', 'partial_failure', 'stopped', 'interrupted'}:
            raise ValueError('Only failed, stopped or interrupted tasks can be resumed.')
        checkpoint = record['data'].get('checkpoint')
        if not checkpoint:
            raise ValueError('This older task has no checkpoint. Start a new task from its saved request.')
        steps = checkpoint.get('steps', {})
        uncertain = any(not steps.get(index, {}).get('success') for index in checkpoint.get('effects', {}))
        if uncertain and not acknowledge_effects:
            raise ValueError('An unfinished step attempted an external tool or scheduling action. Review its result before acknowledging a retry.')
        saved_task = checkpoint['task']
        task = Task(content=saved_task['content'], mode=saved_task['mode'], skill=saved_task.get('skill'), attachments=saved_task.get('attachments', []), history=saved_task.get('history', []))
        store.claim_resume(task_id, task.task_id)
        result = self._execution_hermes(on_event).dispatch(task, on_event=on_event, resume_checkpoint=checkpoint)
        result['resumed_from'] = task_id
        if self.handle_memory:
            self.services.capture_result(task.content, result, task.mode)
        return result

    def _execution_hermes(self, on_event=None):
        hermes = copy.copy(self.hermes)
        hermes.cancel_event = getattr(on_event, 'cancel_event', None) or threading.Event()
        hermes.active_task_id = None
        hermes.router = copy.copy(self.router)
        hermes.roles = {name: copy.copy(role) for name, role in self.roles.items()}
        policy_reader = getattr(self.services, 'workflow_policy', None)
        if callable(policy_reader):
            policy = policy_reader()
            hermes.parallel_workers = policy['parallel_workers']
            hermes.replan_attempts = policy['replan_attempts']
        for role in hermes.roles.values():
            role.config = dict(getattr(role, 'config', {}) or {})
        return hermes

    def get_role(self, name: str) -> Any:
        """Get a role by name."""
        return self.roles.get(name)

    # ---------- internals ----------

    def _find_config(self) -> str:
        """Find the config file by searching in standard locations."""
        candidates = [
            os.environ.get("PANTHEON_CONFIG"),
            str(self.paths.config),
            str(self.paths.workspace / "config/pantheon.yaml"),
            str(self.paths.workspace / "config/pantheon.yml"),
            str(self.paths.workspace / "pantheon.yaml"),
            str(self.paths.workspace / "pantheon.yml"),
            str(Path.home() / ".pantheon.yaml"),
        ]
        for c in candidates:
            if c and Path(c).exists():
                return c
        # Fall back to the example file (read-only)
        example = self.paths.workspace / "config/pantheon.example.yaml"
        if not example.exists():
            example = Path(__file__).parents[1] / "defaults" / "pantheon.yaml"
        if example.exists():
            # Logger isn't initialized yet, so use the root logger.
            logging.getLogger("pantheon").warning(
                "No pantheon.yaml found; using pantheon.example.yaml. "
                "Copy it to pantheon.yaml and customize."
            )
            return str(example)
        raise FileNotFoundError(
            "No Pantheon config found. "
            "Copy config/pantheon.example.yaml to config/pantheon.yaml."
        )

    @staticmethod
    def _load_config(path: str, env_lookup=None) -> dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return _expand_env_vars(normalized_config(data), env_lookup)

    def _build_llm_clients(self) -> dict[str, Any]:
        providers = self.config.get("llm_providers", {})
        clients: dict[str, Any] = {}
        for name, cfg in providers.items():
            if not cfg.get("enabled", True):
                continue
            api_key = cfg.get("api_key") or self.services.env_value(f"{name.upper()}_API_KEY")
            # The YAML may have ${OPENAI_API_KEY} which _expand_env_vars handles
            api_key = api_key or ""
            if not api_key and name != "ollama":
                self.log.warning(
                    "No API key for provider '%s'. Roles using it will fail.",
                    name,
                )
            try:
                client = get_llm_client(
                    provider=cfg.get('adapter') or name,
                    api_key=api_key,
                    base_url=cfg.get("base_url"),
                )
                client.provider_name = cfg.get("provider_id") or name
                client.usage_recorder = self.usage_store.record
                client.budget = self.services.budget
                client.streaming_enabled = cfg.get("streaming", True)
                clients[name] = client
            except Exception as e:
                self.log.error("Failed to init provider '%s': %s", name, e)
        return clients

    def _build_roles(self) -> dict[str, Any]:
        roles_cfg = self.config.get("pantheon", {}).get("roles", {})
        defaults = register_default_roles()
        out: dict[str, Any] = {}

        # Always register all defaults; YAML can override config but not disable (yet)
        for role_name, role_cls in defaults.items():
            cfg = roles_cfg.get(role_name, {})
            if not cfg.get("enabled", True):
                continue

            provider = cfg.get("provider", role_cls.default_provider) or "openai"
            llm_client = self.llm_clients.get(provider)
            if llm_client is None and role_cls.default_model:
                self.log.warning(
                    "Role '%s' wants provider '%s' but it's not configured. "
                    "Role will fail when called.",
                    role_name,
                    provider,
                )

            role = role_cls(
                llm_client=llm_client,
                model=cfg.get("model") or role_cls.default_model,
                temperature=cfg.get("temperature", role_cls.default_temperature),
                config=cfg,
            )
            out[role_name] = role

        return out


def _expand_env_vars(obj: Any, env_lookup=None) -> Any:
    """Recursively expand ${VAR} patterns in a parsed YAML structure."""
    import re

    pattern = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")

    def expand(s: str) -> str:
        def repl(m: re.Match) -> str:
            return env_lookup(m.group(1)) if env_lookup else os.environ.get(m.group(1), "")
        return pattern.sub(repl, s)

    if isinstance(obj, dict):
        return {k: _expand_env_vars(v, env_lookup) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(v, env_lookup) for v in obj]
    if isinstance(obj, str):
        return expand(obj)
    return obj
