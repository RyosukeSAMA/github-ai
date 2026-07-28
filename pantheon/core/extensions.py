"""Local extension stores and MCP client helpers.

The web UI keeps extension configuration in the workspace's ``.pantheon``
directory.  Skills and prompt-pack plugins are deliberately data-only: they
can change agent instructions without granting arbitrary Python execution.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import yaml

EXTENSION_ROLES = {
    "global",
    "hermes",
    "hephaestus",
    "athena",
    "apollo",
    "chronos",
}


def _now() -> int:
    return int(time.time())


def _slug(value: str, fallback: str = "extension") -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return (clean or fallback)[:48]


def _roles(value: list[str] | None) -> list[str]:
    selected: list[str] = []
    for item in value or []:
        role = str(item).strip().lower()
        if role in EXTENSION_ROLES and role not in selected:
            selected.append(role)
    return selected or ["global"]


class JsonCollection:
    """Small atomic JSON collection used for local extension metadata."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [dict(item) for item in value] if isinstance(value, list) else []

    def write(self, items: list[dict[str, Any]]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(items, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)


class PromptExtensionStore:
    """CRUD and role-scoped context for data-only prompt extensions."""

    kind = "extension"

    def __init__(self, path: Path) -> None:
        self.collection = JsonCollection(path)

    @property
    def path(self) -> Path:
        return self.collection.path

    def list(self, query: str = "") -> list[dict[str, Any]]:
        items = self.collection.read()
        needle = query.strip().lower()
        if needle:
            items = [
                item
                for item in items
                if needle in " ".join(
                    str(item.get(key, ""))
                    for key in ("name", "description", "instructions")
                ).lower()
            ]
        return sorted(items, key=lambda item: (not bool(item.get("enabled", True)), item.get("name", "").lower()))

    def get(self, item_id: str) -> dict[str, Any] | None:
        return next((item for item in self.collection.read() if item.get("id") == item_id), None)

    def save(
        self,
        *,
        item_id: str = "",
        name: str,
        description: str,
        instructions: str,
        roles: list[str] | None = None,
        enabled: bool = True,
        version: str = "1.0.0",
    ) -> dict[str, Any]:
        clean_name = name.strip()
        clean_instructions = instructions.strip()
        if not clean_name:
            raise ValueError("name is required")
        if not clean_instructions:
            raise ValueError("instructions are required")
        if len(clean_name) > 100:
            raise ValueError("name is too long")
        if len(clean_instructions) > 20_000:
            raise ValueError("instructions are too long")

        items = self.collection.read()
        existing = next((item for item in items if item.get("id") == item_id), None)
        item = {
            "id": item_id or f"{_slug(clean_name)}-{uuid.uuid4().hex[:6]}",
            "name": clean_name,
            "description": description.strip()[:500],
            "instructions": clean_instructions,
            "roles": _roles(roles),
            "enabled": bool(enabled),
            "version": version.strip() or "1.0.0",
            "source": "local",
            "updated_at": _now(),
        }
        if existing:
            item["created_at"] = existing.get("created_at", _now())
            items[items.index(existing)] = item
        else:
            item["created_at"] = _now()
            items.append(item)
        self.collection.write(items)
        return item

    def delete(self, item_id: str) -> bool:
        items = self.collection.read()
        remaining = [item for item in items if item.get("id") != item_id]
        if len(remaining) == len(items):
            return False
        self.collection.write(remaining)
        return True

    def set_enabled(self, item_id: str, enabled: bool) -> dict[str, Any] | None:
        item = self.get(item_id)
        if item is None:
            return None
        return self.save(
            item_id=item_id,
            name=str(item.get("name", "")),
            description=str(item.get("description", "")),
            instructions=str(item.get("instructions", "")),
            roles=list(item.get("roles") or []),
            enabled=enabled,
            version=str(item.get("version", "1.0.0")),
        )

    def context_block(self, _content: str, role_name: str) -> tuple[str, list[dict[str, Any]]]:
        role = role_name.strip().lower()
        active = [
            item
            for item in self.list()
            if item.get("enabled", True)
            and ("global" in (item.get("roles") or []) or role in (item.get("roles") or []))
        ]
        if not active:
            return "", []
        title = "Active local skills" if self.kind == "skill" else "Active local plugin packs"
        blocks = [title + f" for {role_name}:"]
        details: list[dict[str, Any]] = []
        for item in active:
            blocks.append(f"\n[{item.get('name', self.kind)}]\n{item.get('instructions', '')}")
            details.append({"id": item.get("id", ""), "name": item.get("name", "")})
        return "\n".join(blocks), details


class SkillStore:
    """Directory-backed registry for standard ``SKILL.md`` workflows.

    Built-in skills ship with Pantheon, while user-created skills live below
    ``.pantheon/skills``. A small sidecar stores Pantheon-specific routing
    metadata so the SKILL.md frontmatter remains portable.
    """

    kind = "skill"

    def __init__(
        self,
        path: Path,
        *,
        builtin_path: Path | None = None,
        legacy_path: Path | None = None,
    ) -> None:
        supplied_path = Path(path)
        if supplied_path.suffix.lower() == ".json":
            legacy_path = legacy_path or supplied_path
            supplied_path = supplied_path.with_suffix("")
        self.local_path = supplied_path
        self.builtin_path = builtin_path or Path(__file__).resolve().parents[1] / "skills"
        self.legacy_path = legacy_path
        self.state_path = self.local_path.parent / "skill_state.json"
        self.migration_marker = self.local_path / ".legacy-imported"
        try:
            self._migrate_legacy()
        except OSError:
            # Listing bundled Skills must also work in read-only installations.
            # Migration is retried the next time the registry is writable.
            pass

    @property
    def path(self) -> Path:
        return self.local_path

    @staticmethod
    def _parse_skill(skill_dir: Path, source: str) -> dict[str, Any] | None:
        skill_path = skill_dir / "SKILL.md"
        if not skill_path.exists():
            return None
        try:
            raw = skill_path.read_text(encoding="utf-8")
        except OSError:
            return None
        match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", raw, re.DOTALL)
        if not match:
            return None
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return None
        if not isinstance(frontmatter, dict):
            return None

        metadata: dict[str, Any] = {}
        metadata_path = skill_dir / "pantheon.json"
        if metadata_path.exists():
            try:
                loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata = loaded if isinstance(loaded, dict) else {}
            except (OSError, ValueError):
                metadata = {}

        interface: dict[str, Any] = {}
        policy: dict[str, Any] = {}
        agent_path = skill_dir / "agents" / "openai.yaml"
        if agent_path.exists():
            try:
                loaded = yaml.safe_load(agent_path.read_text(encoding="utf-8")) or {}
                if isinstance(loaded, dict):
                    interface = loaded.get("interface") or {}
                    policy = loaded.get("policy") or {}
            except (OSError, yaml.YAMLError):
                pass

        skill_id = _slug(
            str(metadata.get("id") or frontmatter.get("name") or skill_dir.name),
            "skill",
        )
        description = str(frontmatter.get("description") or metadata.get("description") or "")
        display_name = str(
            metadata.get("display_name")
            or interface.get("display_name")
            or skill_id.replace("-", " ").title()
        )
        try:
            updated_at = int(metadata.get("updated_at") or skill_path.stat().st_mtime)
        except OSError:
            updated_at = 0
        return {
            "id": skill_id,
            "name": display_name,
            "description": description,
            "instructions": match.group(2).strip(),
            "roles": _roles(metadata.get("roles")),
            "version": str(metadata.get("version") or "1.0.0"),
            "source": source,
            "builtin": source == "builtin",
            "editable": source != "builtin",
            "kind": str(metadata.get("kind") or "role"),
            "trigger_terms": [
                str(term).strip()
                for term in metadata.get("trigger_terms") or []
                if str(term).strip()
            ],
            "allow_implicit_invocation": bool(
                metadata.get(
                    "allow_implicit_invocation",
                    policy.get("allow_implicit_invocation", True),
                )
            ),
            "created_at": int(metadata.get("created_at") or updated_at),
            "updated_at": updated_at,
            "path": str(skill_dir),
        }

    def _read_state(self) -> dict[str, bool]:
        if not self.state_path.exists():
            return {}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {
            str(key): bool(value)
            for key, value in raw.items()
        } if isinstance(raw, dict) else {}

    def _write_state(self, state: dict[str, bool]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.state_path)

    def _scan(self) -> list[dict[str, Any]]:
        state = self._read_state()
        items: dict[str, dict[str, Any]] = {}
        for root, source in (
            (self.builtin_path, "builtin"),
            (self.local_path, "local"),
        ):
            if not root.exists():
                continue
            for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
                item = self._parse_skill(skill_dir, source)
                if item is None or item["id"] in items:
                    continue
                item["enabled"] = state.get(item["id"], True)
                items[item["id"]] = item
        return list(items.values())

    def list(self, query: str = "") -> list[dict[str, Any]]:
        items = self._scan()
        needle = query.strip().lower()
        if needle:
            items = [
                item for item in items
                if needle in " ".join(
                    [
                        str(item.get("id") or ""),
                        str(item.get("name") or ""),
                        str(item.get("description") or ""),
                        str(item.get("instructions") or ""),
                        " ".join(item.get("trigger_terms") or []),
                    ]
                ).lower()
            ]
        return sorted(
            items,
            key=lambda item: (
                not bool(item.get("enabled", True)),
                item.get("source") != "builtin",
                str(item.get("name") or "").lower(),
            ),
        )

    def get(self, item_id: str) -> dict[str, Any] | None:
        requested = str(item_id or "").strip().lower().lstrip("$")
        requested_slug = _slug(requested, "")
        for item in self._scan():
            aliases = {
                str(item.get("id") or "").lower(),
                _slug(str(item.get("name") or ""), ""),
            }
            if requested in aliases or requested_slug in aliases:
                return item
        return None

    @staticmethod
    def _default_trigger_terms(
        name: str,
        description: str,
        instructions: str,
    ) -> list[str]:
        candidates = [name, description]
        candidates.extend(
            re.findall(r"[\u4e00-\u9fff]{2,8}|[a-zA-Z][a-zA-Z0-9_-]{2,}", instructions)
        )
        terms: list[str] = []
        for candidate in candidates:
            clean = re.sub(r"\s+", " ", str(candidate)).strip()
            if clean and clean.lower() not in {item.lower() for item in terms}:
                terms.append(clean[:80])
            if len(terms) >= 12:
                break
        return terms

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)

    def save(
        self,
        *,
        item_id: str = "",
        name: str,
        description: str,
        instructions: str,
        roles: list[str] | None = None,
        enabled: bool = True,
        version: str = "1.0.0",
        trigger_terms: list[str] | None = None,
        kind: str = "role",
        allow_implicit_invocation: bool = True,
    ) -> dict[str, Any]:
        clean_name = name.strip()
        clean_description = description.strip()
        clean_instructions = instructions.strip()
        if not clean_name:
            raise ValueError("name is required")
        if not clean_instructions:
            raise ValueError("instructions are required")
        if len(clean_name) > 100:
            raise ValueError("name is too long")
        if len(clean_instructions) > 20_000:
            raise ValueError("instructions are too long")

        existing = self.get(item_id) if item_id else None
        if existing and existing.get("builtin"):
            raise ValueError("built-in skills are read-only")

        skill_id = _slug(item_id or clean_name, "skill")
        if not item_id:
            base_id = skill_id
            while self.get(skill_id) is not None:
                skill_id = f"{base_id}-{uuid.uuid4().hex[:6]}"
        skill_dir = self.local_path / skill_id
        metadata_path = skill_dir / "pantheon.json"
        now = _now()
        created_at = int(existing.get("created_at") or now) if existing else now
        selected_roles = _roles(roles)
        selected_kind = kind if kind in {"role", "shared", "council"} else "role"
        terms = [
            str(term).strip()
            for term in (trigger_terms or [])
            if str(term).strip()
        ] or self._default_trigger_terms(clean_name, clean_description, clean_instructions)

        body = clean_instructions
        if not re.match(r"^#\s+", body):
            body = f"# {clean_name}\n\n{body}"
        frontmatter = yaml.safe_dump(
            {
                "name": skill_id,
                "description": clean_description
                or f"Reusable Pantheon workflow for {clean_name}.",
            },
            allow_unicode=True,
            sort_keys=False,
        ).strip()
        self._write_text(
            skill_dir / "SKILL.md",
            f"---\n{frontmatter}\n---\n\n{body.rstrip()}\n",
        )

        metadata = {
            "id": skill_id,
            "display_name": clean_name,
            "roles": selected_roles,
            "version": version.strip() or "1.0.0",
            "kind": selected_kind,
            "trigger_terms": terms,
            "allow_implicit_invocation": bool(allow_implicit_invocation),
            "created_at": created_at,
            "updated_at": now,
        }
        self._write_text(
            metadata_path,
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        )
        short_description = clean_description or f"Reusable workflow for {clean_name}"
        if len(short_description) < 25:
            short_description = f"{short_description} in Pantheon tasks"
        agent_config = {
            "interface": {
                "display_name": clean_name,
                "short_description": short_description[:64],
                "brand_color": "#6366F1",
                "default_prompt": f"Use ${skill_id} to complete this task carefully.",
            },
            "policy": {
                "allow_implicit_invocation": bool(allow_implicit_invocation),
            },
        }
        self._write_text(
            skill_dir / "agents" / "openai.yaml",
            yaml.safe_dump(
                agent_config,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ),
        )
        state = self._read_state()
        state[skill_id] = bool(enabled)
        self._write_state(state)
        saved = self.get(skill_id)
        if saved is None:
            raise ValueError("skill could not be saved")
        return saved

    def delete(self, item_id: str) -> bool:
        item = self.get(item_id)
        if item is None:
            return False
        if item.get("builtin"):
            raise ValueError("built-in skills cannot be deleted")
        skill_dir = Path(str(item.get("path") or "")).resolve()
        try:
            skill_dir.relative_to(self.local_path.resolve())
        except ValueError as exc:
            raise ValueError("skill path is outside the local registry") from exc
        shutil.rmtree(skill_dir)
        state = self._read_state()
        state.pop(str(item.get("id") or ""), None)
        self._write_state(state)
        return True

    def set_enabled(self, item_id: str, enabled: bool) -> dict[str, Any] | None:
        item = self.get(item_id)
        if item is None:
            return None
        state = self._read_state()
        state[str(item["id"])] = bool(enabled)
        self._write_state(state)
        return self.get(str(item["id"]))

    @staticmethod
    def _applies_to_role(item: dict[str, Any], role_name: str) -> bool:
        roles = item.get("roles") or []
        return "global" in roles or role_name.strip().lower() in roles

    @staticmethod
    def _match_score(content: str, item: dict[str, Any]) -> int:
        text = re.sub(r"\s+", " ", content).strip().lower()
        if not text:
            return 0
        score = 0
        terms = [
            str(item.get("id") or "").replace("-", " "),
            str(item.get("name") or ""),
            *(item.get("trigger_terms") or []),
        ]
        seen: set[str] = set()
        for raw_term in terms:
            term = re.sub(r"\s+", " ", str(raw_term)).strip().lower()
            if len(term) < 2 or term in seen:
                continue
            seen.add(term)
            if term in text:
                score += 8 if " " in term or re.search(r"[\u4e00-\u9fff]", term) else 5
                continue
            words = {
                word for word in re.findall(r"[a-z0-9]{3,}", term)
                if word not in {"with", "from", "that", "this", "skill", "task"}
            }
            if words:
                score += min(4, len(words & set(re.findall(r"[a-z0-9]{3,}", text))))
        return score

    def context_block(
        self,
        content: str,
        role_name: str,
        requested_skill: str = "",
    ) -> tuple[str, list[dict[str, Any]]]:
        role = role_name.strip().lower()
        active = [
            item for item in self.list()
            if item.get("enabled", True) and self._applies_to_role(item, role)
        ]
        explicit = self.get(requested_skill) if requested_skill else None
        selected: list[dict[str, Any]] = []
        if explicit and explicit.get("enabled", True) and self._applies_to_role(explicit, role):
            selected = [explicit]
        elif not requested_skill:
            ranked = sorted(
                (
                    (self._match_score(content, item), item)
                    for item in active
                    if item.get("allow_implicit_invocation", True)
                ),
                key=lambda pair: (-pair[0], str(pair[1].get("name") or "")),
            )
            if ranked and ranked[0][0] >= 5:
                selected = [ranked[0][1]]
        if not selected:
            return "", []

        blocks = [f"Selected Pantheon skill for {role_name}:"]
        details: list[dict[str, Any]] = []
        for item in selected:
            blocks.append(
                f"\n[{item.get('name', item.get('id', 'skill'))} | "
                f"${item.get('id', '')}]\n{item.get('instructions', '')}"
            )
            details.append({
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "source": item.get("source", ""),
                "roles": list(item.get("roles") or []),
                "kind": item.get("kind", "role"),
                "invocation": "explicit" if requested_skill else "automatic",
            })
        return "\n".join(blocks), details

    def catalog_for_roles(self) -> dict[str, list[dict[str, Any]]]:
        catalog: dict[str, list[dict[str, Any]]] = {
            role: [] for role in EXTENSION_ROLES if role != "global"
        }
        for item in self.list():
            if not item.get("enabled", True):
                continue
            roles = item.get("roles") or []
            target_roles = list(catalog) if "global" in roles else roles
            summary = {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "kind": item.get("kind", "role"),
            }
            for role in target_roles:
                if role in catalog:
                    catalog[role].append(summary)
        return catalog

    def _migrate_legacy(self) -> None:
        if (
            self.legacy_path is None
            or not self.legacy_path.exists()
            or self.migration_marker.exists()
        ):
            return
        legacy = JsonCollection(self.legacy_path).read()
        existing_ids = {
            str(item.get("id") or "")
            for item in self._scan()
        }
        for item in legacy:
            item_id = _slug(str(item.get("id") or item.get("name") or ""), "skill")
            if item_id in existing_ids:
                continue
            try:
                self.save(
                    item_id=item_id,
                    name=str(item.get("name") or item_id),
                    description=str(item.get("description") or ""),
                    instructions=str(item.get("instructions") or ""),
                    roles=list(item.get("roles") or []),
                    enabled=bool(item.get("enabled", True)),
                    version=str(item.get("version") or "1.0.0"),
                )
            except ValueError:
                continue
            existing_ids.add(item_id)
        self._write_text(
            self.migration_marker,
            f"Imported from {self.legacy_path.name} at {_now()}.\n",
        )


class PluginStore(PromptExtensionStore):
    kind = "plugin"


class MCPError(RuntimeError):
    """Raised when the optional MCP client cannot connect or call a tool."""


MCP_AGENT_ROLES = ("hephaestus", "athena", "apollo", "chronos")
MCP_APPROVAL_MODES = {"auto", "ask"}
MCP_SAFE_ENV_KEYS = (
    "HOME",
    "USER",
    "LOGNAME",
    "PATH",
    "SHELL",
    "TMPDIR",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "SYSTEMROOT",
)
MAX_MCP_RESULT_CHARS = 50_000
MCP_ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MCP_HEADER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$")


def mcp_available() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        return False
    return True


def _model_dump(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _tool_payload(tool: Any) -> dict[str, Any]:
    raw = _model_dump(tool)
    if isinstance(raw, dict):
        annotations = raw.get("annotations") or {}
        if not isinstance(annotations, dict):
            annotations = _model_dump(annotations) or {}
        normalized_annotations = {
            "read_only": bool(
                annotations.get("readOnlyHint", annotations.get("read_only_hint", False))
            ),
            "destructive": bool(
                annotations.get("destructiveHint", annotations.get("destructive_hint", True))
            ),
            "idempotent": bool(
                annotations.get("idempotentHint", annotations.get("idempotent_hint", False))
            ),
            "open_world": bool(
                annotations.get("openWorldHint", annotations.get("open_world_hint", True))
            ),
        }
        risk = (
            "read"
            if normalized_annotations["read_only"]
            else "destructive"
            if normalized_annotations["destructive"]
            else "write"
        )
        return {
            "name": str(raw.get("name") or ""),
            "title": str(raw.get("title") or raw.get("name") or ""),
            "description": str(raw.get("description") or ""),
            "input_schema": raw.get("inputSchema") or raw.get("input_schema") or {},
            "annotations": normalized_annotations,
            "risk": risk,
        }
    return _tool_payload({
        "name": str(getattr(tool, "name", "")),
        "title": str(getattr(tool, "title", "") or getattr(tool, "name", "")),
        "description": str(getattr(tool, "description", "") or ""),
        "input_schema": _model_dump(getattr(tool, "inputSchema", {})) or {},
        "annotations": _model_dump(getattr(tool, "annotations", {})) or {},
    })


def _result_payload(result: Any) -> dict[str, Any]:
    raw = _model_dump(result)
    if isinstance(raw, dict):
        content = raw.get("content") or []
        structured = raw.get("structuredContent") or raw.get("structured_content")
    else:
        content = getattr(result, "content", []) or []
        structured = getattr(result, "structuredContent", None)
    text_parts: list[str] = []
    for block in content:
        block_raw = _model_dump(block)
        if isinstance(block_raw, dict) and block_raw.get("text") is not None:
            text_parts.append(str(block_raw["text"]))
        elif getattr(block, "text", None) is not None:
            text_parts.append(str(block.text))
    text = "\n".join(text_parts)
    truncated = len(text) > MAX_MCP_RESULT_CHARS
    if truncated:
        text = text[:MAX_MCP_RESULT_CHARS] + "\n\n[Output truncated by Pantheon]"
    return {
        "text": text,
        "structured": structured,
        "is_error": bool(raw.get("isError") if isinstance(raw, dict) else getattr(result, "isError", False)),
        "truncated": truncated,
    }


class MCPManager:
    """Connect configured MCP servers through an explicit, role-aware boundary."""

    def __init__(
        self,
        path: Path,
        env_lookup: Callable[[str], str] | None = None,
    ) -> None:
        self.collection = JsonCollection(path)
        self.env_lookup = env_lookup or (lambda key: os.environ.get(key, ""))

    @property
    def path(self) -> Path:
        return self.collection.path

    def list(self) -> list[dict[str, Any]]:
        return self.collection.read()

    def get(self, server_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list() if item.get("id") == server_id), None)

    @staticmethod
    def _clean_mapping(value: Any) -> dict[str, str]:
        return {
            str(key).strip(): str(source).strip()
            for key, source in (value or {}).items()
            if str(key).strip() and str(source).strip()
        }

    @staticmethod
    def _clean_roles(value: Any, fallback: list[str] | None = None) -> list[str]:
        roles: list[str] = []
        for item in value or fallback or []:
            role = str(item).strip().lower()
            if role in MCP_AGENT_ROLES and role not in roles:
                roles.append(role)
        return roles

    @classmethod
    def _default_tool_policy(
        cls,
        tool: dict[str, Any],
        server_roles: list[str],
    ) -> dict[str, Any]:
        annotations = tool.get("annotations") or {}
        return {
            "enabled": True,
            "roles": cls._clean_roles(server_roles),
            "approval": "auto" if annotations.get("read_only") is True else "ask",
        }

    @classmethod
    def _reconcile_tool_policies(
        cls,
        tools: list[dict[str, Any]],
        raw_policies: Any,
        server_roles: list[str],
    ) -> dict[str, dict[str, Any]]:
        existing = raw_policies if isinstance(raw_policies, dict) else {}
        policies: dict[str, dict[str, Any]] = {}
        for tool in tools:
            name = str(tool.get("name") or "").strip()
            if not name:
                continue
            default = cls._default_tool_policy(tool, server_roles)
            raw = existing.get(name) if isinstance(existing.get(name), dict) else {}
            approval = str(raw.get("approval") or default["approval"]).strip().lower()
            policies[name] = {
                "enabled": bool(raw.get("enabled", default["enabled"])),
                "roles": cls._clean_roles(raw.get("roles"), default["roles"]),
                "approval": approval if approval in MCP_APPROVAL_MODES else default["approval"],
            }
        return policies

    def save(self, data: dict[str, Any], server_id: str = "") -> dict[str, Any]:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")
        transport = str(data.get("transport") or "stdio").strip().lower()
        if transport not in {"stdio", "streamable_http"}:
            raise ValueError("transport must be stdio or streamable_http")
        command = str(data.get("command") or "").strip()
        url = str(data.get("url") or "").strip()
        if transport == "stdio" and not command:
            raise ValueError("command is required for stdio transport")
        if transport == "streamable_http" and not url:
            raise ValueError("url is required for streamable_http transport")
        if transport == "streamable_http" and not url.startswith(("http://", "https://")):
            raise ValueError("HTTP MCP URL must start with http:// or https://")
        args = [str(item).strip() for item in (data.get("args") or []) if str(item).strip()]
        env = self._clean_mapping(data.get("env"))
        headers_env = self._clean_mapping(data.get("headers_env"))
        invalid_env = next(
            (
                name
                for name in (*env.keys(), *env.values())
                if not MCP_ENV_NAME_PATTERN.fullmatch(name)
            ),
            "",
        )
        if invalid_env:
            raise ValueError(f"invalid environment variable name: {invalid_env}")
        invalid_header = next(
            (name for name in headers_env if not MCP_HEADER_NAME_PATTERN.fullmatch(name)),
            "",
        )
        if invalid_header:
            raise ValueError(f"invalid HTTP header name: {invalid_header}")
        invalid_header_env = next(
            (
                name
                for name in headers_env.values()
                if not MCP_ENV_NAME_PATTERN.fullmatch(name)
            ),
            "",
        )
        if invalid_header_env:
            raise ValueError(
                f"invalid header environment variable name: {invalid_header_env}"
            )
        bearer_env = str(data.get("bearer_token_env_var") or "").strip()
        if bearer_env and not MCP_ENV_NAME_PATTERN.fullmatch(bearer_env):
            raise ValueError("bearer token environment variable name is invalid")
        items = self.list()
        old = next((item for item in items if item.get("id") == server_id), None)
        tools = data.get("tools", old.get("tools", []) if old else [])
        tools = [dict(tool) for tool in tools if isinstance(tool, dict)]
        roles = self._clean_roles(
            data.get("roles"),
            old.get("roles") if old else list(MCP_AGENT_ROLES),
        )
        raw_policies = data.get(
            "tool_policies",
            old.get("tool_policies", {}) if old else {},
        )
        item = {
            "id": server_id or f"{_slug(name, 'mcp')}-{uuid.uuid4().hex[:6]}",
            "name": name[:100],
            "transport": transport,
            "command": command[:500],
            "args": args[:50],
            "cwd": str(data.get("cwd") or "").strip()[:500],
            "url": url[:1000],
            "env": env,
            "headers_env": headers_env,
            "bearer_token_env_var": bearer_env[:200],
            "enabled": bool(data.get("enabled", True)),
            "allow_agent_calls": bool(data.get("allow_agent_calls", False)),
            "roles": roles,
            "tools": tools,
            "tool_policies": self._reconcile_tool_policies(
                tools,
                raw_policies,
                roles,
            ),
            "startup_timeout_seconds": max(
                1,
                min(int(data.get("startup_timeout_seconds") or 15), 120),
            ),
            "tool_timeout_seconds": max(
                1,
                min(int(data.get("tool_timeout_seconds") or 60), 600),
            ),
            "server_metadata": data.get(
                "server_metadata",
                old.get("server_metadata", {}) if old else {},
            ),
            "last_test": data.get("last_test", old.get("last_test") if old else None),
            "created_at": old.get("created_at", _now()) if old else _now(),
            "updated_at": _now(),
        }
        if old:
            items[items.index(old)] = item
        else:
            items.append(item)
        self.collection.write(items)
        return item

    def delete(self, server_id: str) -> bool:
        items = self.list()
        remaining = [item for item in items if item.get("id") != server_id]
        if len(remaining) == len(items):
            return False
        self.collection.write(remaining)
        return True

    def _record_test(
        self,
        server_id: str,
        *,
        ok: bool,
        tools: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
        error: str = "",
    ) -> None:
        item = self.get(server_id)
        if item is None:
            return
        item["tools"] = tools
        if metadata is not None:
            item["server_metadata"] = metadata
        item["last_test"] = {
            "ok": ok,
            "error": error[:1000],
            "at": _now(),
        }
        self.save(item, server_id=server_id)

    def _env_for(self, server: dict[str, Any]) -> dict[str, str]:
        env = {
            key: os.environ[key]
            for key in MCP_SAFE_ENV_KEYS
            if key in os.environ
        }
        for key, env_name in (server.get("env") or {}).items():
            value = self.env_lookup(str(env_name))
            if value:
                env[str(key)] = value
        return env

    def _headers_for(self, server: dict[str, Any]) -> dict[str, str]:
        headers: dict[str, str] = {}
        bearer_env = str(server.get("bearer_token_env_var") or "")
        if bearer_env:
            token = self.env_lookup(bearer_env)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        for header, env_name in (server.get("headers_env") or {}).items():
            value = self.env_lookup(str(env_name))
            if value:
                headers[str(header)] = value
        return headers

    async def _with_session(
        self,
        server: dict[str, Any],
        operation: Callable[[Any, Any], Any],
    ) -> Any:
        try:
            from mcp import ClientSession, StdioServerParameters
            if server.get("transport") == "stdio":
                from mcp.client.stdio import stdio_client

                params = StdioServerParameters(
                    command=str(server.get("command") or ""),
                    args=[str(item) for item in server.get("args", [])],
                    env=self._env_for(server),
                    cwd=str(server.get("cwd") or "") or None,
                )
                async with stdio_client(params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        initialized = await asyncio.wait_for(
                            session.initialize(),
                            timeout=float(server.get("startup_timeout_seconds") or 15),
                        )
                        return await asyncio.wait_for(
                            operation(session, initialized),
                            timeout=float(server.get("tool_timeout_seconds") or 60),
                        )

            from mcp.client.streamable_http import streamable_http_client

            startup_timeout = float(server.get("startup_timeout_seconds") or 15)
            tool_timeout = float(server.get("tool_timeout_seconds") or 60)
            timeout = httpx.Timeout(tool_timeout, connect=startup_timeout)
            async with httpx.AsyncClient(
                headers=self._headers_for(server),
                timeout=timeout,
                follow_redirects=True,
            ) as http_client:
                async with streamable_http_client(
                    str(server.get("url") or ""),
                    http_client=http_client,
                ) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        initialized = await asyncio.wait_for(
                            session.initialize(),
                            timeout=startup_timeout,
                        )
                        return await asyncio.wait_for(
                            operation(session, initialized),
                            timeout=tool_timeout,
                        )
        except ImportError as exc:
            raise MCPError("MCP support is not installed. Install the mcp package first.") from exc
        except Exception as exc:
            raise MCPError(str(exc)) from exc

    async def _inspect_async(self, server: dict[str, Any]) -> dict[str, Any]:
        async def operation(session: Any, initialized: Any) -> dict[str, Any]:
            response = await session.list_tools()
            raw = _model_dump(initialized)
            if isinstance(raw, dict):
                instructions_value = raw.get("instructions")
                server_info = raw.get("serverInfo") or raw.get("server_info") or {}
                capabilities = raw.get("capabilities") or {}
            else:
                instructions_value = getattr(initialized, "instructions", "")
                server_info = _model_dump(
                    getattr(initialized, "serverInfo", {})
                ) or {}
                capabilities = _model_dump(
                    getattr(initialized, "capabilities", {})
                ) or {}
            metadata = {
                "instructions": str(instructions_value or "")[:4000],
                "server_info": server_info,
                "capabilities": capabilities,
            }
            return {
                "tools": [_tool_payload(tool) for tool in response.tools],
                "metadata": metadata,
            }

        return await self._with_session(server, operation)

    async def _call_async(self, server: dict[str, Any], tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async def operation(session: Any, _initialized: Any) -> dict[str, Any]:
            result = await session.call_tool(tool_name, arguments=arguments)
            return _result_payload(result)

        return await self._with_session(server, operation)

    @staticmethod
    def _run_sync(factory: Callable[[], Any]) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(factory())

        result: list[Any] = []
        error: list[BaseException] = []

        def worker() -> None:
            try:
                result.append(asyncio.run(factory()))
            except BaseException as exc:  # pragma: no cover - defensive thread bridge
                error.append(exc)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join()
        if error:
            raise error[0]
        return result[0] if result else None

    def inspect(self, server_id: str) -> dict[str, Any]:
        server = self.get(server_id)
        if server is None:
            raise MCPError("MCP server not found")
        try:
            inspected = self._run_sync(lambda: self._inspect_async(server))
            tools = inspected.get("tools", [])
            metadata = inspected.get("metadata", {})
            self._record_test(
                server_id,
                ok=True,
                tools=tools,
                metadata=metadata,
            )
            return {"ok": True, "server": self.get(server_id), "tools": tools}
        except Exception as exc:
            message = str(exc)
            previous = self.get(server_id) or {}
            tools = [
                dict(tool)
                for tool in previous.get("tools", [])
                if isinstance(tool, dict)
            ]
            self._record_test(
                server_id,
                ok=False,
                tools=tools,
                metadata=previous.get("server_metadata") or {},
                error=message,
            )
            return {
                "ok": False,
                "server": self.get(server_id),
                "tools": tools,
                "error": message,
            }

    def call_tool(self, server_id: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        server = self.get(server_id)
        if server is None:
            raise MCPError("MCP server not found")
        if not server.get("enabled", True):
            raise MCPError("MCP server is disabled")
        known_tools = {
            str(tool.get("name") or "")
            for tool in server.get("tools", [])
            if isinstance(tool, dict)
        }
        if tool_name not in known_tools:
            raise MCPError("MCP tool is not in the discovered tool list")
        return self._run_sync(lambda: self._call_async(server, tool_name, arguments))

    def set_tool_policy(
        self,
        server_id: str,
        tool_name: str,
        *,
        enabled: bool,
        roles: list[str],
        approval: str,
    ) -> dict[str, Any]:
        server = self.get(server_id)
        if server is None:
            raise MCPError("MCP server not found")
        if tool_name not in {
            str(tool.get("name") or "") for tool in server.get("tools", [])
        }:
            raise MCPError("MCP tool not found")
        mode = approval.strip().lower()
        if mode not in MCP_APPROVAL_MODES:
            raise MCPError("approval must be auto or ask")
        policies = dict(server.get("tool_policies") or {})
        policies[tool_name] = {
            "enabled": bool(enabled),
            "roles": self._clean_roles(roles),
            "approval": mode,
        }
        server["tool_policies"] = policies
        return self.save(server, server_id=server_id)

    def agent_tool_policy(
        self,
        server_id: str,
        tool_name: str,
        role_name: str,
    ) -> dict[str, Any]:
        server = self.get(server_id)
        if server is None:
            raise MCPError("MCP server not found")
        if not server.get("enabled", True):
            raise MCPError("MCP server is disabled")
        if not server.get("allow_agent_calls", False):
            raise MCPError("MCP agent calls are disabled for this server")
        if not server.get("last_test", {}).get("ok"):
            raise MCPError("MCP server must pass its connection test first")
        tool = next(
            (
                item for item in server.get("tools", [])
                if str(item.get("name") or "") == tool_name
            ),
            None,
        )
        if tool is None:
            raise MCPError("MCP tool not found")
        policy = (server.get("tool_policies") or {}).get(tool_name)
        if not isinstance(policy, dict):
            policy = self._default_tool_policy(tool, server.get("roles") or [])
        role = role_name.strip().lower()
        if not policy.get("enabled", True):
            raise MCPError("MCP tool is disabled")
        if role not in self._clean_roles(policy.get("roles")):
            raise MCPError(f"MCP tool is not assigned to {role_name}")
        return {
            **policy,
            "server_id": server_id,
            "server_name": server.get("name") or server_id,
            "tool": tool,
        }

    def agent_context(self, _content: str, role_name: str) -> tuple[str, list[dict[str, Any]]]:
        role = role_name.strip().lower()
        servers = [
            server
            for server in self.list()
            if server.get("enabled", True)
            and server.get("allow_agent_calls", False)
            and server.get("last_test", {}).get("ok")
            and server.get("tools")
        ]
        if not servers:
            return "", []
        lines = [
            f"Available MCP tools for {role_name}:",
            "If a tool is needed, output only <tool_call>{JSON}</tool_call> and wait for its result.",
            "The JSON must contain server_id, tool, and arguments. Use only the tools listed below.",
        ]
        details: list[dict[str, Any]] = []
        for server in servers:
            available_tools: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for tool in server.get("tools", []):
                name = str(tool.get("name") or "")
                policy = (server.get("tool_policies") or {}).get(name)
                if not isinstance(policy, dict):
                    policy = self._default_tool_policy(tool, server.get("roles") or [])
                if not policy.get("enabled", True):
                    continue
                if role not in self._clean_roles(policy.get("roles")):
                    continue
                available_tools.append((tool, policy))
            if not available_tools:
                continue
            lines.append(f"\nServer {server['id']} ({server['name']}):")
            instructions = str((server.get("server_metadata") or {}).get("instructions") or "").strip()
            if instructions:
                lines.append(f"Server guidance: {instructions[:1000]}")
            for tool, policy in available_tools:
                lines.append(
                    f"- {tool.get('name')}: {tool.get('description', '')} "
                    f"Risk: {tool.get('risk', 'unknown')}. "
                    f"Approval: {policy.get('approval', 'ask')}. "
                    f"Input schema: {json.dumps(tool.get('input_schema') or {}, ensure_ascii=False)}"
                )
                details.append({
                    "server_id": server["id"],
                    "tool": tool.get("name", ""),
                    "approval": policy.get("approval", "ask"),
                    "risk": tool.get("risk", "unknown"),
                })
        return ("\n".join(lines), details) if details else ("", [])
