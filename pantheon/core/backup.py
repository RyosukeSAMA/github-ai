"""Offline, validated workspace backups with rollback on failed restoration."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from pantheon.core.paths import DataPaths
from pantheon.core.runtime import RuntimeLease, maintenance_lease
from pantheon.core.tasks import TaskStore

MAX_BYTES = 512 * 1024 * 1024


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
                if not source.is_file() or source.name in {'runtime.lock', 'maintenance.lock'} or source.name.endswith(('-wal', '-shm', '-journal')):
                    continue
                if not include_secrets and source.name in {'mcp_servers.json', 'plugins.json', '.env'}:
                    continue
                name = 'state/' + source.relative_to(paths.state).as_posix()
                if source.suffix == '.sqlite':
                    with tempfile.TemporaryDirectory() as directory:
                        snapshot = Path(directory) / 'snapshot.sqlite'
                        _copy_database(source, snapshot)
                        archive.write(snapshot, name)
                else:
                    archive.write(source, name)
            if include_secrets:
                for name, source in [('config.yaml', paths.config), ('credentials.env', paths.env)]:
                    if source.is_symlink():
                        raise ValueError('Backups do not follow symbolic links.')
                    if source.is_file():
                        archive.write(source, name)
        os.replace(temporary, destination)
        temporary = None
    finally:
        try:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
        finally:
            lease.release()


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
                    len(path.parts) > 1 and path.parts[0] == 'state' and not {'runtime.lock', 'maintenance.lock'}.intersection(path.parts)
                ):
                    raise ValueError('Unknown backup entry.')
            manifest = json.loads(archive.read('manifest.json'))
            if manifest.get('format') != 1:
                raise ValueError('Unsupported backup format.')
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
            if target.suffix == '.sqlite':
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
