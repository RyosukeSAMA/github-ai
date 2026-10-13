"""Durable task status and cooperative cancellation shared across entry points."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pantheon.core.credentials import atomic_text
from pantheon.core.runtime import maintenance_lease


def _process_alive(pid: int) -> bool:
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # Access denied means existence is uncertain.
        try:
            status = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(status)) or status.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class TaskStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        os.chmod(self.path, 0o600)
        db.row_factory = sqlite3.Row
        try:
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, created REAL, updated REAL, status TEXT, cancel INTEGER DEFAULT 0, data TEXT)')
                yield db
        finally:
            db.close()

    def start(self, task_id: str, task: str, mode: str):
        now = time.time()
        lease = maintenance_lease(self.path.parent)
        lease.acquire(timeout=2)
        try:
            with self.connect() as db:
                db.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, 0, ?)',
                           (task_id, now, now, 'running', json.dumps({'task': task, 'mode': mode, 'owner_pid': os.getpid()})))
        finally:
            lease.release()

    def archive_path(self, task_id: str) -> Path:
        return self.path.parent / 'results' / (hashlib.sha256(task_id.encode()).hexdigest() + '.json')

    def finish(self, task_id: str, status: str, content: str = '', *, result: dict | None = None):
        from dataclasses import asdict, is_dataclass
        with self.connect() as db:
            row = db.execute('SELECT data FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                return
            data = json.loads(row['data'])
            payload = {'task_id': task_id, 'status': status,
                       **(result or {'content': content, 'checkpoint': data.get('checkpoint'), 'task': data.get('task')})}
            archive = json.dumps(payload, ensure_ascii=False,
                                 default=lambda value: asdict(value) if is_dataclass(value) else str(value))
            atomic_text(self.archive_path(task_id), archive)
            data.update(result=content[:200000], result_truncated=len(content) > 200000,
                        result_characters=len(content), archive_available=True)
            db.execute('UPDATE tasks SET updated=?, status=?, data=? WHERE id=?',
                       (time.time(), status, json.dumps(data), task_id))

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
            return {**dict(row), 'data': json.loads(row['data'])} if row else None

    def update_checkpoint(self, task_id: str, **values):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM tasks WHERE id=?', (task_id,)).fetchone()
            if not row:
                return
            data = json.loads(row['data'])
            checkpoint = data.setdefault('checkpoint', {})
            checkpoint.update(values)
            db.execute('UPDATE tasks SET data=?, updated=? WHERE id=?', (json.dumps(data), time.time(), task_id))

    def save_step(self, task_id: str, index: int, result: dict):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM tasks WHERE id=?', (task_id,)).fetchone()
            if not row:
                return
            data = json.loads(row['data'])
            data.setdefault('checkpoint', {}).setdefault('steps', {})[str(index)] = result
            db.execute('UPDATE tasks SET data=?, updated=? WHERE id=?', (json.dumps(data), time.time(), task_id))

    def record_effect(self, task_id: str, index: int, effect: dict):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM tasks WHERE id=?', (task_id,)).fetchone()
            if not row:
                return
            data = json.loads(row['data'])
            data.setdefault('checkpoint', {}).setdefault('effects', {}).setdefault(str(index), []).append(effect)
            db.execute('UPDATE tasks SET data=?, updated=? WHERE id=?', (json.dumps(data), time.time(), task_id))

    def claim_resume(self, task_id: str, child_id: str) -> dict:
        self.list()  # Recover dead-process status before claiming.
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status, data FROM tasks WHERE id=?', (task_id,)).fetchone()
            if not row or row['status'] not in {'failed', 'partial_failure', 'stopped', 'interrupted'}:
                raise ValueError('Only failed, stopped or interrupted tasks can be resumed.')
            data = json.loads(row['data'])
            if not data.get('checkpoint'):
                raise ValueError('This older task has no checkpoint. Start a new task from its saved request.')
            previous = data.get('resumed_by')
            if previous:
                child = db.execute('SELECT status FROM tasks WHERE id=?', (previous,)).fetchone()
                if child:
                    raise ValueError(f'This task already continued as {previous}. View or resume that task instead.')
                if time.time() - data.get('resume_claimed', 0) < 60:
                    raise ValueError('A resume of this task is already running.')
            data.update(resumed_by=child_id, resume_claimed=time.time())
            db.execute('UPDATE tasks SET data=? WHERE id=?', (json.dumps(data), task_id))
            return data

    def cancelled(self, task_id: str) -> bool:
        with self.connect() as db:
            row = db.execute('SELECT cancel FROM tasks WHERE id=?', (task_id,)).fetchone()
            return bool(row and row['cancel'])

    def cancel(self, task_id: str) -> bool:
        with self.connect() as db:
            return db.execute('UPDATE tasks SET cancel=1, updated=? WHERE id=? AND status="running"',
                              (time.time(), task_id)).rowcount > 0

    def list(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            running = db.execute('SELECT id, data FROM tasks WHERE status="running"').fetchall()
            for row in running:
                owner = json.loads(row['data']).get('owner_pid')
                if type(owner) is int and owner > 0 and not _process_alive(owner):
                    db.execute('UPDATE tasks SET status="interrupted", updated=? WHERE id=? AND status="running"',
                               (time.time(), row['id']))
            rows = db.execute('SELECT * FROM tasks ORDER BY updated DESC LIMIT 100').fetchall()
            history = []
            for row in rows:
                data = json.loads(row['data'])
                data.pop('result', None)  # History remains small; original results stay on disk.
                checkpoint = data.pop('checkpoint', {})
                data['recoverable'] = bool(checkpoint) and row['status'] in {'failed', 'partial_failure', 'stopped', 'interrupted'}
                if data.get('resumed_by') and db.execute('SELECT id FROM tasks WHERE id=?', (data['resumed_by'],)).fetchone():
                    data['recoverable'] = False
                finished = checkpoint.get('steps', {})
                data['resume_requires_review'] = any(not finished.get(index, {}).get('success')
                                                    for index in checkpoint.get('effects', {}))
                data['task'] = data.get('task', '')[:2000]
                history.append({**dict(row), 'data': data})
            return history
