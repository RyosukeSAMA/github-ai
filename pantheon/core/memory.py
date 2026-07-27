"""Local long-term memory store for Pantheon."""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MEMORY_KINDS = {"note", "user_profile", "project", "agent", "task"}
DEFAULT_MEMORY_ROLES = {"", "global", "hermes", "hephaestus", "athena", "apollo", "chronos"}
DEFAULT_SUGGESTION_STATUSES = {"pending", "saved", "ignored"}

ROLE_ALIASES = {
    "hermes": ("hermes", "赫尔墨斯", "路由", "规划"),
    "hephaestus": ("hephaestus", "he", "赫菲斯托斯", "火神", "代码", "开发", "实现"),
    "athena": ("athena", "雅典娜", "调研", "研究", "分析"),
    "apollo": ("apollo", "阿波罗", "表达", "文案", "创意", "润色"),
    "chronos": ("chronos", "克洛诺斯", "定时", "提醒", "调度"),
}

EXPLICIT_MEMORY_PATTERNS = (
    r"^\s*(?:请)?(?:你)?帮我记住[：:,，]?\s*(?P<content>.+)$",
    r"^\s*(?:请)?记住[：:,，]?\s*(?P<content>.+)$",
    r"^\s*(?:你要|需要)?记得[：:,，]?\s*(?P<content>.+)$",
    r"^\s*(?:please\s+)?remember(?:\s+that)?[:,]?\s*(?P<content>.+)$",
    r"^\s*keep\s+in\s+mind[:,]?\s*(?P<content>.+)$",
    r"^\s*(?:以后|之后|从现在开始)(?:都|请|帮我|回答|代码|默认)?[：:,，]?\s*(?P<content>.+)$",
    r"^\s*(?:我的偏好|我的习惯|我偏好)(?:是|：|:)?\s*(?P<content>.+)$",
    r"^\s*(?:我喜欢|我不喜欢|我希望|我更喜欢)\s*(?P<content>.+)$",
)

SUGGESTION_KEYWORDS = (
    "项目叫",
    "项目是",
    "本项目",
    "当前项目",
    "这个项目",
    "产品是",
    "技术栈",
    "架构",
    "代码风格",
    "ui 风格",
    "ui风格",
    "设计风格",
    "写代码",
    "回答风格",
    "规范",
    "约定",
    "偏好",
    "习惯",
    "默认使用",
    "用的是",
    "使用的是",
    "Pantheon",
    "agent",
    "github",
    "repository",
    "repo",
    "project",
    "preference",
    "convention",
    "style",
)

QUESTION_HINTS = (
    "?",
    "？",
    "如何",
    "怎么",
    "为什么",
    "什么",
    "是否",
    "能否",
    "how ",
    "what ",
    "why ",
    "can ",
    "could ",
)


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    content: str
    kind: str
    source: str
    role: str
    tags: list[str]
    created_at: float
    updated_at: float
    last_used_at: float | None
    usage_count: int


@dataclass(frozen=True)
class MemorySuggestion:
    id: str
    content: str
    kind: str
    source: str
    role: str
    reason: str
    status: str
    created_at: float
    updated_at: float


def _now() -> float:
    return time.time()


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[\w\u4e00-\u9fff]{2,}", text or "")
        if token.strip()
    }


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    tags_raw = row["tags"] or "[]"
    try:
        tags = json.loads(tags_raw)
    except json.JSONDecodeError:
        tags = []
    return {
        "id": row["id"],
        "content": row["content"],
        "kind": row["kind"],
        "source": row["source"],
        "role": row["role"] or "",
        "tags": tags if isinstance(tags, list) else [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_used_at": row["last_used_at"],
        "usage_count": row["usage_count"],
    }


def _row_to_suggestion(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "content": row["content"],
        "kind": row["kind"],
        "source": row["source"],
        "role": row["role"] or "",
        "reason": row["reason"] or "",
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def normalize_memory_role(role: str | None) -> str:
    clean = (role or "").strip().lower()
    if clean in {"", "global", "all"}:
        return ""
    return clean if clean in DEFAULT_MEMORY_ROLES else ""


def classify_memory_text(text: str) -> tuple[str, str]:
    lowered = (text or "").lower()
    role = ""
    for role_name, aliases in ROLE_ALIASES.items():
        if any(alias.lower() in lowered for alias in aliases):
            role = role_name
            break

    if role:
        return "agent", role
    if any(word in text for word in ("项目", "产品", "架构", "技术栈")) or any(
        word in lowered for word in ("repo", "repository", "pantheon", "project")
    ):
        return "project", ""
    if any(word in text for word in ("我喜欢", "我不喜欢", "我希望", "偏好", "习惯", "中文")) or any(
        word in lowered for word in ("english", "prefer", "preference")
    ):
        return "user_profile", ""
    return "note", ""


def _clean_detected_content(text: str) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip(" \t\r\n:：,，。")
    return clean[:1000]


def detect_memory_candidate(text: str) -> dict[str, str] | None:
    """Detect explicit or suggested memory from a user message.

    This is intentionally conservative and rule-based so local users do not
    spend model tokens just to decide whether something should be remembered.
    """
    clean = _clean_detected_content(text)
    if len(clean) < 6 or len(clean) > 1200:
        return None

    for pattern in EXPLICIT_MEMORY_PATTERNS:
        match = re.match(pattern, clean, flags=re.IGNORECASE)
        if not match:
            continue
        content = _clean_detected_content(match.group("content"))
        if len(content) < 3:
            return None
        kind, role = classify_memory_text(content)
        return {
            "action": "save",
            "content": content,
            "kind": kind,
            "role": role,
            "source": "detected",
            "reason": "explicit memory intent",
        }

    lowered = clean.lower()
    if any(hint in lowered for hint in QUESTION_HINTS):
        return None
    if not any(keyword.lower() in lowered for keyword in SUGGESTION_KEYWORDS):
        return None
    kind, role = classify_memory_text(clean)
    return {
        "action": "suggest",
        "content": clean,
        "kind": kind,
        "role": role,
        "source": "suggested",
        "reason": "stable project or preference detail",
    }


class MemoryStore:
    """Tiny SQLite-backed memory store.

    The first version intentionally uses local keyword search instead of a vector
    index so it works for new users without extra API keys or services.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'note',
                source TEXT NOT NULL DEFAULT 'manual',
                role TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_used_at REAL,
                usage_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_suggestions (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'note',
                source TEXT NOT NULL DEFAULT 'suggested',
                role TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_role ON memories(role)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories(updated_at)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_suggestions_status "
            "ON memory_suggestions(status)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO memory_settings(key, value) VALUES('enabled', 'true')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO memory_settings(key, value) VALUES('auto_capture', 'false')"
        )
        conn.commit()

    def settings(self) -> dict[str, bool]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM memory_settings").fetchall()
        values = {row["key"]: row["value"].lower() in {"1", "true", "yes", "on"} for row in rows}
        return {
            "enabled": values.get("enabled", True),
            "auto_capture": values.get("auto_capture", False),
        }

    def set_settings(self, *, enabled: bool | None = None, auto_capture: bool | None = None) -> dict[str, bool]:
        updates = {}
        if enabled is not None:
            updates["enabled"] = "true" if enabled else "false"
        if auto_capture is not None:
            updates["auto_capture"] = "true" if auto_capture else "false"
        if updates:
            with self._connect() as conn:
                for key, value in updates.items():
                    conn.execute(
                        "INSERT INTO memory_settings(key, value) VALUES(?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, value),
                    )
                conn.commit()
        return self.settings()

    def add(
        self,
        content: str,
        *,
        kind: str = "note",
        source: str = "manual",
        role: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        clean = re.sub(r"\s+", " ", content or "").strip()
        if not clean:
            raise ValueError("memory content is required")
        memory_kind = kind if kind in DEFAULT_MEMORY_KINDS else "note"
        memory_role = normalize_memory_role(role)
        now = _now()
        item_id = uuid.uuid4().hex[:12]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories(
                    id, content, kind, source, role, tags, created_at, updated_at,
                    last_used_at, usage_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 0)
                """,
                (
                    item_id,
                    clean[:4000],
                    memory_kind,
                    source[:80],
                    memory_role[:80],
                    json.dumps(tags or [], ensure_ascii=False),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get(item_id) or {}

    def get(self, memory_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list(
        self,
        *,
        query: str = "",
        kind: str = "",
        role: str = "",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        normalized_role = normalize_memory_role(role)
        if role:
            if normalized_role:
                clauses.append("role = ?")
                params.append(normalized_role)
            else:
                clauses.append("(role = '' OR role = 'global')")
        if query:
            clauses.append("content LIKE ?")
            params.append(f"%{query}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(limit, 200)))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM memories {where} ORDER BY updated_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def search(self, query: str, *, role: str = "", limit: int = 6) -> list[dict[str, Any]]:
        if not self.settings()["enabled"]:
            return []
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        normalized_role = normalize_memory_role(role)
        allowed_roles = {""}
        if normalized_role:
            allowed_roles.add(normalized_role)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY updated_at DESC LIMIT 200"
            ).fetchall()
        scored: list[tuple[float, dict[str, Any]]] = []
        now = _now()
        for row in rows:
            item = _row_to_record(row)
            item_role = normalize_memory_role(item["role"])
            if item_role not in allowed_roles:
                continue
            content_tokens = _tokens(item["content"])
            content_lower = item["content"].lower()
            direct_matches = query_tokens & content_tokens
            partial_matches = {token for token in query_tokens if token in content_lower}
            overlap = len(direct_matches | partial_matches)
            if not overlap:
                continue
            age_days = max(0.0, (now - float(item["updated_at"])) / 86400)
            recency = 1 / (1 + age_days / 30)
            score = overlap * 2 + min(int(item["usage_count"] or 0), 5) * 0.2 + recency
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        selected = [item for _, item in scored[: max(1, min(limit, 20))]]
        if selected:
            self.mark_used([item["id"] for item in selected])
        return selected

    def context_block(
        self,
        query: str,
        *,
        role: str = "",
        limit: int = 6,
    ) -> tuple[str, list[dict[str, Any]]]:
        memories = self.search(query, role=role, limit=limit)
        if not memories:
            return "", []
        role_label = normalize_memory_role(role) or "global"
        lines = [
            f"Relevant long-term memories from Pantheon Memory for {role_label}:",
            *[
                f"- [{item['kind']}{'/' + item['role'] if item['role'] else '/global'}] {item['content']}"
                for item in memories
            ],
            "",
            "Use these memories only when relevant. Do not reveal memory IDs unless asked.",
        ]
        return "\n".join(lines), memories

    def suggest(
        self,
        content: str,
        *,
        kind: str = "note",
        source: str = "suggested",
        role: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        clean = re.sub(r"\s+", " ", content or "").strip()
        if not clean:
            raise ValueError("suggestion content is required")
        memory_kind = kind if kind in DEFAULT_MEMORY_KINDS else "note"
        memory_role = normalize_memory_role(role)
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT * FROM memory_suggestions
                WHERE status = 'pending' AND content = ? AND role = ?
                """,
                (clean[:4000], memory_role),
            ).fetchone()
            if existing:
                return _row_to_suggestion(existing)

            existing_memory = conn.execute(
                "SELECT * FROM memories WHERE content = ? AND role = ? LIMIT 1",
                (clean[:4000], memory_role),
            ).fetchone()
            if existing_memory:
                item = _row_to_record(existing_memory)
                return {
                    "id": item["id"],
                    "content": item["content"],
                    "kind": item["kind"],
                    "source": "existing",
                    "role": item["role"],
                    "reason": "already saved",
                    "status": "saved",
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                }

            now = _now()
            item_id = uuid.uuid4().hex[:12]
            conn.execute(
                """
                INSERT INTO memory_suggestions(
                    id, content, kind, source, role, reason, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    item_id,
                    clean[:4000],
                    memory_kind,
                    source[:80],
                    memory_role[:80],
                    reason[:240],
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_suggestion(item_id) or {}

    def get_suggestion(self, suggestion_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memory_suggestions WHERE id = ?",
                (suggestion_id,),
            ).fetchone()
        return _row_to_suggestion(row) if row else None

    def suggestions(
        self,
        *,
        status: str = "pending",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        suggestion_status = status if status in DEFAULT_SUGGESTION_STATUSES else "pending"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM memory_suggestions
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (suggestion_status, max(1, min(limit, 200))),
            ).fetchall()
        return [_row_to_suggestion(row) for row in rows]

    def accept_suggestion(self, suggestion_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise KeyError("suggestion not found")
        item = self.add(
            suggestion["content"],
            kind=suggestion["kind"],
            source="suggested",
            role=suggestion["role"],
        )
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE memory_suggestions
                SET status = 'saved', updated_at = ?
                WHERE id = ?
                """,
                (now, suggestion_id),
            )
            conn.commit()
        saved_suggestion = self.get_suggestion(suggestion_id) or suggestion
        return item, saved_suggestion

    def ignore_suggestion(self, suggestion_id: str) -> bool:
        now = _now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE memory_suggestions
                SET status = 'ignored', updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (now, suggestion_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def mark_used(self, memory_ids: list[str]) -> None:
        if not memory_ids:
            return
        placeholders = ",".join("?" for _ in memory_ids)
        with self._connect() as conn:
            conn.execute(
                f"""
                UPDATE memories
                SET usage_count = usage_count + 1, last_used_at = ?, updated_at = updated_at
                WHERE id IN ({placeholders})
                """,
                [_now(), *memory_ids],
            )
            conn.commit()

    def delete(self, memory_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cur.rowcount > 0

    def clear(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memories")
            conn.commit()
            return cur.rowcount

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"]
            rows = conn.execute(
                "SELECT kind, COUNT(*) AS c FROM memories GROUP BY kind ORDER BY kind"
            ).fetchall()
            pending = conn.execute(
                "SELECT COUNT(*) AS c FROM memory_suggestions WHERE status = 'pending'"
            ).fetchone()["c"]
        return {
            "count": int(total),
            "pending_suggestions": int(pending),
            "by_kind": {row["kind"]: int(row["c"]) for row in rows},
            "db_path": str(self.db_path),
            **self.settings(),
        }
