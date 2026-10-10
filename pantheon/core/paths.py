"""Stable user data locations shared by every Pantheon entry point."""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path


def application_data_root() -> Path:
    explicit = os.environ.get('PANTHEON_DATA_DIR')
    if explicit:
        return Path(explicit).expanduser().resolve()
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'Pantheon'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'Pantheon'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'pantheon'


@dataclass(frozen=True)
class DataPaths:
    workspace: Path
    root: Path
    state: Path
    config: Path
    env: Path
    legacy: bool

    @classmethod
    def for_workspace(cls, workspace: Path | None = None) -> DataPaths:
        workspace = (workspace or Path(os.environ.get('PANTHEON_WORKSPACE', Path.cwd()))).resolve()
        root = application_data_root()
        legacy = workspace / '.pantheon'
        use_legacy = os.environ.get('PANTHEON_STATE_MODE') == 'workspace' or legacy.exists()
        identity = hashlib.sha256(os.path.normcase(str(workspace)).encode()).hexdigest()[:24]
        state = legacy if use_legacy else root / 'workspaces' / identity
        config = workspace / 'config' / 'pantheon.yaml'
        env = workspace / '.env'
        return cls(workspace, root, state,
                   config if config.exists() or use_legacy else root / 'config' / 'pantheon.yaml',
                   env if env.exists() or use_legacy else root / '.env', use_legacy)
