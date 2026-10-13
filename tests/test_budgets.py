from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pantheon.core.budgets import TASK_ID, BudgetExceededError, BudgetStore
from pantheon.llm.openai_client import OpenAIClient
from pantheon.web import create_app


def test_concurrent_attempts_cannot_exceed_limit(tmp_path):
    path = tmp_path / 'budgets.sqlite'
    store = BudgetStore(path)
    store.save_policy({'daily_requests': 3})
    def attempt(index):
        try:
            BudgetStore(path).reserve('openai', 'model', [{'role': 'user', 'content': 'hi'}], '', 20)
            return True
        except BudgetExceededError:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(16))) == 3
    assert store.summary()['last_24_hours']['requests'] == 3
    assert store.summary()['warnings']


def test_task_limits_prices_and_failure_reservations(tmp_path):
    store = BudgetStore(tmp_path / 'budget.sqlite')
    store.save_policy({'task_requests': 1, 'output_tokens': 15, 'task_usd': 1,
                       'prices': {'openai/model': {'input': 1, 'output': 2}}})
    token = TASK_ID.set('task-one')
    try:
        identity, maximum = store.reserve('openai', 'model', [], '', 200)
        assert maximum == 15
        with pytest.raises(BudgetExceededError, match='Task request'):
            store.reserve('openai', 'model', [], '', 10)
    finally:
        TASK_ID.reset(token)
    with pytest.raises(BudgetExceededError, match='No price'):
        store.reserve('openai', 'unpriced', [], '', 10)
    # Changing prices later must not reprice an in-flight request.
    store.save_policy({'prices': {'openai/model': {'input': 100, 'output': 200}}})
    store.settle(identity, SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5)))
    assert store.summary()['last_24_hours']['estimated_usd'] == pytest.approx(.00002)


def test_provider_guard_caps_output_and_blocks_before_sending(tmp_path):
    store = BudgetStore(tmp_path / 'budgets.sqlite')
    store.save_policy({'daily_requests': 1, 'output_tokens': 20})
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text='ok', usage=SimpleNamespace(input_tokens=2, output_tokens=1))
    client = OpenAIClient(api_key='test-key')
    client.budget = store
    client._client = SimpleNamespace(responses=SimpleNamespace(create=create))
    assert client.complete([{'role': 'user', 'content': 'hi'}], model='gpt-6-sol', max_tokens=200) == 'ok'
    assert calls[0]['max_output_tokens'] == 20
    assert 'max_tokens' not in calls[0]
    with pytest.raises(BudgetExceededError):
        client.complete([], model='gpt-6-sol')
    assert len(calls) == 1
    assert store.summary()['last_24_hours']['uncertain'] == 0


def test_budget_api_validates_and_is_login_protected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())
    assert client.post('/api/budgets', json={'daily_requests': -1}).status_code == 400
    assert client.post('/api/budgets', json={'task_usd': -1}).status_code == 400
    assert client.post('/api/budgets', json={'prices': {'model': {'input': 1}}}).status_code == 400
    assert client.post('/api/budgets', json={'daily_requests': 5}).json()['policy']['daily_requests'] == 5
    assert TestClient(create_app()).get('/api/budgets').json()['policy']['daily_requests'] == 5
    (tmp_path / '.env').write_text('PANTHEON_UI_AUTH_ENABLED=1\nPANTHEON_UI_PASSWORD=password\n')
    assert client.get('/api/budgets').status_code == 401
    assert client.post('/api/budgets', json={}).status_code == 401
