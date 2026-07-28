"""Small local scheduler used by Chronos and the web UI."""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class ScheduleParseError(ValueError):
    """Raised when Chronos cannot parse a schedule request."""


@dataclass(frozen=True)
class ScheduleSpec:
    """Parsed scheduling intent."""

    prompt: str
    schedule_type: str
    title: str
    mode: str = "auto"
    interval_seconds: int | None = None
    run_at: float | None = None
    hour: int | None = None
    minute: int | None = None
    original_text: str = ""


ROLE_ALIASES = {
    "hephaestus": ("hephaestus", "he", "赫菲斯托斯", "火神", "代码", "写代码"),
    "athena": ("athena", "ath", "雅典娜", "研究", "调研", "搜索"),
    "apollo": ("apollo", "apo", "阿波罗", "创意", "文案", "图片"),
}

UNIT_SECONDS = {
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
    "秒": 1,
    "分钟": 60,
    "分": 60,
    "小时": 3600,
    "天": 86400,
    "日": 86400,
}


def local_now() -> datetime:
    return datetime.now().astimezone()


def iso_from_ts(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=local_now().tzinfo).isoformat(timespec="seconds")


def _title_from_prompt(prompt: str) -> str:
    text = re.sub(r"\s+", " ", prompt).strip()
    return text[:48] or "Scheduled task"


def _seconds(value: str | None, unit: str) -> int:
    amount = int(value or "1")
    return amount * UNIT_SECONDS[unit.lower()]


def _parse_time(hour_text: str, minute_text: str | None = None, meridiem: str | None = None) -> tuple[int, int]:
    hour = int(hour_text)
    minute = int(minute_text or "0")
    marker = (meridiem or "").lower()
    if marker == "pm" and hour < 12:
        hour += 12
    if marker == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        raise ScheduleParseError("time must be between 00:00 and 23:59")
    return hour, minute


def _next_daily_run(hour: int, minute: int, now: datetime | None = None) -> float:
    current = now or local_now()
    candidate = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= current:
        candidate += timedelta(days=1)
    return candidate.timestamp()


def _once_at(hour: int, minute: int, tomorrow: bool = False, now: datetime | None = None) -> float:
    current = now or local_now()
    candidate = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if tomorrow:
        candidate += timedelta(days=1)
    elif candidate <= current:
        candidate += timedelta(days=1)
    return candidate.timestamp()


def _clean_prompt(text: str, span: tuple[int, int]) -> str:
    prompt = (text[: span[0]] + " " + text[span[1] :]).strip()
    prompt = re.sub(r"^[\s,，、;；:：]+", "", prompt)
    prompt = re.sub(r"^(then|please|to)\s+", "", prompt, flags=re.I)
    prompt = re.sub(r"^(请|帮我|让|叫|提醒我)\s*", "", prompt)
    prompt = re.sub(r"\s+", " ", prompt).strip()
    return prompt or text.strip()


def _alias_in_text(alias: str, lowered_text: str) -> bool:
    lowered_alias = alias.lower()
    if re.fullmatch(r"[a-z][a-z0-9_-]*", lowered_alias):
        return re.search(rf"\b{re.escape(lowered_alias)}\b", lowered_text) is not None
    return lowered_alias in lowered_text


def _extract_role(prompt: str) -> tuple[str, str]:
    lowered = prompt.lower()
    mode = "auto"
    for role, aliases in ROLE_ALIASES.items():
        if any(_alias_in_text(alias, lowered) for alias in aliases):
            mode = f"role:{role}"
            break
    cleaned = re.sub(r"^(ask|let)\s+(hephaestus|athena|apollo)\s+(to\s+)?", "", prompt, flags=re.I)
    cleaned = re.sub(r"^(让|叫)\s*(赫菲斯托斯|火神|雅典娜|阿波罗)\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return mode, cleaned or prompt


def parse_schedule_request(text: str, now: datetime | None = None) -> ScheduleSpec:
    """Parse a limited but useful set of local scheduling expressions.

    Supported examples:
    - every 10 seconds, remind me to drink water
    - 每5分钟提醒我喝水
    - in 30 minutes, ask Athena to summarize notes
    - 10分钟后提醒我开会
    - daily at 09:00, ask Apollo to draft a post
    - 每天 9:30 提醒我查看任务
    - at 18:00, remind me to stop work
    """

    raw = text.strip()
    if not raw:
        raise ScheduleParseError("schedule request is empty")
    current = now or local_now()

    patterns: list[tuple[str, str]] = [
        ("interval", r"\bevery\s+(\d+)?\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d)\b"),
        ("interval", r"每(?:隔)?\s*(\d+)?\s*(秒|分钟|分|小时|天|日)"),
        ("relative", r"\bin\s+(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d)\b"),
        ("relative", r"(\d+)\s*(秒|分钟|分|小时|天|日)\s*后"),
        ("daily", r"\b(?:daily|every day)\s+(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b"),
        ("daily", r"每天.*?(\d{1,2})(?:[:：点](\d{1,2}))?\s*(?:分)?"),
        ("at", r"\b(today|tomorrow)?\s*(?:at\s+)?(\d{1,2}):(\d{2})\s*(am|pm)?\b"),
        ("at", r"(今天|明天)?\s*(\d{1,2})[:：点](\d{1,2})?\s*(?:分)?"),
    ]

    for kind, pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if not match:
            continue
        prompt = _clean_prompt(raw, match.span())
        mode, prompt = _extract_role(prompt)
        title = _title_from_prompt(prompt)

        if kind == "interval":
            interval_seconds = _seconds(match.group(1), match.group(2))
            if interval_seconds < 5:
                raise ScheduleParseError("interval must be at least 5 seconds")
            return ScheduleSpec(
                prompt=prompt,
                schedule_type="interval",
                title=title,
                mode=mode,
                interval_seconds=interval_seconds,
                run_at=current.timestamp() + interval_seconds,
                original_text=raw,
            )

        if kind == "relative":
            interval_seconds = _seconds(match.group(1), match.group(2))
            return ScheduleSpec(
                prompt=prompt,
                schedule_type="once",
                title=title,
                mode=mode,
                run_at=current.timestamp() + interval_seconds,
                original_text=raw,
            )

        if kind == "daily":
            hour, minute = _parse_time(match.group(1), match.group(2), match.group(3) if len(match.groups()) >= 3 else None)
            return ScheduleSpec(
                prompt=prompt,
                schedule_type="daily",
                title=title,
                mode=mode,
                hour=hour,
                minute=minute,
                run_at=_next_daily_run(hour, minute, current),
                original_text=raw,
            )

        if kind == "at":
            marker = (match.group(1) or "").lower()
            hour, minute = _parse_time(match.group(2), match.group(3), match.group(4) if len(match.groups()) >= 4 else None)
            tomorrow = marker in {"tomorrow", "明天"}
            return ScheduleSpec(
                prompt=prompt,
                schedule_type="once",
                title=title,
                mode=mode,
                run_at=_once_at(hour, minute, tomorrow, current),
                original_text=raw,
            )

    raise ScheduleParseError(
        "I can schedule simple forms like `every 10 minutes ...`, `in 30 minutes ...`, `daily at 09:00 ...`, or `每天 9:00 ...`."
    )


class ChronosScheduler:
    """Persistent local scheduler with a tiny asyncio runner."""

    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        self._lock = threading.RLock()
        self._data: dict[str, Any] | None = None

    def _empty_data(self) -> dict[str, Any]:
        return {"jobs": [], "runs": []}

    def _load(self) -> dict[str, Any]:
        if self._data is not None:
            return self._data
        if not self.store_path.exists():
            self._data = self._empty_data()
            return self._data
        try:
            self._data = json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            self._data = self._empty_data()
        self._data.setdefault("jobs", [])
        self._data.setdefault("runs", [])
        return self._data

    def _save(self) -> None:
        if self._data is None:
            return
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _public_job(self, job: dict[str, Any]) -> dict[str, Any]:
        item = dict(job)
        item["next_run_at_iso"] = iso_from_ts(item.get("next_run_at"))
        item["last_run_at_iso"] = iso_from_ts(item.get("last_run_at"))
        item["created_at_iso"] = iso_from_ts(item.get("created_at"))
        return item

    def _public_run(self, run: dict[str, Any]) -> dict[str, Any]:
        item = dict(run)
        item["started_at_iso"] = iso_from_ts(item.get("started_at"))
        item["finished_at_iso"] = iso_from_ts(item.get("finished_at"))
        return item

    def add_job(self, spec: ScheduleSpec) -> dict[str, Any]:
        now_ts = time.time()
        job = {
            "id": uuid.uuid4().hex[:10],
            "title": spec.title,
            "prompt": spec.prompt,
            "original_text": spec.original_text,
            "mode": spec.mode,
            "schedule_type": spec.schedule_type,
            "interval_seconds": spec.interval_seconds,
            "hour": spec.hour,
            "minute": spec.minute,
            "next_run_at": spec.run_at,
            "enabled": True,
            "running": False,
            "created_at": now_ts,
            "updated_at": now_ts,
            "run_count": 0,
            "last_status": "scheduled",
            "last_error": "",
            "last_output": "",
            "last_run_at": None,
        }
        with self._lock:
            data = self._load()
            data["jobs"].append(job)
            self._save()
        return self._public_job(job)

    def add_job_from_text(self, text: str) -> dict[str, Any]:
        return self.add_job(parse_schedule_request(text))

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            data = self._load()
            jobs = sorted(data["jobs"], key=lambda item: item.get("created_at", 0), reverse=True)
            return [self._public_job(job) for job in jobs]

    def list_runs(self, job_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            data = self._load()
            runs = data["runs"]
            if job_id:
                runs = [run for run in runs if run.get("job_id") == job_id]
            runs = sorted(runs, key=lambda item: item.get("started_at", 0), reverse=True)[:limit]
            return [self._public_run(run) for run in runs]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            data = self._load()
            for job in data["jobs"]:
                if job.get("id") == job_id:
                    return self._public_job(job)
        return None

    def set_enabled(self, job_id: str, enabled: bool) -> dict[str, Any]:
        with self._lock:
            data = self._load()
            for job in data["jobs"]:
                if job.get("id") != job_id:
                    continue
                job["enabled"] = enabled
                job["updated_at"] = time.time()
                if enabled and not job.get("next_run_at"):
                    job["next_run_at"] = self._next_run(job, time.time())
                job["last_status"] = "scheduled" if enabled else "paused"
                self._save()
                return self._public_job(job)
        raise KeyError(job_id)

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            data = self._load()
            before = len(data["jobs"])
            data["jobs"] = [job for job in data["jobs"] if job.get("id") != job_id]
            removed = len(data["jobs"]) != before
            if removed:
                data["runs"] = [run for run in data["runs"] if run.get("job_id") != job_id]
                self._save()
            return removed

    def claim_due_jobs(self, now_ts: float | None = None) -> list[dict[str, Any]]:
        current = now_ts or time.time()
        due: list[dict[str, Any]] = []
        with self._lock:
            data = self._load()
            for job in data["jobs"]:
                if not job.get("enabled") or job.get("running"):
                    continue
                next_run = job.get("next_run_at")
                if next_run is None or float(next_run) > current:
                    continue
                job["running"] = True
                job["last_status"] = "running"
                job["last_run_at"] = current
                job["updated_at"] = current
                due.append(dict(job))
                if job.get("schedule_type") == "once":
                    job["enabled"] = False
                    job["next_run_at"] = None
                else:
                    job["next_run_at"] = self._next_run(job, current)
            if due:
                self._save()
        return due

    def _next_run(self, job: dict[str, Any], after_ts: float) -> float | None:
        schedule_type = job.get("schedule_type")
        if schedule_type == "interval":
            interval = int(job.get("interval_seconds") or 60)
            return after_ts + interval
        if schedule_type == "daily":
            hour = int(job.get("hour") or 0)
            minute = int(job.get("minute") or 0)
            return _next_daily_run(hour, minute, datetime.fromtimestamp(after_ts, tz=local_now().tzinfo))
        return None

    def record_run(
        self,
        job_id: str,
        *,
        success: bool,
        output: str = "",
        error: str = "",
        started_at: float | None = None,
        finished_at: float | None = None,
        duration_ms: int = 0,
    ) -> dict[str, Any]:
        started = started_at or time.time()
        finished = finished_at or time.time()
        run = {
            "id": uuid.uuid4().hex[:10],
            "job_id": job_id,
            "success": success,
            "output": output[:2000],
            "error": error[:1000],
            "started_at": started,
            "finished_at": finished,
            "duration_ms": duration_ms,
        }
        with self._lock:
            data = self._load()
            data["runs"].append(run)
            data["runs"] = data["runs"][-200:]
            for job in data["jobs"]:
                if job.get("id") != job_id:
                    continue
                job["running"] = False
                job["run_count"] = int(job.get("run_count") or 0) + 1
                job["last_status"] = "done" if success else "error"
                job["last_output"] = output[:500]
                job["last_error"] = error[:500]
                job["updated_at"] = finished
                break
            self._save()
        return self._public_run(run)
