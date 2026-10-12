from pantheon.core.context import compact_context
from tests.conftest import MockLLMClient


def test_compaction_preserves_contracts_originals_and_all_steps():
    client = MockLLMClient()
    client.add_response('Decision: use PostgreSQL. Source: https://example.com. File: src/db.py')
    original = [{'role': 'athena', 'step': 'compare', 'result': 'evidence ' * 4000,
                 'deliverable': 'brief', 'acceptance_criteria': ['sources']},
                {'role': 'hephaestus', 'result': 'Recent result'}]
    result = compact_context(original, client=client, model='mock')
    assert len(result) == 2
    assert result[0]['context_summary']
    assert 'PostgreSQL' in result[0]['result']
    assert result[0]['acceptance_criteria'] == ['sources']
    assert result[1]['result'] == 'Recent result'
    assert len(original[0]['result']) == 36000
    assert len(client.calls) == 2


def test_compaction_failure_is_labelled_and_retains_tail():
    result = compact_context([{'role': 'athena', 'result': 'HEAD ' + 'x' * 30000 + ' TAIL'}],
                             client=None, model='none')
    assert result[0]['context_incomplete']
    assert 'HEAD' in result[0]['result'] and 'TAIL' in result[0]['result']
    assert 'Excerpt' in result[0]['result']


def test_cancellation_is_not_swallowed():
    import pytest

    def stop():
        raise RuntimeError('stopped')

    with pytest.raises(RuntimeError, match='stopped'):
        compact_context([{'result': 'x' * 30000}], client=None, model='none', checkpoint=stop)
