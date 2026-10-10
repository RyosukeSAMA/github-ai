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
