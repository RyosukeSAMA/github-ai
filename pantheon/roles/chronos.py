"""Chronos: god of time. Schedules and runs periodic tasks. No LLM."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional

from pantheon.core.base import Role, Task, TaskResult, time_ms

log = logging.getLogger(__name__)


CHRONOS_SYSTEM_PROMPT = """You are Chronos, the personification of time in Greek mythology.
You are the scheduler. You do not write code or do research; you ensure things happen on time.

Operating principles:
- Be precise about timing and recurrence.
- Validate cron expressions before storing.
- Log clearly when tasks fire.
"""


class Chronos(Role):
    name = "chronos"
    description = "Schedules and runs periodic tasks (no LLM needed)"
    default_model = ""  # no LLM
    default_provider = ""
    default_temperature = 0.0
    tools: List[str] = ["cronjob"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("system_prompt", CHRONOS_SYSTEM_PROMPT)
        super().__init__(*args, **kwargs)

    def run(self, task: Task, context: Optional[List[dict]] = None) -> TaskResult:
        """Chronos doesn't actually call an LLM. It interprets scheduling intent.

        For v0.1 this returns a structured confirmation. Real cron scheduling
        can be plugged into the config (e.g. APScheduler) in a future version.
        """
        start = time_ms()
        try:
            content = (
                f"[Chronos] Received scheduling request:\n"
                f"  - Task: {task.content}\n"
                f"  - Received at: {datetime.utcnow().isoformat()}Z\n\n"
                f"Note: This is v0.1 — Chronos confirms the request but does not "
                f"persist a real cron job yet. Use the planned `cronjob` tool "
                f"(APScheduler integration) to enable actual scheduling."
            )
            return TaskResult(
                role=self.name,
                content=content,
                success=True,
                duration_ms=time_ms() - start,
                metadata={"scheduled_at": datetime.utcnow().isoformat()},
            )
        except Exception as e:
            log.exception("Chronos run failed")
            return TaskResult(
                role=self.name,
                content=f"[Chronos] Error: {e}",
                success=False,
                error=str(e),
                duration_ms=time_ms() - start,
            )
