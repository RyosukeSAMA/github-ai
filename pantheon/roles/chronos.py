"""Chronos: god of time. Schedules and runs periodic tasks. No LLM."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pantheon.core.base import Role, Task, TaskResult, time_ms
from pantheon.core.scheduler import ScheduleParseError, parse_schedule_request

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
    tools: list[str] = ["cronjob"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("system_prompt", CHRONOS_SYSTEM_PROMPT)
        super().__init__(*args, **kwargs)

    def run(self, task: Task, context: list[dict] | None = None) -> TaskResult:
        """Interpret scheduling intent and create a local scheduled job when possible."""
        start = time_ms()
        try:
            scheduler = self.config.get("scheduler") if isinstance(self.config, dict) else None
            spec = parse_schedule_request(task.content)
            job = scheduler.add_job(spec) if scheduler is not None else None

            if job:
                next_run = job.get("next_run_at_iso") or "not scheduled"
                content = (
                    "[Chronos] Scheduled task created.\n"
                    f"- Job: {job['title']}\n"
                    f"- Schedule: {job['schedule_type']}\n"
                    f"- Next run: {next_run}\n"
                    f"- Mode: {job.get('mode', 'auto')}\n"
                    f"- Job ID: {job['id']}"
                )
                metadata = {
                    "scheduled": True,
                    "job": job,
                    "scheduled_at": datetime.utcnow().isoformat(),
                }
            else:
                content = (
                    "[Chronos] Schedule parsed.\n"
                    f"- Task: {spec.prompt}\n"
                    f"- Schedule: {spec.schedule_type}\n"
                    f"- Next run: {datetime.fromtimestamp(spec.run_at).isoformat() if spec.run_at else 'not scheduled'}\n\n"
                    "This Chronos instance has no scheduler attached, so no job was persisted."
                )
                metadata = {
                    "scheduled": False,
                    "schedule": spec.__dict__,
                    "scheduled_at": datetime.utcnow().isoformat(),
                }

            return TaskResult(
                role=self.name,
                content=content,
                success=True,
                duration_ms=time_ms() - start,
                metadata=metadata,
            )
        except ScheduleParseError as e:
            content = (
                "[Chronos] I could not create a schedule from that request.\n"
                f"- Reason: {e}\n\n"
                "Try one of these forms:\n"
                "- every 10 minutes, remind me to drink water\n"
                "- in 30 minutes, ask Athena to summarize my notes\n"
                "- daily at 09:00, ask Apollo to draft a status message\n"
                "- 每天 9:00 提醒我查看任务"
            )
            return TaskResult(
                role=self.name,
                content=content,
                success=False,
                error=str(e),
                duration_ms=time_ms() - start,
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
