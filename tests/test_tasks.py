from pantheon.core.tasks import TaskStore


def test_task_history_and_cancellation_cross_instances(tmp_path):
    a = TaskStore(tmp_path / 'tasks.sqlite')
    b = TaskStore(a.path)
    a.start('id', 'work', 'auto')
    assert b.cancel('id')
    assert a.cancelled('id')
    a.finish('id', 'stopped', 'cancelled')
    assert b.list()[0]['status'] == 'stopped'
    assert not b.cancel('id')


def test_history_recovers_tasks_after_owner_process_exits(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / 'tasks.sqlite')
    store.start('lost', 'work', 'auto')
    monkeypatch.setattr('pantheon.core.tasks._process_alive', lambda pid: False)
    assert store.list()[0]['status'] == 'interrupted'
    assert not store.cancel('lost')


def test_cancellation_stops_hermes_before_provider_execution(tmp_path):
    import pytest

    from pantheon.core.base import Task
    from pantheon.core.hermes import ExecutionStoppedError, Hermes
    from pantheon.core.router import Router
    from tests.conftest import MockLLMClient
    client = MockLLMClient()
    hermes = Hermes(roles={}, router=Router(client))
    hermes.task_store = TaskStore(tmp_path / 'tasks.sqlite')
    task = Task(content='work')
    hermes.task_store.start(task.task_id, task.content, task.mode)
    hermes.task_store.cancel(task.task_id)
    hermes.active_task_id = task.task_id
    with pytest.raises(ExecutionStoppedError, match='stopped'):
        hermes._checkpoint()
    assert client.calls == []
