import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import pantheon.cli as cli
from pantheon.core.cli_sessions import CliSessions


def test_chat_restores_only_explicit_cli_session_and_bounded_history(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('PANTHEON_STATE_MODE','workspace')
    calls = []
    def ask(task, **kwargs):
        calls.append((task,kwargs))
        return {'content':'Reply '+task,'task_id':'fake','steps':[]}
    monkeypatch.setattr(cli,'Pantheon',lambda **kw: SimpleNamespace(ask=ask))
    runner = CliRunner()
    assert runner.invoke(cli.app,['chat','--session','first','--no-stream'],input='First\nSecond\n/exit\n').exit_code == 0
    assert calls[0][1]['history'] == []
    assert calls[1][1]['history'] == [{'role':'user','content':'First'},{'role':'assistant','content':'Reply First'}]
    assert runner.invoke(cli.app,['chat','--session','other','--no-stream'],input='Isolated\n/exit\n').exit_code == 0
    assert calls[-1][1]['history'] == []
    assert runner.invoke(cli.app,['chat','--session','first','--no-stream'],input='Followup\n/exit\n').exit_code == 0
    assert calls[-1][1]['history'][-1]['content'] == 'Reply Second'
    assert runner.invoke(cli.app,['chat','--list']).exit_code == 0
    store = CliSessions(tmp_path/'.pantheon')
    assert len(json.loads(store.path('first').read_text())['messages']) == 6
    if hasattr(store.path('first').stat(),'st_mode'):
        assert store.path('first').stat().st_mode & 0o077 == 0


@pytest.mark.parametrize('identity',['../escape','/tmp/escape','a.b','a'*81])
def test_cli_session_paths_are_explicit_safe_names(tmp_path,identity):
    with pytest.raises(ValueError):
        CliSessions(tmp_path).path(identity)
