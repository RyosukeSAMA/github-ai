"""The Desktop maintenance runner uses the same offline backup and restore rules."""
import json
import os
import subprocess
import sys
import zipfile

import pytest

from pantheon.core.backup import export_backup, inspect_backup, restore_backup
from pantheon.core.paths import DataPaths
from pantheon.core.runtime import RuntimeLease


def run_maintenance(root, *args):
    env = {**os.environ, 'PANTHEON_STATE_MODE': 'workspace',
           'PANTHEON_DATA_DIR': str(root / 'private-data')}
    env.pop('PANTHEON_DESKTOP_TOKEN', None)
    env.pop('PANTHEON_CONFIG', None)
    return subprocess.run([sys.executable, '-m', 'pantheon.desktop.runner', '--workspace', str(root), *map(str, args)],
                          env=env, capture_output=True, text=True, timeout=20)


def test_offline_runner_exports_inspects_and_restores_without_a_server(tmp_path):
    state = tmp_path / '.pantheon'
    state.mkdir()
    (state / 'note.txt').write_text('before')
    archive = tmp_path / 'backup.zip'
    result = run_maintenance(tmp_path, '--backup', archive)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['saved']
    inspected = run_maintenance(tmp_path, '--inspect-backup', archive)
    assert inspected.returncode == 0
    assert json.loads(inspected.stdout)['includes_secrets'] is False
    (state / 'note.txt').write_text('changed')
    restored = run_maintenance(tmp_path, '--restore', archive)
    assert restored.returncode == 0, restored.stderr
    assert json.loads(restored.stdout)['restored']
    assert (state / 'note.txt').read_text() == 'before'


def test_offline_runner_cannot_bypass_an_existing_runtime_lease(tmp_path):
    state = tmp_path / '.pantheon'
    lease = RuntimeLease(state / 'runtime.lock', {'operation': 'fixture runtime'})
    lease.acquire()
    try:
        archive = tmp_path / 'must-not-exist.zip'
        result = run_maintenance(tmp_path, '--backup', archive)
        assert result.returncode != 0
        assert not archive.exists()
    finally:
        lease.release()


def test_inspection_rejects_traversal_and_reports_credentials_even_if_manifest_is_mislabelled(tmp_path):
    bad = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(bad, 'w') as archive:
        archive.writestr('manifest.json', json.dumps({'format': 1}))
        archive.writestr('../outside', 'not allowed')
    with pytest.raises(ValueError, match='Unsafe'):
        inspect_backup(bad)
    credentials = tmp_path / 'credentials.zip'
    with zipfile.ZipFile(credentials, 'w') as archive:
        archive.writestr('manifest.json', json.dumps({'format': 1, 'includes_secrets': False}))
        archive.writestr('credentials.env', 'FIXTURE_KEY=private')
    summary = inspect_backup(credentials)
    assert summary['includes_secrets'] is True
    assert 'private' not in json.dumps(summary)


def test_inspection_uses_shared_backup_limits(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_STATE_MODE', 'workspace')
    paths = DataPaths.for_workspace(tmp_path)
    paths.state.mkdir()
    (paths.state / 'note').write_text('test')
    archive = tmp_path / 'backup.zip'
    export_backup(paths, archive)
    monkeypatch.setattr('pantheon.core.backup.MAX_BYTES', 1)
    with pytest.raises(ValueError, match='limits'):
        inspect_backup(archive)


def test_restored_automations_remain_paused_including_legacy_archives(tmp_path, monkeypatch):
    from pantheon.core.scheduler import ChronosScheduler
    monkeypatch.setenv('PANTHEON_STATE_MODE', 'workspace')
    paths = DataPaths.for_workspace(tmp_path)
    scheduler = ChronosScheduler(paths.state / 'chronos_jobs.json')
    scheduler.add_job_from_text('every 5 seconds, remind me to review notes')
    archive = tmp_path / 'backup.zip'
    export_backup(paths, archive)
    # Simulate an older archive that stored enabled jobs without sanitizing them.
    legacy = tmp_path / 'legacy.zip'
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(legacy, 'w') as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == 'state/chronos_jobs.json':
                snapshot = json.loads(data)
                for job in snapshot['jobs']:
                    job.update(enabled=True, running=True)
                data = json.dumps(snapshot).encode()
            target.writestr(item, data)
    restore_backup(paths, legacy)
    restored = ChronosScheduler(paths.state / 'chronos_jobs.json')
    assert all(not job['enabled'] and not job['running'] for job in restored.list_jobs())
    assert restored.claim_due_jobs(now_ts=99999999999) == []


def test_export_refuses_to_create_an_archive_that_exceeds_restore_limits(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_STATE_MODE', 'workspace')
    paths = DataPaths.for_workspace(tmp_path)
    paths.state.mkdir()
    (paths.state / 'note').write_text('data')
    monkeypatch.setattr('pantheon.core.backup.MAX_BYTES', 1)
    with pytest.raises(ValueError, match='limits'):
        export_backup(paths, tmp_path / 'too-large.zip')
    assert not (tmp_path / 'too-large.zip').exists()
