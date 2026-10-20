"""Real adapter event formats, without network calls or billable providers."""
from contextlib import contextmanager
from types import SimpleNamespace as Ns

import pytest

from pantheon.core.budgets import TASK_ID, BudgetStore
from pantheon.core.calls import call_scope
from pantheon.core.usage import UsageStore
from pantheon.llm.anthropic_client import AnthropicClient
from pantheon.llm.openai_client import OpenAIClient


class Chunks:
    def __init__(self, events):
        self.events = events
        self.closed = False

    def __iter__(self):
        yield from self.events

    def close(self):
        self.closed = True


def chat_chunks():
    return [Ns(usage=None, choices=[Ns(delta=Ns(content='Hello '), finish_reason=None)]),
            Ns(usage=None, choices=[Ns(delta=Ns(content='world'), finish_reason='stop')]),
            Ns(usage=Ns(prompt_tokens=12, completion_tokens=3, prompt_tokens_details=None), choices=[])]


@pytest.mark.parametrize('responses', [True, False])
def test_adapters_deliver_deltas_once_with_one_budget_and_attributed_usage(tmp_path, responses):
    deltas, seen = [], []
    usage = UsageStore(tmp_path / 'usage.sqlite')
    budget = BudgetStore(tmp_path / 'budgets.sqlite')
    model = 'gpt-6-sol' if responses else 'compatible-test'
    budget.save_policy({'task_requests':1, 'prices':{f'openai/{model}':{'input':2., 'output':8.}}})
    client = OpenAIClient(api_key='fake')
    client.budget, client.usage_recorder = budget, usage.record
    def events():
        if responses:
            yield Ns(type='response.output_text.delta', delta='Hello ')
            seen.append(list(deltas))
            yield Ns(type='response.output_text.delta', delta='world')
            yield Ns(type='response.completed', response=Ns(usage=Ns(input_tokens=12, output_tokens=3, input_tokens_details=None)))
        else:
            values = chat_chunks()
            yield values[0]
            seen.append(list(deltas))
            yield from values[1:]
    stream = Chunks(events())
    def create(**kwargs):
        assert kwargs['stream'] is True
        return stream
    client._client = Ns(responses=Ns(create=create), chat=Ns(completions=Ns(create=create)))
    task = TASK_ID.set('task-stream')
    try:
        with call_scope('athena', 'execution', sink=deltas.append):
            assert client.complete([{'role':'user','content':'hi'}], model) == 'Hello world'
    finally:
        TASK_ID.reset(task)
    assert seen == [['Hello ']]  # First delta arrived before the next provider chunk.
    assert deltas == ['Hello ', 'world'] and stream.closed
    assert budget.summary()['last_24_hours']['requests'] == 1
    rows = usage.details('task-stream')['calls']
    assert len(rows) == 1
    assert rows[0]['role'] == 'athena' and rows[0]['phase'] == 'execution'
    assert rows[0]['status'] == 'reported' and rows[0]['input_tokens'] == 12
    assert rows[0]['estimated_usd'] == pytest.approx(.000048)


def test_interrupted_stream_closes_and_retains_uncertain_budget(tmp_path):
    client = OpenAIClient('fake', 'https://compatible.example/v1')
    client.budget = BudgetStore(tmp_path / 'budgets.sqlite')
    client.budget.save_policy({'prices':{'openai/model':{'input':1.,'output':1.}}})
    usage = UsageStore(tmp_path / 'usage.sqlite')
    client.usage_recorder = usage.record
    stream = Chunks(chat_chunks())
    client._client = Ns(chat=Ns(completions=Ns(create=lambda **kw: stream)))
    def stop(text):
        raise RuntimeError('stop after first delta')
    with call_scope('apollo','execution',sink=stop), pytest.raises(RuntimeError, match='stop after'):
        client.complete([{'role':'user','content':'hi'}], 'model')
    assert stream.closed
    assert client.budget.summary()['last_24_hours']['uncertain'] == 1
    row = usage.details()['calls'][0]
    assert row['status'] == 'failed' and row['output_tokens'] is None
    assert row['estimated_usd'] > 0 and row['task_id'].startswith('request:')


def test_provider_eof_without_terminal_is_not_success(tmp_path):
    client = OpenAIClient('fake', 'https://compatible.example/v1')
    stream = Chunks(chat_chunks()[:1])
    client._client = Ns(chat=Ns(completions=Ns(create=lambda **kw: stream)))
    with call_scope('athena','execution',sink=lambda _: None), pytest.raises(RuntimeError, match='completion event'):
        client.complete([], 'model')
    assert stream.closed


def test_anthropic_stream_uses_final_usage_and_closes():
    deltas, closed = [], []
    @contextmanager
    def stream(**kwargs):
        try:
            assert kwargs['max_tokens'] == 123
            yield Ns(text_stream=iter(['one ', 'two']), get_final_message=lambda: Ns(stop_reason='end_turn', usage=Ns(input_tokens=4,output_tokens=2)))
        finally:
            closed.append(True)
    client = AnthropicClient('fake')
    client._client = Ns(messages=Ns(stream=stream))
    with call_scope('hephaestus','execution',sink=deltas.append):
        assert client.complete([], 'claude-opus-5-5', max_tokens=123) == 'one two'
    assert deltas == ['one ', 'two'] and closed == [True]


def test_connection_can_disable_streaming_for_compatible_gateways():
    client = OpenAIClient('fake','https://compatible.example/v1')
    client.streaming_enabled = False
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        return Ns(choices=[Ns(message=Ns(content='Complete reply'))],usage=None)
    client._client = Ns(chat=Ns(completions=Ns(create=create)))
    with call_scope('athena','execution',sink=lambda _: pytest.fail('No streaming expected')):
        assert client.complete([], 'model') == 'Complete reply'
    assert 'stream' not in requests[0]
