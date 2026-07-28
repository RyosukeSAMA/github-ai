import time

from fastapi.testclient import TestClient

import pantheon.web.app as web_app
from pantheon.core.base import TaskResult


def test_stream_reports_live_phases_steps_and_heartbeats(tmp_path, monkeypatch) -> None:
    class FakeHermes:
        def dispatch(self, task, on_event=None):
            on_event("plan_start", {
                "role": "hermes",
                "description": "Building the route",
            })
            time.sleep(0.04)
            on_event("plan_ready", {
                "plan": "Research, then build.",
                "mode": "multi",
                "steps": [
                    {
                        "index": 0,
                        "total": 1,
                        "role": "athena",
                        "task": "Research the topic",
                        "description": "Research",
                        "skills": [],
                    },
                ],
            })
            step = {
                "index": 0,
                "total": 1,
                "role": "athena",
                "task": "Research the topic",
                "description": "Research",
                "skills": [],
            }
            on_event("step_start", step)
            on_event("step_done", {
                **step,
                "content": "Research complete.",
                "duration_ms": 12,
                "success": True,
                "error": None,
            })
            on_event("summary_start", {
                "role": "hermes",
                "description": "Preparing the final answer",
            })
            on_event("summary_done", {
                "role": "hermes",
                "content": "Final answer.",
                "success": True,
            })
            return {
                "mode": "multi",
                "plan": "Research, then build.",
                "content": "Final answer.",
                "steps": [
                    TaskResult(role="athena", content="Research complete."),
                ],
                "memory_matches": [],
                "skill_matches": [],
            }

    class FakePantheon:
        def __init__(self, *args, **kwargs):
            self.hermes = FakeHermes()

        def get_role(self, name):
            return None

    monkeypatch.setenv("PANTHEON_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(web_app, "Pantheon", FakePantheon)
    monkeypatch.setattr(web_app, "STREAM_HEARTBEAT_SECONDS", 0.01)
    client = TestClient(web_app.create_app())

    response = client.post(
        "/api/ask/stream",
        json={"task": "Research and build", "mode": "multi"},
    )

    assert response.status_code == 200
    stream = response.text
    assert "event: progress" in stream
    assert stream.index("event: phase") < stream.index("event: plan")
    assert stream.index("event: plan") < stream.index("event: step_start")
    assert stream.index("event: step_start") < stream.index("event: step_done")
    assert stream.index("event: summary_start") < stream.index("event: done")
