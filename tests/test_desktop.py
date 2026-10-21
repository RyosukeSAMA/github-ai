import asyncio
import json
import threading
import time

import pytest
from fastapi.testclient import TestClient
from starlette.responses import StreamingResponse

from pantheon.web.app import create_app


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('PANTHEON_DATA_DIR', str(tmp_path / 'data'))
    app = create_app()
    with TestClient(app) as client:
        client.headers['x-pantheon-desktop-token'] = app.state.desktop.token
        yield client, app.state.desktop, tmp_path


def make_session(client):
    response = client.post('/api/desktop/sessions', json={'title': 'Real task'})
    assert response.status_code == 200, response.text
    return response.json()


def test_desktop_capability_is_required_and_private(desktop):
    client, runtime, root = desktop
    identity = client.get('/api/desktop/identity?challenge=one').json()
    assert identity['workspace'] == str(root)
    assert identity['challenge'] == 'one'
    assert 'token' not in identity
    assert json.loads(runtime.descriptor.read_text())['token'] == runtime.token
    client.headers.pop('x-pantheon-desktop-token')
    assert client.get('/api/desktop/sessions').status_code == 401
    assert client.get('/api/health').status_code == 200


def test_session_edits_conflict_and_preserve_other_conversations(desktop):
    client, runtime, root = desktop
    first, second = make_session(client), make_session(client)
    response = client.patch('/api/desktop/sessions/'+first['id'], json={'expected_version': 0, 'draft': 'A', 'pinned': True})
    assert response.status_code == 200
    assert client.patch('/api/desktop/sessions/'+first['id'], json={'expected_version': 0, 'draft': 'stale'}).status_code == 409
    assert runtime.session(first['id'])['draft'] == 'A'
    assert runtime.session(second['id'])['draft'] == ''
    saved = json.loads((runtime.services.paths.state/'conversations.json').read_text())
    assert len(saved['sessions']) == 2
    assert client.get('/api/desktop/search?query=A').json()['sessions']


def test_file_review_detects_external_edits_and_uses_actual_content(desktop):
    client, runtime, root = desktop
    target = root/'document.txt'
    target.write_text('original\n')
    current = client.get('/api/desktop/file?path=document.txt').json()
    request = client.post('/api/desktop/reviews', json={'path': 'document.txt','content':'reviewed\n','expected_hash':current['hash']})
    assert request.status_code == 200
    review = request.json()
    assert '-original' in review['diff'] and '+reviewed' in review['diff']
    assert target.read_text() == 'original\n'
    target.write_text('external\n')
    assert client.post('/api/desktop/reviews/'+review['id']+'/accept').status_code == 409
    assert target.read_text() == 'external\n'
    fresh = client.post('/api/desktop/reviews', json={'path':'document.txt','content':'final\n'}).json()
    assert client.post('/api/desktop/reviews/'+fresh['id']+'/accept').json()['saved']
    assert target.read_text() == 'final\n'
    assert client.post('/api/desktop/reviews/'+fresh['id']+'/accept').status_code == 409
    assert client.get('/api/desktop/file?path=.env').status_code == 403
    assert client.post('/api/desktop/reviews',json={'path':'../outside','content':'x'}).status_code == 403


def test_detached_run_is_idempotent_and_keeps_new_draft(desktop):
    client, runtime, root = desktop
    gate = threading.Event()
    calls = []
    async def ask(req):
        calls.append(req.task)
        async def events():
            yield 'event: start\ndata: {"task_id":"core-task"}\n\n'
            while not gate.is_set():
                await asyncio.sleep(.01)
            yield 'event: done\ndata: '+json.dumps({'status':'completed','success':True,'content':'# Real output\n```html\n<h1>Ready</h1>\n```'})+'\n\n'
        return StreamingResponse(events())
    runtime.ask = ask
    session = make_session(client)
    request = {'request_id':'unique-request-1','prompt':'Build it','expected_version':0}
    first = client.post('/api/desktop/sessions/'+session['id']+'/runs',json=request)
    assert first.status_code == 200, first.text
    second = client.post('/api/desktop/sessions/'+session['id']+'/runs',json=request)
    assert second.json()['id'] == first.json()['id']
    current = runtime.session(session['id'])
    assert client.patch('/api/desktop/sessions/'+session['id'],json={'draft':'Next task','expected_version':current['desktop_version']}).status_code == 200
    gate.set()
    for _ in range(100):
        run = runtime.run(first.json()['id'])
        if run['status'] == 'completed':
            break
        time.sleep(.01)
    assert run['status'] == 'completed'
    assert calls == ['Build it']
    assert runtime.session(session['id'])['draft'] == 'Next task'
    for _ in range(100):
        artifacts = client.get('/api/desktop/artifacts').json()['artifacts']
        if len(artifacts) == 2:
            break
        time.sleep(.01)
    assert len(artifacts) == 2
    assert all('content' not in item for item in artifacts)
    assert client.get('/api/desktop/artifacts/'+artifacts[0]['id']).json()['content']


def test_git_worktree_is_explicit_and_starts_from_commit(desktop):
    import subprocess
    client, runtime, root = desktop
    subprocess.run(['git','init',str(root)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(root),'-c','user.name=Test','-c','user.email=test@example.com','commit','--allow-empty','-m','Initial'],check=True,capture_output=True)
    assert client.get('/api/desktop/git').json()['available']
    response = client.post('/api/desktop/git/worktrees',json={'base':'HEAD'})
    assert response.status_code == 200, response.text
    assert response.json()['branch'].startswith('pantheon/')
    assert client.post('/api/desktop/git/worktrees',json={'base':'--help'}).status_code == 400


def test_recovery_reconciles_completed_core_result_without_reexecution(desktop):
    client, runtime, root = desktop
    session = make_session(client)
    runtime.services.tasks.start('finished-core', 'recover', 'auto')
    content = 'Complete saved answer\n```html\n<h1>Recovered</h1>\n```'
    runtime.services.tasks.finish('finished-core', 'completed', content)
    with runtime.db() as db:
        db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)', ('lost-final','recover-request',session['id'],'finished-core','running',time.time(),time.time(),'{}'))
    runtime.start('127.0.0.1', 1234)
    assert runtime.run('lost-final')['status'] == 'completed'
    assert runtime.run('lost-final')['data']['result']['content'] == content
    assert runtime.session(session['id'])['messages'][0]['text'] == content
    assert len(runtime.artifacts()) == 2
    runtime.start('127.0.0.1', 1234)
    assert len(runtime.session(session['id'])['messages']) == 1
    assert len(runtime.artifacts()) == 2


def test_attachment_draft_survives_reload_and_invalid_request_is_rejected(desktop):
    import base64
    client, runtime, root = desktop
    session = make_session(client)
    raw = b'%PDF-1.4\nminimal attachment'
    uploaded = client.post('/api/desktop/attachments',json={'name':'sample.pdf','data':base64.b64encode(raw).decode()})
    assert uploaded.status_code == 200, uploaded.text
    identity = uploaded.json()['id']
    assert client.patch('/api/desktop/sessions/'+session['id'],json={'expected_version':0,'attachment_draft':[identity]}).status_code == 200
    detail = client.get('/api/desktop/sessions/'+session['id']).json()
    assert detail['attachments'][0]['name'] == 'sample.pdf'
    result = client.post('/api/desktop/sessions/'+session['id']+'/runs',json={'request_id':'invalid-request','prompt':'hello','attachments':'bad'})
    assert result.status_code == 400
    assert runtime.runs() == []


def test_remote_desktop_requires_web_auth_and_shares_saved_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('PANTHEON_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('PANTHEON_STATE_MODE', 'workspace')
    monkeypatch.setenv('PANTHEON_UI_AUTH_ENABLED', 'true')
    monkeypatch.setenv('PANTHEON_UI_USERNAME', 'desktop-test')
    monkeypatch.setenv('PANTHEON_UI_PASSWORD', 'isolated-test-password')
    app = create_app(bind_host='0.0.0.0')
    with TestClient(app, base_url='http://127.0.0.1') as first:
        first.headers['x-pantheon-desktop-token'] = app.state.desktop.token
        assert first.get('/api/desktop/sessions').status_code == 401  # A local token cannot authorize a remote bind.
        assert first.post('/api/auth/login',json={'username':'desktop-test','password':'isolated-test-password'}).status_code == 200
        saved = make_session(first)
        second = TestClient(app, base_url='http://127.0.0.1')
        assert second.get('/api/desktop/sessions').status_code == 401
        assert second.post('/api/auth/login',json={'username':'desktop-test','password':'isolated-test-password'}).status_code == 200
        assert second.get('/api/desktop/sessions').json()['sessions'][0]['id'] == saved['id']
        assert second.patch('/api/desktop/sessions/'+saved['id'],json={'expected_version':0,'draft':'from another device'}).status_code == 200
        assert first.get('/api/desktop/sessions/'+saved['id']).json()['draft'] == 'from another device'
        second.close()
