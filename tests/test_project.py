import json

import pytest
from fastapi.testclient import TestClient

from pantheon.core.project import ProjectConflictError, ProjectStore
from pantheon.web.app import create_app


def add(store, kind, text, **fields):
    state = store.snapshot()
    return store.save({'project_id': state['project_id'], 'expected_revision': state['revision'],
                       'kind': kind, 'text': text, **fields})


def test_confirmed_state_is_shared_and_deleted_or_superseded_text_is_not_reinjected(tmp_path):
    store = ProjectStore(tmp_path/'state/project.sqlite', tmp_path)
    candidate = add(store, 'decision', 'Candidate purple')
    first = add(store, 'decision', 'Use green', status='confirmed', reference='Brand review')
    assert 'Use green' in store.context_block() and 'Candidate purple' not in store.context_block()
    add(store, 'decision', 'Use blue', status='confirmed', replaces=first)
    assert 'Use green' not in store.context_block()
    other = ProjectStore(store.path, tmp_path)
    state = other.snapshot()
    assert next(x for x in state['entries'] if x['id'] == first)['status'] == 'superseded'
    other.delete(candidate, state['revision'], state['project_id'])
    confirmed = next(x for x in other.snapshot()['entries'] if x['text'] == 'Use blue')
    state = other.snapshot()
    other.delete(confirmed['id'], state['revision'], state['project_id'])
    assert 'Use blue' not in store.context_block()
    assert 'Use blue' not in json.dumps(store.snapshot())


def test_conflicting_edits_and_wrong_project_cannot_overwrite_state(tmp_path):
    store = ProjectStore(tmp_path/'state/project.sqlite', tmp_path)
    state = store.snapshot()
    add(store, 'goal', 'Build the site')
    with pytest.raises(ProjectConflictError):
        store.save({'kind': 'decision', 'text': 'stale', 'expected_revision': state['revision']})
    with pytest.raises(ProjectConflictError):
        store.save({'kind': 'goal', 'text': 'wrong project', 'expected_revision': 1, 'project_id': 'a'*32})
    assert len(store.snapshot()['entries']) == 1


def test_file_changes_missing_files_and_acknowledgement_are_observations_not_passed_checks(tmp_path):
    file = tmp_path/'index.html'
    file.write_text('original')
    store = ProjectStore(tmp_path/'state/project.sqlite', tmp_path)
    identity = add(store, 'output', 'Current home page', file_path='index.html')
    original = store.snapshot()
    assert original['files'][0]['state'] == 'unchanged'
    file.write_text('changed outside')
    state = store.snapshot()
    assert state['files'][0]['state'] == 'changed'
    assert original['revision'] == state['revision']
    assert original['fingerprint'] != state['fingerprint']
    with pytest.raises(ProjectConflictError):
        store.validate_review({'project_id': original['project_id'], 'revision': original['revision'], 'fingerprint': original['fingerprint']})
    entry = next(x for x in state['entries'] if x['id'] == identity)
    store.save({**entry, 'expected_revision': state['revision'], 'acknowledge_file': True,
                'expected_hash': state['files'][0]['current_hash']}, identity)
    assert store.snapshot()['files'][0]['state'] == 'unchanged'
    assert 'not independently passed tests' in store.context_block()
    file.unlink()
    assert store.snapshot()['files'][0]['state'] == 'missing'


@pytest.mark.parametrize('path', ['../secret', '/etc/passwd', '.env', 'config/pantheon.yaml', '.git/config',
                                 'a\\b', 'private.key', './index.html', 'C:/private'])
def test_tracking_refuses_private_or_escaping_paths(tmp_path, path):
    store = ProjectStore(tmp_path/'state/project.sqlite', tmp_path)
    with pytest.raises((ValueError, OSError)):
        add(store, 'output', 'Unsafe', file_path=path)
    assert store.snapshot()['entries'] == []


def test_symlinks_and_large_files_are_not_hashed_or_included(tmp_path):
    store = ProjectStore(tmp_path/'state/project.sqlite', tmp_path)
    target = tmp_path/'target.txt'
    target.write_text('private')
    link = tmp_path/'linked.txt'
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip('Symlink creation unavailable on this host')
    with pytest.raises((ValueError, OSError)):
        add(store, 'output', 'Link', file_path='linked.txt')
    target.write_bytes(b'x' * (4*1024*1024+1))
    with pytest.raises(ValueError):
        add(store, 'output', 'Too large', file_path='target.txt')


def test_context_is_bounded_valid_json_and_prioritizes_confirmed_decisions(tmp_path):
    store = ProjectStore(tmp_path/'state/project.sqlite', tmp_path)
    add(store, 'decision', 'Keep the green brand', status='confirmed')
    for i in range(12):
        add(store, 'todo', f'{i}: '+('work '*700))
    context = store.context_block()
    payload = json.loads(context.split('\n', 1)[1])
    assert payload['context_incomplete'] is True
    assert len(json.dumps(payload, ensure_ascii=False)) <= 18000
    assert 'Keep the green brand' in context


@pytest.fixture
def project_client(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('PANTHEON_STATE_MODE', 'workspace')
    monkeypatch.setenv('PANTHEON_MODEL_DOCS_SYNC', '0')
    monkeypatch.setenv('PANTHEON_UI_AUTH_ENABLED', 'false')
    with TestClient(create_app()) as client:
        yield client, tmp_path


def test_web_and_native_share_state_and_stale_continue_never_starts_work(project_client):
    client, root = project_client
    state = client.get('/api/project').json()
    body = {'project_id': state['project_id'], 'expected_revision': state['revision'],
            'kind': 'decision', 'text': 'Use green', 'status': 'confirmed'}
    saved = client.post('/api/project/entries', json=body)
    assert saved.status_code == 200
    assert client.post('/api/project/entries', json=body).status_code == 409
    review = {k: saved.json()[k] for k in ['project_id', 'revision', 'fingerprint']}
    prepared = client.post('/api/project/continue', json={**review, 'intent': 'Add pricing page'})
    assert prepared.status_code == 200 and prepared.json()['prompt'] == 'Add pricing page'
    assert 'Use green' not in prepared.json()['prompt']  # Latest state is injected at execution, not copied into a stale draft.
    body.update(expected_revision=1, text='A newer project decision')
    assert client.post('/api/project/entries', json=body).status_code == 200
    assert client.post('/api/ask/stream', json={'task': 'Continue', 'project_review': review}).status_code == 409
    native = create_app()  # Another adapter on the same workspace uses the same SQLite state.
    assert len(native.state.project.snapshot()['entries']) == 2
    client.headers['x-pantheon-desktop-token'] = client.app.state.desktop.token
    session = client.post('/api/desktop/sessions', json={}).json()
    response = client.post('/api/desktop/sessions/'+session['id']+'/runs', json={
        'prompt': 'Continue', 'request_id': 'stale-project-request', 'project_review': review})
    assert response.status_code == 409
    assert client.app.state.desktop.runs() == []


def test_auth_origin_and_false_verification_are_enforced(project_client):
    client, _ = project_client
    state = client.get('/api/project').json()
    body = {'project_id': state['project_id'], 'expected_revision': 0, 'kind': 'check', 'text': 'Tests passed', 'status': 'passed'}
    assert client.post('/api/project/entries', json=body).status_code == 400
    body.update(status='reported')
    assert client.post('/api/project/entries', json=body, headers={'Origin': 'https://evil.invalid'}).status_code == 403
    assert client.post('/api/project/entries', json={**body, 'source': 'verified-browser'}).status_code == 422


def test_explicit_web_save_registers_a_real_output_without_a_decision_or_test_claim(project_client):
    client, _ = project_client
    result = client.post('/api/workspace/file', json={'path': 'index.html', 'content': '<h1>Site</h1>', 'overwrite': True})
    assert result.status_code == 200
    state = client.get('/api/project').json()
    assert state['entries'][0]['kind'] == 'output'
    assert state['entries'][0]['source'] == 'reviewed_save'
    assert state['files'][0]['state'] == 'unchanged'


def test_each_dispatch_reads_current_state_but_steps_keep_one_snapshot(tmp_path):
    from pantheon.core.base import Task
    from tests.conftest import MockLLMClient
    from tests.test_hermes import _build_hermes

    store = ProjectStore(tmp_path/'state/project.sqlite', tmp_path)
    decision = add(store, 'decision', 'Use forest green', status='confirmed')
    mock = MockLLMClient()
    mock.add_response('{"type":"multi","reasoning":"build","steps":[{"role":"athena","task":"research"},{"role":"hephaestus","task":"implement"}]}')
    mock.add_response('Research complete')
    mock.add_response('Implementation complete')
    mock.add_response('Summary')
    hermes, _ = _build_hermes(mock)
    hermes.project_context_provider = store.context_block
    def change_after_plan(event, data):
        if event == 'plan_ready':
            saved = store.snapshot()
            store.delete(decision, saved['revision'], saved['project_id'])
    result = hermes.dispatch(Task(content='Build a pricing page'), on_event=change_after_plan)
    assert result['mode'] == 'multi'
    assert 'Use forest green' in json.dumps(mock.calls[0])
    assert 'Use forest green' in json.dumps(mock.calls[1])
    assert 'Use forest green' in json.dumps(mock.calls[2])
    mock.calls.clear()
    hermes.dispatch(Task(content='Continue tomorrow', mode='role:hephaestus'))
    assert 'Use forest green' not in json.dumps(mock.calls)
    assert hermes.active_project_context == ''


def test_project_api_uses_existing_auth_and_static_assets_stay_public(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('PANTHEON_UI_AUTH_ENABLED', 'true')
    monkeypatch.setenv('PANTHEON_UI_USERNAME', 'reviewer')
    monkeypatch.setenv('PANTHEON_UI_PASSWORD', 'fixture-private-password')
    with TestClient(create_app()) as client:
        assert client.get('/api/project').status_code == 401
        assert client.get('/project-assets/project-overview.js').status_code == 200
        assert client.post('/api/auth/login', json={'username':'reviewer','password':'fixture-private-password'}).status_code == 200
        assert client.get('/api/project').status_code == 200


def test_successful_file_save_survives_project_index_failure(project_client, monkeypatch):
    import sqlite3
    client, root = project_client
    def fail(*_args):
        raise sqlite3.OperationalError('fixture index unavailable')
    monkeypatch.setattr(client.app.state.project, 'record_output', fail)
    response = client.post('/api/workspace/file', json={'path':'saved.html','content':'Saved actual work','overwrite':False})
    assert response.status_code == 200
    assert (root/'saved.html').read_text() == 'Saved actual work'
    assert 'file was saved' in response.json()['project_state_warning']
    desktop = client.app.state.desktop
    review = desktop.prepare_review({'path':'native.html','content':'Native work'})
    saved = desktop.accept_review(review['id'])
    assert saved['saved'] is True and (root/'native.html').read_text() == 'Native work'
    assert 'file was saved' in saved['project_state_warning']
