"""Offline, validated workspace backups with rollback on failed restoration."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path, PurePosixPath

from pantheon.core.paths import DataPaths
from pantheon.core.runtime import RuntimeLease, maintenance_lease
from pantheon.core.tasks import TaskStore

MAX_BYTES = 512 * 1024 * 1024
EPHEMERAL = {'runtime.lock', 'maintenance.lock', 'desktop-runtime.json', 'desktop-sessions.lock', 'desktop-writes.lock'}


def _copy_database(source: Path, target: Path) -> None:
    original = sqlite3.connect(f'{source.as_uri()}?mode=ro', uri=True)
    copy = sqlite3.connect(target)
    try:
        original.backup(copy)
    finally:
        copy.close()
        original.close()


def _lease(paths: DataPaths) -> RuntimeLease:
    return RuntimeLease(paths.state / 'runtime.lock', {'operation': 'backup'})


def _sanitize_channel_snapshot(path: Path, name: str):
    """Restoring a backup must not replay queued messages or reactivate callbacks."""
    if name not in {'channels.sqlite', 'readiness.sqlite', 'desktop.sqlite'}:
        return
    with closing(sqlite3.connect(path)) as db, db:
        if name == 'channels.sqlite':
            db.execute('UPDATE events SET state="interrupted" WHERE state IN ("queued", "running")')
            db.execute('UPDATE events SET data=json_remove(data, "$.route.token")')
        elif name == 'desktop.sqlite':
            db.execute('UPDATE runs SET status="interrupted" WHERE status IN ("queued", "running", "stopping")')
            db.execute('UPDATE reviews SET status="rejected" WHERE status="pending"')
        else:
            for name, raw in db.execute('SELECT name, value FROM preferences WHERE name LIKE "channel:%"').fetchall():
                data = json.loads(raw)
                data['enabled'] = False
                db.execute('UPDATE preferences SET value=? WHERE name=?', (json.dumps(data), name))


def _sanitize_scheduler_snapshot(path: Path) -> None:
    """Restored automations require review before they can execute again."""
    data = json.loads(path.read_text())
    if (not isinstance(data, dict) or not isinstance(data.get('jobs', []), list)
            or not isinstance(data.get('runs', []), list)
            or any(not isinstance(item, dict) for item in [*data.get('jobs', []), *data.get('runs', [])])):
        raise ValueError('Invalid Chronos backup state.')
    for job in data.get('jobs', []):
        job.update(enabled=False, running=False, last_status='paused')
    for run in data.get('runs', []):
        if run.get('status') in {'queued', 'running'}:
            run['status'] = 'interrupted'
    path.write_text(json.dumps(data), encoding='utf8')


def _require_idle(paths: DataPaths) -> None:
    database = paths.state / 'tasks.sqlite'
    if database.exists() and any(task['status'] == 'running' for task in TaskStore(database).list()):
        raise ValueError('Wait for running CLI tasks to finish before backup or restore.')


def export_backup(paths: DataPaths, destination: Path, *, include_secrets: bool = False) -> None:
    with maintenance_lease(paths.state):
        _export_backup(paths, destination, include_secrets=include_secrets)


def _export_backup(paths: DataPaths, destination: Path, *, include_secrets: bool = False) -> None:
    destination = destination.expanduser().resolve()
    if destination.exists():
        raise ValueError('Backup destination already exists; choose a new filename.')
    if destination.is_relative_to(paths.state.resolve()):
        raise ValueError('Save the backup outside the data directory.')
    lease = _lease(paths)
    lease.acquire()
    temporary = None
    try:
        _require_idle(paths)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=destination.parent, suffix='.partial')
        os.close(fd)
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', json.dumps({'format': 1, 'includes_secrets': include_secrets}))
            for source in paths.state.rglob('*'):
                if source.is_symlink():
                    raise ValueError('Backups do not follow symbolic links.')
                if '.locks' in source.relative_to(paths.state).parts:
                    continue
                if not source.is_file() or source.name in EPHEMERAL or source.name.endswith(('-wal', '-shm', '-journal')):
                    continue
                if not include_secrets and source.name in {'mcp_servers.json', 'plugins.json', '.env'}:
                    continue
                name = 'state/' + source.relative_to(paths.state).as_posix()
                if source.suffix == '.sqlite':
                    with tempfile.TemporaryDirectory() as directory:
                        snapshot = Path(directory) / 'snapshot.sqlite'
                        _copy_database(source, snapshot)
                        _sanitize_channel_snapshot(snapshot, source.name)
                        archive.write(snapshot, name)
                elif source.relative_to(paths.state).as_posix() == 'chronos_jobs.json':
                    with tempfile.TemporaryDirectory() as directory:
                        snapshot = Path(directory) / 'chronos_jobs.json'
                        shutil.copy2(source, snapshot)
                        _sanitize_scheduler_snapshot(snapshot)
                        archive.write(snapshot, name)
                else:
                    archive.write(source, name)
            if include_secrets:
                for name, source in [('config.yaml', paths.config), ('credentials.env', paths.env)]:
                    if source.is_symlink():
                        raise ValueError('Backups do not follow symbolic links.')
                    if source.is_file():
                        archive.write(source, name)
        with zipfile.ZipFile(temporary) as archive:
            _validate_archive(archive)
        os.replace(temporary, destination)
        temporary = None
    finally:
        try:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
        finally:
            lease.release()


def _validate_archive(archive: zipfile.ZipFile) -> dict:
    entries = archive.infolist()
    if len(entries) > 10000 or sum(item.file_size for item in entries) > MAX_BYTES:
        raise ValueError('Backup exceeds restore limits.')
    names: set[str] = set()
    for entry in entries:
        path = PurePosixPath(entry.filename)
        if ('\\' in entry.filename or ':' in entry.filename or path.is_absolute() or '..' in path.parts
                or entry.filename in names or (entry.external_attr >> 16) & 0o170000 == 0o120000):
            raise ValueError('Unsafe backup entry.')
        names.add(entry.filename)
        if entry.filename not in {'manifest.json', 'config.yaml', 'credentials.env'} and not (
            len(path.parts) > 1 and path.parts[0] == 'state' and not (EPHEMERAL | {'.locks'}).intersection(path.parts)
        ):
            raise ValueError('Unknown backup entry.')
    manifest = json.loads(archive.read('manifest.json'))
    if not isinstance(manifest, dict) or manifest.get('format') != 1:
        raise ValueError('Unsupported backup format.')
    return manifest


def inspect_backup(source: Path) -> dict:
    """Inspect an archive without writing state or exposing credential values."""
    with zipfile.ZipFile(source.expanduser().resolve()) as archive:
        manifest = _validate_archive(archive)
        entries = archive.infolist()
        return {'format': manifest['format'], 'files': len(entries),
                'uncompressed_bytes': sum(item.file_size for item in entries),
                'includes_secrets': bool(manifest.get('includes_secrets')) or
                    any(item.filename in {'config.yaml', 'credentials.env'} for item in entries)}


def restore_backup(paths: DataPaths, source: Path) -> Path:
    with maintenance_lease(paths.state):
        return _restore_backup(paths, source.expanduser().resolve())


def _restore_backup(paths: DataPaths, source: Path) -> Path:
    """Merge saved files; retain original files in a rollback directory."""
    lease = _lease(paths)
    lease.acquire()
    staging = None
    rollback = None
    changed: list[tuple[Path, Path | None]] = []
    try:
        staging = Path(tempfile.mkdtemp(prefix='pantheon-restore-'))
        rollback = Path(tempfile.mkdtemp(prefix='pantheon-before-restore-', dir=paths.state.parent))
        _require_idle(paths)
        with zipfile.ZipFile(source) as archive:
            _validate_archive(archive)
            archive.extractall(staging)
        for saved in staging.rglob('*'):
            if not saved.is_file() or saved.name == 'manifest.json':
                continue
            relative = saved.relative_to(staging)
            if relative.parts[0] == 'state':
                target = paths.state.joinpath(*relative.parts[1:])
            elif relative.as_posix() == 'config.yaml':
                target = paths.config
            else:
                target = paths.env
            # Refuse symlink parents so extraction cannot escape the selected paths.
            if any(parent.is_symlink() for parent in (target, *target.parents)):
                raise ValueError('Restore target contains a symbolic link.')
            previous = None
            if target.exists():
                previous = rollback / str(len(changed))
                if target.suffix == '.sqlite':
                    _copy_database(target, previous)
                else:
                    shutil.copy2(target, previous)
            target.parent.mkdir(parents=True, exist_ok=True)
            changed.append((target, previous))
            if relative.as_posix() == 'state/chronos_jobs.json':
                _sanitize_scheduler_snapshot(saved)
            if target.suffix == '.sqlite':
                _sanitize_channel_snapshot(saved, target.name)
                _copy_database(saved, target)
            else:
                shutil.copy2(saved, target)
        (rollback / 'manifest.json').write_text(json.dumps([
            {'target': str(target), 'previous': str(previous) if previous else None}
            for target, previous in changed
        ]))
        return rollback
    except Exception:
        for target, previous in reversed(changed):
            if previous:
                if target.suffix == '.sqlite':
                    _copy_database(previous, target)
                else:
                    shutil.copy2(previous, target)
            else:
                target.unlink(missing_ok=True)
        raise
    finally:
        try:
            if staging is not None:
                shutil.rmtree(staging)
        finally:
            lease.release()
