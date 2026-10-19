import json
import sqlite3
import zipfile

import pytest

from pantheon.core.backup import export_backup, restore_backup
from pantheon.core.paths import DataPaths
from pantheon.core.runtime import RuntimeLease


def test_backup_restore_preserves_wal_data_and_original_files(tmp_path):
    paths = DataPaths.for_workspace(tmp_path)
    paths.state.mkdir(parents=True)
    data = paths.state / 'conversations.json'
    data.write_text('original')
    (paths.state / 'mcp_servers.json').write_text('secret')
    db = sqlite3.connect(paths.state / 'memory.sqlite')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE memory (text TEXT)')
    db.execute('INSERT INTO memory VALUES ("remember")')
    db.commit()
    archive = tmp_path / 'backup.zip'
    export_backup(paths, archive)
    with zipfile.ZipFile(archive) as saved:
        assert 'state/mcp_servers.json' not in saved.namelist()
    db.close()
    data.write_text('newer')
    rollback = restore_backup(paths, archive)
    assert data.read_text() == 'original'
    index = json.loads((rollback / 'manifest.json').read_text())
    previous = next(item['previous'] for item in index if item['target'] == str(data))
    from pathlib import Path
    assert Path(previous).read_text() == 'newer'
    with sqlite3.connect(paths.state / 'memory.sqlite') as restored:
        assert restored.execute('SELECT text FROM memory').fetchone()[0] == 'remember'


def test_restore_rejects_traversal_before_any_write(tmp_path):
    paths = DataPaths.for_workspace(tmp_path)
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as saved:
        saved.writestr('manifest.json', '{"format": 1}')
        saved.writestr('state/../../escape', 'bad')
    with pytest.raises(ValueError, match='Unsafe'):
        restore_backup(paths, archive)
    assert not (tmp_path / 'escape').exists()


def test_backup_requires_stopped_runtime(tmp_path):
    paths = DataPaths.for_workspace(tmp_path)
    lease = RuntimeLease(paths.state / 'runtime.lock', {})
    lease.acquire()
    try:
        with pytest.raises(RuntimeError, match='already running'):
            export_backup(paths, tmp_path / 'backup.zip')
    finally:
        lease.release()


def test_backup_blocks_task_start_while_copying(tmp_path, monkeypatch):
    import pantheon.core.backup as backup
    from pantheon.core.tasks import TaskStore

    paths = DataPaths.for_workspace(tmp_path)
    idle = backup._require_idle
    store = TaskStore(paths.state / 'tasks.sqlite')

    def check_before_copy(selected):
        idle(selected)
        with pytest.raises(RuntimeError, match='backup or restore'):
            store.start('racing', 'must not start', 'auto')

    monkeypatch.setattr(backup, '_require_idle', check_before_copy)
    archive = tmp_path / 'safe.zip'
    export_backup(paths, archive)
    with zipfile.ZipFile(archive) as saved:
        assert 'state/maintenance.lock' not in saved.namelist()
        assert 'state/runtime.lock' not in saved.namelist()
    store.start('after', 'now allowed', 'auto')
    store.finish('after', 'completed')


def test_restore_rolls_back_all_writes_after_copy_failure(tmp_path, monkeypatch):
    import pantheon.core.backup as backup

    paths = DataPaths.for_workspace(tmp_path)
    paths.state.mkdir(parents=True)
    data = paths.state / 'conversations.json'
    data.write_text('old')
    archive = tmp_path / 'saved.zip'
    export_backup(paths, archive)
    data.write_text('new')
    original = backup.shutil.copy2
    failed = False

    def fail_once(source, target, *args, **kwargs):
        nonlocal failed
        if not failed and str(source).startswith(tempfile.gettempdir()) and 'pantheon-restore-' in str(source):
            failed = True
            raise OSError('Injected restore failure')
        return original(source, target, *args, **kwargs)

    import tempfile
    monkeypatch.setattr(backup.shutil, 'copy2', fail_once)
    with pytest.raises(OSError, match='Injected'):
        restore_backup(paths, archive)
    assert data.read_text() == 'new'
    with RuntimeLease(paths.state / 'runtime.lock', {}):
        pass


def test_backup_disables_callbacks_and_never_replays_saved_messages(tmp_path):
    from pantheon.core.services import WorkspaceServices
    services = WorkspaceServices(DataPaths.for_workspace(tmp_path))
    services.channels.save('telegram', {'enabled': True, 'users': ['11'], 'channels': ['22']},
                           {'bot_token': '123:test-token', 'secret_token': 'callback-secret'})
    body = json.dumps({'update_id': 1, 'message': {'text': 'a task', 'message_id': 8, 'from': {'id': 11}, 'chat': {'id': 22}}}).encode()
    services.channels.receive('telegram', {'x-telegram-bot-api-secret-token': 'callback-secret'}, body)
    archive = tmp_path / 'saved.zip'
    export_backup(services.paths, archive)
    assert services.channels.config('telegram')['enabled']  # Export sanitizes only its own snapshot.
    assert services.channels.history()[0]['state'] == 'queued'
    restore_backup(services.paths, archive)
    assert not services.channels.config('telegram')['enabled']
    assert services.channels.history()[0]['state'] == 'interrupted'
    assert not services.channels.process_next(lambda *args: pytest.fail('A restored event must not execute'))


def test_documented_cli_backup_and_restore_work_in_a_new_workspace(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from pantheon.cli import app

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    paths = DataPaths.for_workspace(tmp_path)
    paths.state.mkdir(parents=True)
    data = paths.state / 'conversations.json'
    data.write_text('before backup')
    archive = tmp_path / 'backup.zip'
    runner = CliRunner()
    exported = runner.invoke(app, ['backup', str(archive)])
    assert exported.exit_code == 0, exported.output
    data.write_text('after backup')
    restored = runner.invoke(app, ['restore', str(archive)])
    assert restored.exit_code == 0, restored.output
    assert data.read_text() == 'before backup'
