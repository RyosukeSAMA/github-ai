"""Cross-platform exclusive ownership of a workspace's background runtime."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class RuntimeLease:
    def __init__(self, path: Path, metadata: dict[str, Any], *, conflict_message: str = '') -> None:
        self.path = path
        self.metadata = metadata
        self.file: Any = None
        self.conflict_message = conflict_message or 'Pantheon is already running for this workspace. Use the existing service or stop it first.'

    def acquire(self, *, timeout: float = 0) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        file = os.fdopen(fd, 'r+b')
        if not os.fstat(fd).st_size:
            file.write(b' ')
            file.flush()
        file.seek(0)
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    file.close()
                    raise RuntimeError(self.conflict_message) from exc
                time.sleep(min(0.025, max(0, deadline - time.monotonic())))
        self.file = file
        file.seek(0)
        file.write(json.dumps({'pid': os.getpid(), **self.metadata}).encode())
        file.truncate()
        file.flush()

    def release(self) -> None:
        if self.file is not None:
            self.file.seek(0)
            self.file.write(b'{}')
            self.file.truncate()
            self.file.flush()
            self.file.close()  # Closing releases the OS lock, including after a crash.
            self.file = None

    def __enter__(self) -> RuntimeLease:
        self.acquire()
        return self

    def __exit__(self, *args: Any) -> None:
        self.release()


def maintenance_lease(state: Path) -> RuntimeLease:
    return RuntimeLease(state / 'maintenance.lock', {'operation': 'maintenance'},
                        conflict_message='Workspace backup or restore is in progress. Retry after it finishes.')
