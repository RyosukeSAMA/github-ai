"""Athena: goddess of wisdom. Does research and information gathering."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from pantheon.core.base import Role, Task, TaskResult, time_ms

log = logging.getLogger(__name__)


ATHENA_SYSTEM_PROMPT = """You are Athena, the Greek goddess of wisdom, strategy, and craft.
You are a senior research analyst with deep knowledge of science, history, technology, and current events.

Operating principles:
- Be accurate. Distinguish what you know from what you're inferring.
- Cite sources when making factual claims (URLs, paper titles, etc.).
- When uncertain, say "I'm not certain; here's what I do know...".
- Structure longer answers with clear sections.
- For comparisons, use tables.
- For trends, give dates and figures, not vague impressions.
- You can use web_search and web_extract to verify facts.

You focus on: research synthesis, literature reviews, fact-checking, comparisons, summaries.
You do NOT: write code (ask Hephaestus), generate images (ask Apollo), or schedule tasks (ask Chronos).
"""


class Athena(Role):
    name = "athena"
    description = "Researches and gathers information; fact-checks; summarizes"
    default_model = "gpt-4o"
    default_provider = "openai"
    default_temperature = 0.3
    tools: List[str] = ["web_search", "web_extract"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("system_prompt", ATHENA_SYSTEM_PROMPT)
        super().__init__(*args, **kwargs)

    def run(self, task: Task, context: Optional[List[dict]] = None) -> TaskResult:
        start = time_ms()
        context_block = self._format_context(context)

        user_prompt = (
            f"Research request:\n{task.content}\n\n{context_block}"
            if context_block
            else f"Research request:\n{task.content}"
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
            log.exception("Athena run failed")
            return TaskResult(
                role=self.name,
                content=f"[Athena] Error: {e}",
                success=False,
                error=str(e),
                duration_ms=time_ms() - start,
            )
