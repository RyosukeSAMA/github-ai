from fastapi.testclient import TestClient

from pantheon.core.paths import DataPaths
from pantheon.core.tasks import TaskStore
from pantheon.web.app import create_app


def test_task_details_share_cli_store_and_require_existing_task(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    store = TaskStore(DataPaths.for_workspace().state / 'tasks.sqlite')
    store.start('saved', 'remember result', 'auto')
    store.finish('saved', 'completed', 'Stored answer')
    with TestClient(create_app()) as client:
        summary = client.get('/api/tasks').json()['tasks'][0]
        assert 'result' not in summary['data']
        detail = client.get('/api/tasks/saved').json()
        assert detail['data']['result'] == 'Stored answer'
        assert client.get('/api/tasks/missing').status_code == 404
        assert not client.post('/api/tasks/saved/stop').json()['stop_requested']
