"""Hephaestus: the smith god. Writes and refactors code."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from pantheon.core.base import Role, Task, TaskResult, time_ms

log = logging.getLogger(__name__)


HEPHAESTUS_SYSTEM_PROMPT = """You are Hephaestus, the Greek god of the forge, fire, and craftsmanship.
You are a 20-year veteran software engineer. You write clean, correct, production-ready code.

Operating principles:
- Read the task carefully. Don't assume.
- Write minimal, focused code. No premature abstraction.
- Match the existing code style when refactoring.
- Prefer standard library; justify any external dependency.
- Always explain what you built and why, in concise prose.
- If you are unsure, say so explicitly. Do not invent APIs.
- For refactors, preserve existing behavior unless asked otherwise.
- Output code in fenced blocks with the language tag.

You focus on: Python, JavaScript/TypeScript, Go, Rust, and Bash.
You do NOT: do web research (ask Athena), generate images (ask Apollo), or schedule tasks (ask Chronos).
"""


class Hephaestus(Role):
    name = "hephaestus"
    description = "Writes and refactors code (Python, JS/TS, Go, Rust, Bash)"
    default_model = "claude-sonnet-4-20250514"
    default_provider = "anthropic"
    default_temperature = 0.1
    tools: List[str] = ["terminal", "file", "patch"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("system_prompt", HEPHAESTUS_SYSTEM_PROMPT)
        super().__init__(*args, **kwargs)

    def run(self, task: Task, context: Optional[List[dict]] = None) -> TaskResult:
        start = time_ms()
        context_block = self._format_context(context)

        user_prompt = (
            f"Task:\n{task.content}\n\n{context_block}"
            if context_block
            else f"Task:\n{task.content}"
        )

        try:
            content = self._make_llm_call(
                messages=[{"role": "user", "content": user_prompt}]
            )
            return TaskResult(
                role=self.name,
                content=content,
                success=True,
                duration_ms=time_ms() - start,
                metadata={"model": self.model, "provider": self.default_provider},
            )
        except Exception as e:
            log.exception("Hephaestus run failed")
            return TaskResult(
                role=self.name,
                content=f"[Hephaestus] Error: {e}",
                success=False,
                error=str(e),
                duration_ms=time_ms() - start,
            )
