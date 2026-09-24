"""Versioned, atomic local conversation persistence for the Web UI."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any

MAX_SESSIONS = 200
MAX_MESSAGES = 2000
MAX_BYTES = 10 * 1024 * 1024


def validate_sessions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_SESSIONS:
        raise ValueError("Expected at most 200 conversations")
    result = []
    ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Invalid conversation")
        session_id = item.get("id")
        if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session_id) or session_id in ids:
            raise ValueError("Invalid or duplicate conversation ID")
        ids.add(session_id)
        messages = item.get("messages", [])
        if not isinstance(messages, list) or len(messages) > MAX_MESSAGES:
            raise ValueError("Conversation has too many messages")
        for message in messages:
            if not isinstance(message, dict) or message.get("role") not in {"user", "assistant", "error", "hermes", "hephaestus", "athena", "apollo", "chronos"}:
                raise ValueError("Invalid message")
            if not isinstance(message.get("text"), str) or len(message["text"]) > 200_000:
                raise ValueError("Invalid message text")
        if not isinstance(item.get("title"), str) or len(item["title"]) > 200:
            raise ValueError("Invalid conversation title")
        if not isinstance(item.get("mode"), str) or len(item["mode"]) > 100:
            raise ValueError("Invalid conversation mode")
        if not isinstance(item.get("overrides", {}), dict):
            raise ValueError("Invalid model overrides")
        for field in ("createdAt", "updatedAt"):
            if type(item.get(field)) is not int or item[field] < 0:
                raise ValueError("Invalid conversation date")
        result.append(item)
    return result


class ConversationStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    @staticmethod
    def _read_file(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Unsupported conversation format")
        validate_sessions(data.get("sessions"))
        return data

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            backup = self.path.with_suffix(".json.bak")
            if backup.exists():
                return self._read_file(backup)
            return {"schema_version": 1, "revision": "", "sessions": []}
        try:
            return self._read_file(self.path)
        except (ValueError, json.JSONDecodeError):
            backup = self.path.with_suffix(".json.bak")
            if not backup.exists():
                raise
            return self._read_file(backup)

    def get(self) -> dict[str, Any]:
        with self._lock:
            return self._read()

    def replace(self, sessions: Any, expected_revision: str) -> dict[str, Any] | None:
        validated = validate_sessions(sessions)
        payload = {"schema_version": 1, "revision": uuid.uuid4().hex, "sessions": validated}
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_BYTES:
            raise ValueError("Conversations exceed 10 MB")
        with self._lock:
            current = self._read()
            if current["revision"] != expected_revision:
                return None
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
            try:
                with temp.open("wb") as file:
                    os.chmod(temp, 0o600)
                    file.write(encoded)
                    file.flush()
                    os.fsync(file.fileno())
                if self.path.exists():
                    backup = self.path.with_suffix(".json.bak")
                    # Retain the last valid snapshot, even if the main file was damaged.
                    backup_temp = backup.with_name(f".{backup.name}.{uuid.uuid4().hex}.tmp")
                    try:
                        with backup_temp.open("w", encoding="utf-8") as backup_file:
                            os.chmod(backup_temp, 0o600)
                            json.dump(current, backup_file, ensure_ascii=False)
                            backup_file.flush()
                            os.fsync(backup_file.fileno())
                        os.replace(backup_temp, backup)
                    finally:
                        backup_temp.unlink(missing_ok=True)
                os.replace(temp, self.path)
            finally:
                temp.unlink(missing_ok=True)
        return payload
