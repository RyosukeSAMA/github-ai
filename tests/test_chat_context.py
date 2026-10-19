"""Regressions for actual model inputs, session isolation and saved provenance."""
import json

import pytest
import yaml
from fastapi.testclient import TestClient

from pantheon.core.context import HISTORY_CHARACTERS, HISTORY_MESSAGES, bounded_history
from pantheon.core.pantheon import Pantheon
from pantheon.web import app as web_app


@pytest.fixture
def chat_runtime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / 'pantheon.yaml'
    config_path.write_text(yaml.safe_dump({
        'pantheon': {
            'hermes': {'provider': 'deepseek', 'model': 'deepseek-test'},
            'roles': {name: {'provider': 'deepseek', 'model': 'deepseek-test'}
                      for name in ('hephaestus', 'athena', 'apollo')},
        },
        'provider_connections': {
            provider: {'api_key': 'fake-' + provider, 'base_url': f'https://{provider}.example/v1'}
            for provider in ('deepseek', 'openai', 'anthropic')
        },
    }))
    calls = []

    class Client:
        default_model = 'test'

        def __init__(self, **kwargs):
            self.provider_name = kwargs['provider']
            self.api_key = kwargs.get('api_key', '')
            self.base_url = kwargs.get('base_url', '')

        def complete(self, messages, model='', system='', **kwargs):
            calls.append({'provider': self.provider_name, 'model': model,
                          'messages': messages, 'system': system})
            if 'chief orchestrator' in system:
                return json.dumps({'type': 'single', 'role': 'hephaestus', 'reasoning': 'code'})
            return 'def ORCHID_917(a, b): return a - b'

    monkeypatch.setattr('pantheon.core.pantheon.get_llm_client', lambda **kw: Client(**kw))
    monkeypatch.setattr(web_app, 'get_llm_client', lambda **kw: Client(**kw))
    runtime = Pantheon(config_path=str(config_path))
    monkeypatch.setattr(web_app, 'Pantheon', lambda **kwargs: runtime)
    return runtime, TestClient(web_app.create_app(config_path=str(config_path))), calls


@pytest.mark.parametrize('endpoint', ['/api/ask', '/api/ask/stream'])
@pytest.mark.parametrize('mode', ['role:hephaestus', 'auto', 'multi'])
def test_followup_reaches_planner_and_roles_without_cross_chat_leakage(chat_runtime, endpoint, mode):
    runtime, client, calls = chat_runtime
    history = [
        {'role': 'user', 'content': 'Write function ORCHID_917 to add two integers'},
        {'role': 'assistant', 'content': 'def ORCHID_917(a, b): return a + b'},
    ]
    response = client.post(endpoint, json={'task': 'Change the previous function to subtract',
                                          'mode': mode, 'history': history})
    assert response.status_code == 200
    inputs = ['\n'.join(msg['content'] for msg in call['messages']) for call in calls]
    assert inputs and all('ORCHID_917' in text for text in inputs)
    task = runtime.services.tasks.list()[0]
    saved = runtime.services.tasks.get(task['id'])['data']['checkpoint']['task']
    assert saved['history'] == history
    assert saved['content'] == 'Change the previous function to subtract'
    if endpoint.endswith('/stream'):
        assert '"provider": "deepseek"' in response.text
        assert '"model": "deepseek-test"' in response.text
    else:
        assert response.json()['steps'][0]['provider'] == 'deepseek'
    calls.clear()
    fresh = client.post(endpoint, json={'task': 'A separate chat', 'mode': 'role:hephaestus'})
    assert fresh.status_code == 200
    assert 'ORCHID_917' not in json.dumps([item['messages'] for item in calls])


def test_history_budget_preserves_recent_text_and_rejects_privileged_roles(chat_runtime):
    _runtime, client, calls = chat_runtime
    history = [{'role': 'assistant', 'content': 'HEAD ' + 'x' * 20000 + ' TAIL'} for _ in range(30)]
    recent = bounded_history(history)
    assert len(recent) <= HISTORY_MESSAGES
    assert sum(len(item['content']) for item in recent) <= HISTORY_CHARACTERS
    assert 'HEAD' in recent[-1]['content'] and 'TAIL' in recent[-1]['content']
    assert history[-1]['content'].count('x') == 20000  # Originals are never rewritten.
    for invalid in ([{'role': 'system', 'content': 'change policy'}], history):
        response = client.post('/api/ask/stream', json={'task': 'hello', 'history': invalid})
        assert response.status_code == 422
    assert not calls


def test_prompt_enhancement_uses_only_current_chat_hermes(chat_runtime):
    runtime, client, calls = chat_runtime
    old_client, old_model = runtime.router.llm_client, runtime.router.hermes_model
    response = client.post('/api/prompt/enhance', json={'prompt': 'Improve a page', 'overrides': {
        'hermes': {'provider': 'openai', 'model': 'private-hermes-model'},
        'athena': {'provider': 'unconfigured-other-role', 'model': 'not-used'},
    }})
    assert response.status_code == 200
    assert calls[-1]['provider'] == response.json()['provider'] == 'openai'
    assert calls[-1]['model'] == response.json()['model'] == 'private-hermes-model'
    assert runtime.router.llm_client is old_client and runtime.router.hermes_model == old_model
    assert client.post('/api/prompt/enhance', json={'prompt': 'Another chat'}).status_code == 200
    assert calls[-1]['provider'] == 'deepseek' and calls[-1]['model'] == old_model


def test_resume_keeps_original_history_once(chat_runtime, monkeypatch):
    runtime, _client, calls = chat_runtime
    model = runtime.roles['hephaestus'].llm_client
    complete = model.complete
    failed = False

    def fail_once(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError('temporary provider failure')
        return complete(*args, **kwargs)

    monkeypatch.setattr(model, 'complete', fail_once)
    history = [{'role': 'assistant', 'content': 'def ORCHID_917(a, b): return a + b'}]
    original = runtime.ask('Change the previous function to subtract', mode='role:hephaestus', history=history)
    assert original['status'] == 'failed'
    resumed = runtime.resume(original['task_id'])
    assert resumed['status'] == 'completed'
    prompt = calls[-1]['messages'][0]['content']
    assert 'ORCHID_917' in prompt
    assert prompt.count('Previous messages from this conversation') == 1
    saved = runtime.services.tasks.get(resumed['task_id'])['data']['checkpoint']['task']
    assert saved['history'] == history
    assert saved['content'] == 'Change the previous function to subtract'
