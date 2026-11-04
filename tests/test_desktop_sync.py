import copy
import uuid

import pytest
from fastapi.testclient import TestClient

from pantheon.web.app import create_app


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('PANTHEON_DATA_DIR', str(tmp_path/'data'))
    app = create_app()
    with TestClient(app) as client:
        client.headers['x-pantheon-desktop-token'] = app.state.desktop.token
        yield client, app.state.desktop


def operation(session=None, version=0, revision=None, **changes):
    return {'operation_id': uuid.uuid4().hex, 'session_id': session or uuid.uuid4().hex,
            'expected_version': version, 'expected_revision': revision, 'create': session is None, 'changes': changes}


def test_draft_sync_is_idempotent_across_a_lost_response_without_executing(clients):
    client, runtime = clients
    request = operation(title='Offline task', draft='Unsuitable for automatic execution')
    first = client.post('/api/desktop/sync', json=request)
    assert first.status_code == 200
    second = client.post('/api/desktop/sync', json=request)
    assert second.json()['desktop_version'] == first.json()['desktop_version']
    assert len(runtime.sessions()) == 1 and runtime.runs() == []
    assert runtime.session(request['session_id'])['messages'] == []
    altered = copy.deepcopy(request)
    altered['changes']['draft'] = 'Different payload with same operation ID'
    assert client.post('/api/desktop/sync', json=altered).status_code == 409


def test_another_device_conflict_requires_explicit_review_and_new_version(clients):
    client, runtime = clients
    first = client.post('/api/desktop/sync', json=operation(draft='Shared original')).json()
    offline = operation(first['id'], first['desktop_version'], first['sync_revision'], draft='Offline edit')
    second_device = client.patch('/api/desktop/sessions/'+first['id'], json={'expected_version': first['desktop_version'], 'draft': 'Other device edit'}).json()
    result = client.post('/api/desktop/sync', json=offline)
    assert result.status_code == 409
    assert result.json()['detail']['current']['draft'] == 'Other device edit'
    assert runtime.session(first['id'])['draft'] == 'Other device edit'
    reviewed = operation(first['id'], second_device['desktop_version'], second_device['sync_revision'], draft='Explicitly reviewed local edit')
    assert client.post('/api/desktop/sync', json=reviewed).status_code == 200
    assert runtime.runs() == []


@pytest.mark.parametrize('field', ['messages', 'editor_draft', 'overrides', 'request_id', 'attachments'])
def test_offline_sync_cannot_replay_messages_files_models_or_execution(clients, field):
    client, runtime = clients
    assert client.post('/api/desktop/sync', json=operation(**{field: 'blocked'})).status_code == 400
    assert runtime.sessions() == [] and runtime.runs() == []


def test_sync_requires_desktop_authentication(clients):
    client, runtime = clients
    client.headers.pop('x-pantheon-desktop-token')
    assert client.post('/api/desktop/sync', json=operation(draft='private')).status_code == 401


def test_web_draft_changes_are_detected_even_without_a_desktop_version_bump(clients):
    client, runtime = clients
    first = client.post('/api/desktop/sync', json=operation(draft='Original')).json()
    snapshot = runtime.conversations.get()
    snapshot['sessions'][0]['draft'] = 'Edited through the shared Web conversation store'
    assert runtime.conversations.replace(snapshot['sessions'], snapshot['revision']) is not None
    assert runtime.session(first['id'])['desktop_version'] == first['desktop_version']
    stale = operation(first['id'], first['desktop_version'], first['sync_revision'], draft='Offline edit')
    assert client.post('/api/desktop/sync', json=stale).status_code == 409
    assert runtime.session(first['id'])['draft'].startswith('Edited through')
