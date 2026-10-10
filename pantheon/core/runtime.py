"""Cross-platform exclusive ownership of a workspace's background runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class RuntimeLease:
    def __init__(self, path: Path, metadata: dict[str, Any]) -> None:
        self.path = path
        self.metadata = metadata
        self.file: Any = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        file = os.fdopen(fd, 'r+b')
        if not os.fstat(fd).st_size:
            file.write(b' ')
            file.flush()
        file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            file.close()
            raise RuntimeError('Pantheon is already running for this workspace. Use the existing service or stop it first.') from exc
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
