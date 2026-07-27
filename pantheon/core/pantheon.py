"""Pantheon: the unified entry point used by CLI, Web, and SDK."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from pantheon.core.base import Task
from pantheon.core.extensions import SkillStore
from pantheon.core.hermes import Hermes
from pantheon.core.router import Router
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
        # Load .env if present (silently)
        env_path = env_path or ".env"
        if Path(env_path).exists():
            load_dotenv(env_path)

        # Load YAML config (do this first; needed before logging init)
        config_path = config_path or self._find_config()
        self.config = self._load_config(config_path)

        # Logging
        log_cfg = self.config.get("logging", {})
        logging.basicConfig(
            level=log_cfg.get("level", "INFO"),
            format=log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
        )
        self.log = logging.getLogger("pantheon")
        if verbose:
            self.log.setLevel("DEBUG")

        # Build LLM clients (one per provider)
        self.llm_clients: dict[str, Any] = self._build_llm_clients()

        # Build Router (Hermes's planner)
        hermes_cfg = self.config.get("pantheon", {}).get("hermes", {})
        hermes_model = hermes_cfg.get("model")
        # The router uses the hermes model's provider
        hermes_provider = hermes_cfg.get("provider", "anthropic")
        hermes_llm = self.llm_clients.get(hermes_provider)
        if hermes_llm is None:
            # fall back to any available provider
            hermes_llm = next(iter(self.llm_clients.values()), None)
        if hermes_llm is not None:
            hermes_llm.default_model = hermes_model or hermes_llm.default_model
        self.router = Router(llm_client=hermes_llm, hermes_model=hermes_model)

        # Build roles
        self.roles = self._build_roles()

        # Hermes (the orchestrator)
        self.hermes = Hermes(roles=self.roles, router=self.router)
        workspace_root = Path(os.environ.get("PANTHEON_WORKSPACE", Path.cwd())).resolve()
        self.skill_store = SkillStore(
            workspace_root / ".pantheon" / "skills",
            legacy_path=workspace_root / ".pantheon" / "skills.json",
        )
        self.hermes.skill_context_provider = self.skill_store.context_block
        self.hermes.skill_catalog_provider = self.skill_store.catalog_for_roles
        self.hermes.skill_lookup_provider = self.skill_store.get

    # ---------- public API ----------

    def ask(
        self,
        content: str,
        mode: str = "auto",
        skill: str | None = None,
    ) -> dict[str, Any]:
        """Ask the Pantheon to do something.

        Args:
            content: The task description.
            mode:
              - "auto" (default): Hermes picks the right role(s).
              - "role:<name>": Force a specific role.
              - "multi": Force multi-role decomposition.
            skill: Optional installed skill id to invoke explicitly.

        Returns:
            Dict with keys: mode, plan, content, steps.
        """
        task = Task(content=content, mode=mode, skill=skill)
        return self.hermes.dispatch(task)

    def list_roles(self) -> list[str]:
        """Return names of all enabled roles."""
        return list(self.roles.keys())

    def get_role(self, name: str) -> Any:
        """Get a role by name."""
        return self.roles.get(name)

    # ---------- internals ----------

    def _find_config(self) -> str:
        """Find the config file by searching in standard locations."""
        candidates = [
            os.environ.get("PANTHEON_CONFIG"),
            "config/pantheon.yaml",
            "config/pantheon.yml",
            "pantheon.yaml",
            "pantheon.yml",
            str(Path.home() / ".pantheon.yaml"),
        ]
        for c in candidates:
            if c and Path(c).exists():
                return c
        # Fall back to the example file (read-only)
        example = Path("config/pantheon.example.yaml")
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
    def _load_config(path: str) -> dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return _expand_env_vars(data)

    def _build_llm_clients(self) -> dict[str, Any]:
        providers = self.config.get("llm_providers", {})
        clients: dict[str, Any] = {}
        for name, cfg in providers.items():
            if not cfg.get("enabled", True):
                continue
            api_key = cfg.get("api_key") or os.environ.get(
                f"{name.upper()}_API_KEY", ""
            )
            # The YAML may have ${OPENAI_API_KEY} which _expand_env_vars handles
            api_key = api_key or ""
            if not api_key and name != "ollama":
                self.log.warning(
                    "No API key for provider '%s'. Roles using it will fail.",
                    name,
                )
            try:
                client = get_llm_client(
                    provider=name,
                    api_key=api_key,
                    base_url=cfg.get("base_url"),
                )
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


def _expand_env_vars(obj: Any) -> Any:
    """Recursively expand ${VAR} patterns in a parsed YAML structure."""
    import re

    pattern = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")

    def expand(s: str) -> str:
        def repl(m: re.Match) -> str:
            return os.environ.get(m.group(1), "")
        return pattern.sub(repl, s)

    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(v) for v in obj]
    if isinstance(obj, str):
        return expand(obj)
    return obj
