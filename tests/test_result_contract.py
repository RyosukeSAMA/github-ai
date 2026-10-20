"""Failure outcomes must agree in scripts, terminal output and HTTP transports."""
import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import pantheon.cli as cli
from pantheon.core.base import TaskResult
from pantheon.core.hermes import ExecutionStoppedError
from pantheon.core.results import result_exit_code, result_payload


@pytest.mark.parametrize(('steps', 'fields', 'status', 'code'), [
    ([TaskResult('athena', 'ok')], {}, 'completed', 0),
    ([TaskResult('athena', '', False, 'denied')], {}, 'failed', 1),
    ([TaskResult('athena', 'ok'), TaskResult('apollo', '', False, 'denied')], {'status': 'completed'}, 'partial_failure', 1),
    ([], {'success': False, 'content': 'Unknown skill'}, 'failed', 1),
    ([], {'status': 'stopped'}, 'stopped', 130),
    ([], {'status': 'interrupted'}, 'interrupted', 130),
])
def test_canonical_outcomes_preserve_failure_evidence(steps, fields, status, code):
    result = {'steps': steps, **fields}
    payload = result_payload(result)
    assert payload['status'] == status
    assert payload['success'] is (code == 0)
    assert result_exit_code(payload) == code
    assert json.loads(json.dumps(payload)) == payload
    if steps:
        assert isinstance(payload['steps'][0], dict)
        assert isinstance(result['steps'][0], TaskResult)  # SDK result remains compatible.


@pytest.mark.parametrize('raw', [True, False])
@pytest.mark.parametrize(('status', 'code'), [('failed', 1), ('partial_failure', 1), ('stopped', 130)])
def test_cli_failure_never_reports_complete(monkeypatch, raw, status, code):
    steps = [TaskResult('athena', 'partial', False, 'provider denied')]
    pantheon = SimpleNamespace(router=SimpleNamespace(hermes_model='fake'),
        ask=lambda *a, **kw: {'steps': steps, 'status': status, 'content': 'Partial output'})
    monkeypatch.setattr(cli, 'Pantheon', lambda **kw: pantheon)
    result = CliRunner().invoke(cli.app, ['ask', 'test task', *(['--raw'] if raw else [])])
    assert result.exit_code == code
    if raw:
        payload = json.loads(result.stdout)
        assert payload['success'] is False
        assert payload['steps'][0]['error'] == 'provider denied'
    else:
        assert '✓ Complete' not in result.stdout
        assert 'Needs attention' in result.stdout
        assert 'Partial output' in result.stdout


@pytest.mark.parametrize('constructor', [False, True])
@pytest.mark.parametrize('error', [ValueError('planner failed'), FileNotFoundError('config missing'), KeyboardInterrupt(), ExecutionStoppedError('stopped')])
def test_raw_errors_always_emit_json(monkeypatch, constructor, error):
    def fail(*args, **kwargs):
        raise error
    pantheon = SimpleNamespace(ask=fail)
    monkeypatch.setattr(cli, 'Pantheon', fail if constructor else lambda **kw: pantheon)
    result = CliRunner().invoke(cli.app, ['ask', 'test task', '--raw'])
    payload = json.loads(result.stdout)
    stopped = isinstance(error, (KeyboardInterrupt, ExecutionStoppedError))
    assert result.exit_code == (130 if stopped else 1)
    assert payload['status'] == ('stopped' if stopped else 'failed')
    assert payload['success'] is False
    assert payload['error']


def test_raw_success_keeps_real_step_objects_and_metadata(monkeypatch):
    step = TaskResult('athena', 'done', metadata={'provider': 'test', 'model': 'test-id'})
    monkeypatch.setattr(cli, 'Pantheon', lambda **kw: SimpleNamespace(ask=lambda *a, **kw: {'steps': [step]}))
    result = CliRunner().invoke(cli.app, ['ask', 'test task', '--raw'])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload['steps'][0]['metadata'] == step.metadata
    assert payload['steps'][0]['success'] is True


def test_resume_cli_reports_failure_exit_code(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, 'Pantheon', lambda: SimpleNamespace(resume=lambda *a, **kw: {
        'task_id': 'resumed', 'content': 'partial', 'success': False}))
    result = CliRunner().invoke(cli.app, ['tasks', '--resume', 'old-task'])
    assert result.exit_code == 1
    assert 'failed' in result.stdout
