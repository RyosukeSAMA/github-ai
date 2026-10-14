import time

from fastapi.testclient import TestClient

from pantheon.core.readiness import ReadinessStore
from pantheon.web import create_app
from tests.test_web_setup import _write_minimal_config


def test_health_identity_expiry_and_no_secrets(tmp_path, monkeypatch):
    store = ReadinessStore(tmp_path / 'readiness.sqlite')
    store.record('openai', 'model', 'https://endpoint/v1/', 'never-store-this-key', True)
    assert store.health('openai', 'model', 'https://endpoint/v1', 'never-store-this-key')['state'] == 'verified'
    for provider, model, url, key in [('anthropic', 'model', 'https://endpoint/v1', 'never-store-this-key'),
                                      ('openai', 'next', 'https://endpoint/v1', 'never-store-this-key'),
                                      ('openai', 'model', 'https://other/v1', 'never-store-this-key'),
                                      ('openai', 'model', 'https://endpoint/v1', 'rotated')]:
        assert store.health(provider, model, url, key)['state'] == 'untested'
    assert b'never-store-this-key' not in store.path.read_bytes()
    now = time.time()
    monkeypatch.setattr('pantheon.core.readiness.time.time', lambda: now + store.TTL + 1)
    assert store.health('openai', 'model', 'https://endpoint/v1', 'never-store-this-key')['state'] == 'expired'


def test_saved_model_evidence_and_guide_lifecycle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('PANTHEON_STATE_MODE', 'workspace')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    client = TestClient(create_app())
    assert client.get('/api/setup/status').json()['onboarding']['show']
    assert client.post('/api/onboarding', json={'action': 'confirm_workspace'}).json()['onboarding']['steps']['workspace']
    assert not client.post('/api/onboarding', json={'action': 'skip'}).json()['onboarding']['show']
    assert not TestClient(create_app()).get('/api/setup/status').json()['onboarding']['show']
    assert client.post('/api/onboarding', json={'action': 'reopen'}).json()['onboarding']['show']
    _write_minimal_config(tmp_path / 'config/pantheon.yaml')
    (tmp_path / '.env').write_text('OPENAI_API_KEY=sk-test-key\n')
    class Client:
        def complete(self, *args, **kwargs):
            return 'ok'
    monkeypatch.setattr('pantheon.web.app.get_llm_client', lambda **kwargs: Client())
    draft = client.post('/api/setup/test', json={'provider': 'openai', 'model': 'draft-model'}).json()
    assert draft['ok'] and draft['verified_count'] == 0
    saved = client.post('/api/setup/test', json={'provider': 'openai', 'model': 'old-model'}).json()
    assert saved['verified_count'] == 4
    assert saved['onboarding']['steps']['verified']
    (tmp_path / '.env').write_text('OPENAI_API_KEY=rotated-key\n')
    assert client.get('/api/setup/status').json()['verified_count'] == 0
