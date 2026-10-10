import time

import pytest
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
            on_event("agent_message", {
                "message_id": "msg-1",
                "type": "result",
                "from_role": "athena",
                "to_role": "hermes",
                "summary": "Research brief delivered",
                "step_index": 1,
                "target_step_index": 1,
                "deliverable": "Research brief",
                "acceptance_criteria": ["Includes reliable evidence"],
                "metadata": {"success": True},
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
    assert "event: agent_message" in stream
    assert '"type": "result"' in stream
    assert stream.index("event: summary_start") < stream.index("event: done")


def test_model_overrides_are_isolated_between_requests(tmp_path, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    barrier = threading.Barrier(2)

    class FakeHermes:
        def dispatch(self, task, on_event=None):
            if task.content == "parallel":
                barrier.wait(timeout=5)
            content = self.roles["athena"].model
            return {"mode": "single", "content": content, "steps": []}

    instances = []

    class FakePantheon:
        def __init__(self, *args, **kwargs):
            self.roles = {"athena": SimpleNamespace(model="default", config={})}
            self.hermes = FakeHermes()
            self.hermes.roles = self.roles
            instances.append(self)

        def get_role(self, name):
            return self.roles.get(name)

        def ask(self, content, mode="auto", skill=None):
            return self.hermes.dispatch(SimpleNamespace(content=content))

    monkeypatch.setenv("PANTHEON_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(web_app, "Pantheon", FakePantheon)
    client = TestClient(web_app.create_app())
    override = {"athena": {"model": "session-a"}}
    assert client.post("/api/ask", json={"task": "a", "overrides": override}).json()["content"] == "session-a"
    assert client.post("/api/ask", json={"task": "b"}).json()["content"] == "default"
    assert 'session-a' in client.post("/api/ask/stream", json={"task": "a", "overrides": override}).text
    assert instances[0].roles["athena"].model == "default"
    with ThreadPoolExecutor(max_workers=2) as executor:
        a = executor.submit(client.post, "/api/ask", json={"task": "parallel", "overrides": override})
        b = executor.submit(client.post, "/api/ask", json={"task": "parallel"})
        assert a.result().json()["content"] == "session-a"
        assert b.result().json()["content"] == "default"


@pytest.mark.asyncio
async def test_stream_disconnect_cancels_remaining_backend_work(tmp_path, monkeypatch):
    import asyncio
    import threading

    from pantheon.core.base import Plan, PlanStep, TaskResult
    from pantheon.core.hermes import Hermes

    started = threading.Event()
    release = threading.Event()
    calls = []

    class FakeRouter:
        def plan(self, *args, **kwargs):
            return Plan.multi([PlanStep(role='athena', task='one'), PlanStep(role='athena', task='two')])

    class FakeRole:
        config = {}
        description = 'Research'

        def run(self, task, context=None):
            calls.append(task.content)
            started.set()
            release.wait(timeout=5)
            return TaskResult(role='athena', content='completed')

    class FakePantheon:
        def __init__(self, *args, **kwargs):
            self.roles = {'athena': FakeRole()}
            self.router = FakeRouter()
            self.hermes = Hermes(self.roles, self.router)

        def get_role(self, name):
            return self.roles.get(name)

    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    monkeypatch.setattr(web_app, 'Pantheon', FakePantheon)
    app = web_app.create_app()
    endpoint = next(route.endpoint for route in app.routes if getattr(route, 'path', '') == '/api/ask/stream')
    response = await endpoint(web_app.AskRequest(task='work', mode='multi'))
    iterator = response.body_iterator
    await anext(iterator)
    assert await asyncio.to_thread(started.wait, 2)
    await iterator.aclose()
    release.set()
    # Let the accepted call return and hit the cancellation checkpoint.
    await asyncio.sleep(0.1)
    assert len(calls) == 1
