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


def test_result_detail_survives_restart_without_bloating_history(tmp_path):
    store = TaskStore(tmp_path / 'tasks.sqlite')
    store.start('result', 'work', 'auto')
    store.finish('result', 'completed', 'x' * 200001)
    reopened = TaskStore(store.path)
    detail = reopened.get('result')
    assert detail['data']['result'] == 'x' * 200000
    assert detail['data']['result_truncated']
    assert detail['data']['result_characters'] == 200001
    assert 'result' not in reopened.list()[0]['data']
    assert reopened.get('missing') is None


def test_cli_can_cancel_a_task_owned_by_another_process(tmp_path, monkeypatch):
    import json
    import os
    import subprocess
    import sys

    from pantheon.core.paths import DataPaths

    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    database = DataPaths.for_workspace().state / 'tasks.sqlite'
    child = subprocess.Popen([sys.executable, '-u', '-c', '''
import sys, time
from pathlib import Path
from pantheon.core.tasks import TaskStore
store = TaskStore(Path(sys.argv[1]))
store.start('external', 'cross-process work', 'auto')
print('ready', flush=True)
deadline = time.monotonic() + 20
while not store.cancelled('external'):
    if time.monotonic() > deadline:
        raise RuntimeError('Cancellation did not arrive')
    time.sleep(.025)
store.finish('external', 'stopped', 'Cancelled across processes')
''', str(database)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'ready'
        other = tmp_path / 'another-directory'
        other.mkdir()
        env = {**os.environ, 'PYTHONPATH': str(__import__('pathlib').Path(__file__).resolve().parents[1])}
        stopped = subprocess.run([sys.executable, '-m', 'pantheon.cli', '--workspace', str(tmp_path),
                                  'tasks', '--stop', 'external'], cwd=other, env=env,
                                 capture_output=True, text=True, timeout=30)
        assert stopped.returncode == 0, stopped.stderr
        assert json.loads(stopped.stdout)['stop_requested']
        child.communicate(timeout=20)
        assert child.returncode == 0
        assert TaskStore(database).get('external')['status'] == 'stopped'
        viewed = subprocess.run([sys.executable, '-m', 'pantheon.cli', '--workspace', str(tmp_path),
                                 'tasks', '--show', 'external'], cwd=other, env=env,
                                capture_output=True, text=True, timeout=30)
        assert viewed.returncode == 0, viewed.stderr
        assert json.loads(viewed.stdout)['data']['result'] == 'Cancelled across processes'
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)


def test_task_is_interrupted_after_actual_owner_crash(tmp_path):
    import subprocess
    import sys

    database = tmp_path / 'tasks.sqlite'
    child = subprocess.Popen([sys.executable, '-u', '-c', '''
import sys
from pathlib import Path
from pantheon.core.tasks import TaskStore
TaskStore(Path(sys.argv[1])).start('crashed', 'work', 'auto')
print('ready', flush=True)
sys.stdin.readline()
''', str(database)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'ready'
        child.kill()
        child.communicate(timeout=10)
        assert TaskStore(database).list()[0]['status'] == 'interrupted'
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)
