import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pantheon.core.base import Plan, PlanStep, Task, TaskResult
from pantheon.core.hermes import Hermes
from pantheon.core.pantheon import Pantheon
from pantheon.core.tasks import TaskStore
from pantheon.web import create_app


def runtime(tmp_path):
    calls = []
    class Agent:
        description = 'test agent'
        def __init__(self, name):
            self.name = name
            self.config = {}
        def run(self, task, context=None):
            calls.append(self.name)
            if self.name == 'hephaestus' and calls.count(self.name) == 1:
                return TaskResult(self.name, 'temporary failure', success=False)
            return TaskResult(self.name, 'completed ' + self.name)
    plan = Plan.multi([PlanStep('athena', 'research', depends_on=[]),
                       PlanStep('hephaestus', 'build', depends_on=[1])])
    class Router:
        def plan(self, *args, **kwargs):
            return plan
        def summarize(self, task, context):
            return json.dumps(context)
    p = Pantheon.__new__(Pantheon)
    p.roles = {name: Agent(name) for name in ('athena', 'hephaestus')}
    p.router = Router()
    p.hermes = Hermes(p.roles, p.router)
    p.hermes.task_store = TaskStore(tmp_path / 'tasks.sqlite')
    p.services = SimpleNamespace(process_input=lambda _: {'saved': [], 'suggestions': []})
    p.handle_memory = False
    return p, calls


def test_resume_reuses_successes_and_archives_complete_results(tmp_path):
    p, calls = runtime(tmp_path)
    original = p.ask('Build using the research findings', mode='multi')
    assert original['status'] == 'partial_failure'
    saved = p.hermes.task_store.get(original['task_id'])
    assert saved['data']['checkpoint']['steps']['1']['success']
    p.hermes.cancel_event.set()  # A previous cancellation must not contaminate this new attempt.
    resumed = p.resume(original['task_id'])
    assert resumed['status'] == 'completed'
    assert calls == ['athena', 'hephaestus', 'hephaestus']
    assert resumed['steps'][0].content == 'completed athena'
    archive = json.loads(p.hermes.task_store.archive_path(resumed['task_id']).read_text())
    assert archive['steps'][0]['content'] == 'completed athena'
    assert 'completed athena' in archive['content']
    with pytest.raises(ValueError, match='already continued'):
        p.resume(original['task_id'])
    assert not next(task for task in p.hermes.task_store.list() if task['id'] == original['task_id'])['data']['recoverable']


def test_uncertain_external_action_requires_explicit_review(tmp_path):
    p, calls = runtime(tmp_path)
    task = Task('schedule something', mode='role:hephaestus')
    store = p.hermes.task_store
    store.start(task.task_id, task.content, task.mode)
    store.update_checkpoint(task.task_id, task=asdict(task), plan=asdict(Plan.single('hephaestus')))
    store.record_effect(task.task_id, 1, {'kind': 'mcp', 'tool': 'write'})
    store.finish(task.task_id, 'interrupted')
    with pytest.raises(ValueError, match='Review'):
        p.resume(task.task_id)
    assert calls == []
    assert store.list()[0]['data']['resume_requires_review']
    p.resume(task.task_id, acknowledge_effects=True)
    assert calls == ['hephaestus']


def test_full_archive_has_no_truncation_and_download_is_protected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = TaskStore(tmp_path / '.pantheon/tasks.sqlite')
    store.start('archive', 'request', 'auto')
    store.finish('archive', 'completed', 'z' * 250000)
    client = TestClient(create_app())
    response = client.get('/api/tasks/archive/archive')
    assert response.status_code == 200
    assert response.json()['content'] == 'z' * 250000
    assert store.get('archive')['data']['result_truncated']
    (tmp_path / '.env').write_text('PANTHEON_UI_AUTH_ENABLED=1\nPANTHEON_UI_PASSWORD=secret\n')
    assert client.get('/api/tasks/archive/archive').status_code == 401
    assert client.post('/api/tasks/archive/resume', json={}).status_code == 401


def test_web_resume_stream_reuses_checkpoint_without_a_new_plan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p, calls = runtime(tmp_path / '.pantheon')
    original = p.ask('build', mode='multi')
    # A fresh Web request snapshots these execution objects; no provider network call occurs.
    monkeypatch.setattr('pantheon.web.app.Pantheon', lambda **kwargs: p)
    client = TestClient(create_app())
    response = client.post('/api/ask/stream', json={'task': 'resume saved task', 'resume_task_id': original['task_id']})
    assert response.status_code == 200
    assert '"reused": true' in response.text
    assert '"status": "completed"' in response.text
    assert calls == ['athena', 'hephaestus', 'hephaestus']
