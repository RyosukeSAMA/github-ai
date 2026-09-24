"""Local accounting for provider-reported LLM usage (never prompts or keys)."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


def _token_count(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def usage_from_response(response: Any, *, responses_api: bool = False) -> dict[str, int | None]:
    """Normalize OpenAI-compatible and Anthropic response usage objects."""
    usage = getattr(response, "usage", None)
    input_name = "input_tokens" if responses_api else "prompt_tokens"
    output_name = "output_tokens" if responses_api else "completion_tokens"
    input_tokens = _token_count(getattr(usage, input_name, None))
    output_tokens = _token_count(getattr(usage, output_name, None))
    if input_tokens is None:
        input_tokens = _token_count(getattr(usage, "input_tokens", None))
    if output_tokens is None:
        output_tokens = _token_count(getattr(usage, "output_tokens", None))
    details = getattr(usage, "input_tokens_details", None) if responses_api else getattr(usage, "prompt_tokens_details", None)
    cached = _token_count(getattr(details, "cached_tokens", None))
    if cached is None:
        cached = _token_count(getattr(usage, "cache_read_input_tokens", None))
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "cached_input_tokens": cached}


class UsageStore:
    """SQLite-backed summary of successful model calls."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY, created_at INTEGER NOT NULL,
            provider TEXT NOT NULL, model TEXT NOT NULL,
            input_tokens INTEGER, output_tokens INTEGER, cached_input_tokens INTEGER
        )""")
        return db

    def record(self, provider: str, model: str, response: Any, *, responses_api: bool = False) -> None:
        counts = usage_from_response(response, responses_api=responses_api)
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO calls (created_at, provider, model, input_tokens, output_tokens, cached_input_tokens) VALUES (?, ?, ?, ?, ?, ?)",
                (int(time.time()), provider, model, counts["input_tokens"], counts["output_tokens"], counts["cached_input_tokens"]),
            )

    def summary(self, days: int = 30) -> dict[str, Any]:
        since = int(time.time()) - days * 86400
        with self._lock, self._connect() as db:
            rows = db.execute("""SELECT provider, model, COUNT(*),
                SUM(input_tokens), SUM(output_tokens), SUM(cached_input_tokens),
                COUNT(input_tokens) FROM calls WHERE created_at >= ?
                GROUP BY provider, model ORDER BY COUNT(*) DESC, provider, model""", (since,)).fetchall()
        models = [{"provider": r[0], "model": r[1], "calls": r[2],
                   "input_tokens": r[3] or 0, "output_tokens": r[4] or 0,
                   "cached_input_tokens": r[5] or 0, "metered_calls": r[6]} for r in rows]
        return {"days": days, "models": models,
                "totals": {key: sum(row[key] for row in models)
                           for key in ("calls", "input_tokens", "output_tokens", "cached_input_tokens", "metered_calls")}}
