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


@pytest.mark.parametrize('missing_skill', [True, False])
def test_failure_contract_matches_http_sse_webhook_and_task_history(chat_runtime, monkeypatch, missing_skill):
    from pantheon.core.base import TaskResult
    runtime, client, _ = chat_runtime
    if not missing_skill:
        monkeypatch.setattr(runtime.roles['hephaestus'], 'run', lambda task, context=None: TaskResult(
            'hephaestus', 'Partial output', False, 'Simulated provider refusal'))
    payload = {'task': 'Run this request', 'mode': 'role:hephaestus'}
    if missing_skill:
        payload['skill'] = 'not-installed-xyz'
    response = client.post('/api/ask', json=payload)
    result = response.json()
    assert response.status_code == 200
    assert result['success'] is False
    assert result['status'] == 'failed'
    assert result['error']
    stored = runtime.services.tasks.get(result['task_id'])
    assert stored['status'] == 'failed'
    assert isinstance(runtime.services.tasks.get(result['task_id'])['data']['result'], str)
    stream = client.post('/api/ask/stream', json=payload)
    events = [(frame.splitlines()[0][7:], json.loads(frame.splitlines()[1][6:]))
              for frame in stream.text.strip().split('\n\n') if frame.startswith('event:')]
    done = next(data for event, data in events if event == 'done')
    assert done['success'] is False and done['status'] == 'failed' and done['task_id']
    assert not any(event == 'step_done' and data.get('success') is True for event, data in events)
    assert any(event == 'step_error' for event, data in events)
    # Webhooks have no explicit-skill parameter, so test the real failing role path.
    if not missing_skill:
        monkeypatch.setenv('PANTHEON_WEBHOOK_ENABLED', 'true')
        monkeypatch.setenv('PANTHEON_WEBHOOK_TOKEN', 'fake-contract-token')
        webhook = client.post('/api/channels/webhook', json=payload,
                              headers={'Authorization': 'Bearer fake-contract-token'}).json()
        assert webhook['ok'] is False
        assert webhook['success'] is False and webhook['status'] == 'failed' and webhook['error']


def test_resume_stream_reports_the_new_durable_task_id(chat_runtime):
    runtime, client, _ = chat_runtime
    original = client.post('/api/ask', json={'task': 'Validate skill', 'skill': 'missing-skill'}).json()
    response = client.post('/api/ask/stream', json={'task': 'Resume', 'resume_task_id': original['task_id']})
    events = [(frame.splitlines()[0][7:], json.loads(frame.splitlines()[1][6:]))
              for frame in response.text.strip().split('\n\n') if frame.startswith('event:')]
    start = next(data for name, data in events if name == 'start')
    assert start['task_id'] is None  # Do not advertise an unrelated provisional ID.
    done = next(data for name, data in events if name == 'done')
    assert done['task_id'] != original['task_id']
    assert runtime.services.tasks.get(done['task_id'])['status'] == 'failed'
    assert all(data['task_id'] == done['task_id'] for name, data in events if name == 'step_error')


def test_stream_sends_actual_provider_chunks_without_full_text_duplicate(chat_runtime):
    from types import SimpleNamespace as Ns

    from pantheon.llm.openai_client import OpenAIClient
    runtime, client, _ = chat_runtime
    adapter = OpenAIClient('fake', 'https://compatible.example/v1')
    adapter.provider_name = 'deepseek'
    adapter.budget, adapter.usage_recorder = runtime.services.budget, runtime.usage_store.record
    class Stream:
        def __iter__(self):
            yield Ns(usage=None, choices=[Ns(delta=Ns(content='Alpha '), finish_reason=None)])
            yield Ns(usage=None, choices=[Ns(delta=Ns(content='Beta'), finish_reason='stop')])
            yield Ns(usage=Ns(prompt_tokens=4,completion_tokens=2,prompt_tokens_details=None),choices=[])
        def close(self):
            pass
    adapter._client = Ns(chat=Ns(completions=Ns(create=lambda **kw: Stream())))
    runtime.roles['hephaestus'].llm_client = adapter
    response = client.post('/api/ask/stream', json={'task':'Stream', 'mode':'role:hephaestus'})
    events = [(frame.splitlines()[0][7:], json.loads(frame.splitlines()[1][6:]))
              for frame in response.text.strip().split('\n\n') if frame.startswith('event:')]
    assert [data['text'] for event,data in events if event == 'step_chunk'] == ['Alpha ', 'Beta']
    done = next(data for event,data in events if event == 'done')
    assert done['content'] == 'Alpha Beta'
    usage = client.get('/api/usage/details', params={'task_id':done['task_id']}).json()
    assert usage['calls'][0]['role'] == 'hephaestus' and usage['calls'][0]['phase'] == 'execution'


def test_connection_disable_remove_and_reenable_do_not_retarget_roles(chat_runtime):
    runtime, client, calls = chat_runtime
    original = client.get('/api/setup/status').json()['role_statuses']
    refs = client.get('/api/connections/deepseek/references').json()
    assert set(refs['saved_roles']) == {'hermes','hephaestus','athena','apollo'}
    assert client.post('/api/connections/deepseek/manage', json={'action':'disable'}).status_code == 409
    assert client.post('/api/connections/deepseek/manage', json={'action':'disable','acknowledge_references':True}).status_code == 200
    failed = client.post('/api/ask', json={'task':'blocked', 'overrides':{'hermes':{'provider':'deepseek','model':'test'}}})
    assert failed.status_code == 500 and not calls
    probe = client.post('/api/setup/test', json={'provider':'deepseek','model':'test'}).json()
    assert probe['tested'] is False and not calls
    assert client.post('/api/connections/deepseek/manage', json={'action':'enable'}).status_code == 200
    restored = client.get('/api/setup/status').json()['role_statuses']
    assert [(row['provider'],row['model']) for row in restored] == [(row['provider'],row['model']) for row in original]
    assert client.post('/api/connections/deepseek/manage', json={'action':'remove','acknowledge_references':True}).status_code == 200
    assert client.post('/api/connections/deepseek/manage', json={'action':'enable'}).status_code == 409
    assert client.post('/api/connections/deepseek/manage', json={'action':'disable','delete_saved_key':'yes'}).status_code == 400


def test_connection_removal_can_delete_key_and_stream_preference_is_saved(chat_runtime):
    runtime, client, _ = chat_runtime
    response = client.post('/api/connections/save',json={'provider':'openai','model':'test',
        'api_key':'fake-temporary-key','streaming':False})
    assert response.status_code == 200
    assert next(row for row in response.json()['providers'] if row['id']=='openai')['streaming'] is False
    assert runtime.services.credentials.get('OPENAI_API_KEY') == 'fake-temporary-key'
    response = client.post('/api/connections/openai/manage',json={'action':'remove','acknowledge_references':True,'delete_saved_key':True})
    assert response.status_code == 200
    assert runtime.services.credentials.get('OPENAI_API_KEY') == ''
