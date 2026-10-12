from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pantheon.core.scheduler import ChronosScheduler, parse_schedule_request


def test_parse_interval_schedule() -> None:
    now = datetime(2026, 7, 3, 9, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    spec = parse_schedule_request("every 10 minutes remind me to drink water", now=now)

    assert spec.schedule_type == "interval"
    assert spec.interval_seconds == 600
    assert spec.prompt == "remind me to drink water"
    assert spec.mode == "auto"


def test_parse_chinese_relative_schedule() -> None:
    now = datetime(2026, 7, 3, 9, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    spec = parse_schedule_request("10分钟后提醒我开会", now=now)

    assert spec.schedule_type == "once"
    assert spec.prompt == "开会"
    assert int(spec.run_at or 0) == int(now.timestamp()) + 600


def test_parse_daily_role_schedule() -> None:
    now = datetime(2026, 7, 3, 10, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    spec = parse_schedule_request("daily at 09:30 ask Athena to summarize notes", now=now)

    assert spec.schedule_type == "daily"
    assert spec.hour == 9
    assert spec.minute == 30
    assert spec.mode == "role:athena"
    assert spec.prompt == "summarize notes"


def test_scheduler_add_claim_and_record(tmp_path) -> None:
    scheduler = ChronosScheduler(tmp_path / "chronos_jobs.json")
    spec = parse_schedule_request("in 5 minutes ping me")
    job = scheduler.add_job(spec)

    assert job["enabled"] is True
    assert scheduler.claim_due_jobs(now_ts=(job["next_run_at"] or 0) - 1) == []

    due = scheduler.claim_due_jobs(now_ts=(job["next_run_at"] or 0) + 1)
    assert [item["id"] for item in due] == [job["id"]]
    assert scheduler.get_job(job["id"])["running"] is True

    run = scheduler.record_run(job["id"], success=True, output="ok")

    stored = scheduler.get_job(job["id"])
    assert run["success"] is True
    assert stored["running"] is False
    assert stored["enabled"] is False
    assert stored["last_status"] == "done"
    assert stored["run_count"] == 1


def test_schedulers_reload_shared_jobs_before_writing(tmp_path):
    a = ChronosScheduler(tmp_path / 'jobs.json')
    b = ChronosScheduler(tmp_path / 'jobs.json')
    first = a.add_job_from_text('in 10 minutes first task')
    assert b.list_jobs()[0]['id'] == first['id']
    second = b.add_job_from_text('in 20 minutes second task')
    assert {job['id'] for job in a.list_jobs()} == {first['id'], second['id']}
    a.set_enabled(first['id'], False)
    assert not b.get_job(first['id'])['enabled']


def test_corrupt_schedule_is_not_silently_overwritten(tmp_path):
    import pytest

    path = tmp_path / 'jobs.json'
    path.write_text('broken data')
    scheduler = ChronosScheduler(path)
    with pytest.raises(RuntimeError, match='Restore a backup'):
        scheduler.add_job_from_text('in 1 minute test')
    assert path.read_text() == 'broken data'


def test_schedule_updates_from_two_processes_do_not_lose_jobs(tmp_path):
    import subprocess
    import sys

    script = '''
import sys
from pathlib import Path
from pantheon.core.scheduler import ChronosScheduler
scheduler = ChronosScheduler(Path(sys.argv[1]))
for index in range(10):
    scheduler.add_job_from_text(f'in 10 minutes worker {sys.argv[2]} item {index}')
'''
    children = [subprocess.Popen([sys.executable, '-c', script, str(tmp_path / 'jobs.json'), name],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for name in ('a', 'b')]
    try:
        for child in children:
            _, error = child.communicate(timeout=30)
            assert child.returncode == 0, error
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
    assert len(ChronosScheduler(tmp_path / 'jobs.json').list_jobs()) == 20
