"""Durable task status and cooperative cancellation shared across entry points."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


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
        db.row_factory = sqlite3.Row
        try:
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, created REAL, updated REAL, status TEXT, cancel INTEGER DEFAULT 0, data TEXT)')
                yield db
        finally:
            db.close()

    def start(self, task_id: str, task: str, mode: str):
        now = time.time()
        with self.connect() as db:
            db.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, 0, ?)',
                       (task_id, now, now, 'running', json.dumps({'task': task[:2000], 'mode': mode, 'owner_pid': os.getpid()})))

    def finish(self, task_id: str, status: str, content: str = ''):
        with self.connect() as db:
            db.execute('UPDATE tasks SET updated=?, status=?, data=json_set(data, "$.result", ?) WHERE id=?',
                       (time.time(), status, content[:200000], task_id))

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
            return [{**dict(row), 'data': json.loads(row['data'])} for row in rows]
