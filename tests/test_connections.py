from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import yaml
from fastapi.testclient import TestClient

from pantheon.core.connections import normalized_config, resolve_connection
from pantheon.core.pantheon import Pantheon
from pantheon.web import app as web_app
from tests.test_web_setup import _write_minimal_config


def setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('PANTHEON_STATE_MODE', 'workspace')
    for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY'):
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / 'config/pantheon.yaml'
    _write_minimal_config(path)
    value = yaml.safe_load(path.read_text())
    value['llm_providers']['openai'] = {'api_key':'${DEEPSEEK_API_KEY}', 'base_url':'https://api.deepseek.com'}
    value['pantheon']['hermes']['model'] = 'deepseek-flash'
    path.write_text(yaml.safe_dump(value))
    (tmp_path / '.env').write_text('DEEPSEEK_API_KEY=fake-deepseek\n')
    return path, TestClient(web_app.create_app())


def test_connections_save_independently_without_retargeting_defaults(tmp_path, monkeypatch):
    path, client = setup(tmp_path, monkeypatch)
    original = yaml.safe_load(path.read_text())
    def save(provider):
        return client.post('/api/connections/save', json={
            'provider':provider, 'api_key':f'fake-{provider}', 'model':f'{provider}-test',
            'base_url':f'https://{provider}.example/v1',
        })
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, ['openai', 'anthropic']))
    assert all(r.status_code == 200 for r in results)
    assert all('fake-' not in r.text for r in results)
    saved = yaml.safe_load(path.read_text())
    assert saved['pantheon'] == original['pantheon']
    assert saved['llm_providers'] == original['llm_providers']
    assert set(saved['provider_connections']) == {'openai','anthropic'}
    assert 'fake-openai' in (tmp_path / '.env').read_text()
    assert 'fake-anthropic' in (tmp_path / '.env').read_text()
    assert 'fake-deepseek' in (tmp_path / '.env').read_text()
    config = normalized_config(saved)
    assert config['pantheon']['hermes']['provider'] == 'deepseek'
    assert config['llm_providers']['deepseek']['base_url'] == 'https://api.deepseek.com'
    assert config['llm_providers']['openai']['base_url'] == 'https://openai.example/v1'


def test_blank_key_preserves_saved_account_and_role_tests_use_its_endpoint(tmp_path, monkeypatch):
    path, client = setup(tmp_path, monkeypatch)
    assert client.post('/api/connections/save', json={'provider':'anthropic','api_key':'fake-anthropic',
                'base_url':'https://claude.example/v1','model':'claude-test'}).status_code == 200
    assert client.post('/api/connections/save', json={'provider':'anthropic','base_url':'https://claude.example/v1',
                'model':'claude-test'}).status_code == 200
    calls = []
    def fake_client(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(complete=lambda *args, **kwargs: 'ok')
    monkeypatch.setattr(web_app, 'get_llm_client', fake_client)
    response = client.post('/api/setup/test', json={'provider':'anthropic','model':'claude-test'})
    assert response.json()['ok']
    assert calls[0]['base_url'] == 'https://claude.example/v1'
    assert calls[0]['api_key'] == 'fake-anthropic'
    status = client.post('/api/models/status', json={'overrides':{'hephaestus':{'provider':'anthropic','model':'claude-test'}}}).json()
    assert next(item for item in status['role_statuses'] if item['role'] == 'hephaestus')['status'] == 'verified'
    # The default DeepSeek model was not tested by the Anthropic probe.
    assert client.get('/api/setup/status').json()['verified_count'] == 0
    assert 'fake-anthropic' not in response.text
    assert yaml.safe_load(path.read_text())['pantheon']['hermes']['model'] == 'deepseek-flash'


def test_single_and_mixed_default_models_work_in_shared_runtime(tmp_path, monkeypatch):
    path, client = setup(tmp_path, monkeypatch)
    names = ['hermes', 'hephaestus', 'athena', 'apollo']
    single = {name:{'provider':'deepseek','model':'deepseek-flash'} for name in names}
    assert client.post('/api/models/defaults', json={'models':single}).status_code == 200
    for provider in ('openai','anthropic'):
        assert client.post('/api/connections/save', json={'provider':provider,'api_key':f'fake-{provider}'}).status_code == 200
    mixed = {**single, 'hephaestus':{'provider':'anthropic','model':'claude-test'},
             'athena':{'provider':'openai','model':'gpt-test'}}
    assert client.post('/api/models/defaults', json={'models':mixed}).status_code == 200
    created = []
    def factory(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(**kwargs, default_model='test')
    monkeypatch.setattr('pantheon.core.pantheon.get_llm_client', factory)
    p = Pantheon(config_path=str(path), env_path=str(tmp_path / '.env'))
    assert p.roles['hephaestus'].llm_client.api_key == 'fake-anthropic'
    assert p.roles['athena'].llm_client.api_key == 'fake-openai'
    assert p.roles['apollo'].llm_client.api_key == 'fake-deepseek'
    assert p.router.llm_client.api_key == 'fake-deepseek'
    assert p.roles['athena'].model == 'gpt-test'
    assert p.roles['chronos'].llm_client is None


def test_missing_connection_blocks_defaults_and_bad_endpoint_does_not_save(tmp_path, monkeypatch):
    path, client = setup(tmp_path, monkeypatch)
    before = path.read_bytes()
    missing = {name:{'provider':'openai','model':'gpt-test'} for name in ['hermes','hephaestus','athena','apollo']}
    assert client.post('/api/models/defaults', json={'models':missing}).status_code == 400
    assert client.post('/api/connections/save', json={'provider':'openai','api_key':'fake-key',
                'base_url':'https://user:password@example.com'}).status_code == 400
    assert path.read_bytes() == before


def test_default_save_pins_legacy_chats_and_retains_existing_overrides(tmp_path, monkeypatch):
    _path, client = setup(tmp_path, monkeypatch)
    state = client.get('/api/conversations').json()
    chat = {'id':'legacy-chat', 'title':'Old chat', 'mode':'auto', 'createdAt':1, 'updatedAt':1,
            'messages':[], 'overrides':{'athena':{'provider':'deepseek','model':'custom-old-model'}}}
    assert client.put('/api/conversations', json={'schema_version':1, 'sessions':[chat], 'expected_revision':state['revision']}).status_code == 200
    assert client.post('/api/connections/save', json={'provider':'openai','api_key':'fake-openai'}).status_code == 200
    models = {name:{'provider':'openai','model':'gpt-test'} for name in ['hermes','hephaestus','athena','apollo']}
    assert client.post('/api/models/defaults', json={'models':models}).status_code == 200
    saved = client.get('/api/conversations').json()['sessions'][0]
    assert saved['overrides']['hermes'] == {'provider':'deepseek','model':'deepseek-flash'}
    assert saved['overrides']['athena']['model'] == 'custom-old-model'
    assert saved['overrides']['apollo']['provider'] == 'deepseek'
    assert saved['updatedAt'] == 1


def test_legacy_literal_key_and_custom_url_remain_together():
    config = {'llm_providers':{'openai':{'provider_id':'deepseek','api_key':'literal-key',
                                      'base_url':'https://gateway.example/v1'}}}
    assert resolve_connection(config, 'deepseek', lambda _: 'other-key') == ('https://gateway.example/v1', 'literal-key')
    assert normalized_config(config)['pantheon']['roles']['athena']['provider'] == 'deepseek'


def test_hermes_provider_override_isolated_and_uses_independent_profile(tmp_path, monkeypatch):
    path, client = setup(tmp_path, monkeypatch)
    assert client.post('/api/connections/save', json={'provider':'openai','api_key':'fake-openai',
                'base_url':'https://openai.example/v1'}).status_code == 200
    class Client:
        default_model = 'test'
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def complete(self, *args, **kwargs):
            return 'ok'
    monkeypatch.setattr('pantheon.core.pantheon.get_llm_client', lambda **kwargs: Client(**kwargs))
    base = Pantheon(config_path=str(path), env_path=str(tmp_path / '.env'))
    original_model, original_client = base.router.hermes_model, base.router.llm_client
    monkeypatch.setattr(web_app, 'Pantheon', lambda **kwargs: base)
    monkeypatch.setattr(Pantheon, 'ask', lambda self, *args, **kwargs: {
        'content':f'{self.router.hermes_model}|{self.router.llm_client.base_url}'})
    override = client.post('/api/ask', json={'task':'hello', 'overrides':{'hermes':{'provider':'openai','model':'gpt-test'}}})
    assert override.json()['content'] == 'gpt-test|https://openai.example/v1'
    default = client.post('/api/ask', json={'task':'hello'})
    assert default.json()['content'] == 'deepseek-flash|https://api.deepseek.com'
    assert base.router.llm_client is original_client
    assert base.router.hermes_model == original_model
