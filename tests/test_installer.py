import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pantheon import installer


def staged_command(args, *, cwd=None, capture=False, env=None):
    if args[:2] == ['git', 'clone']:
        root = Path(args[-1])
        (root / '.git').mkdir()
        (root / 'requirements.lock').write_text('wheel==0.46.3\n')
        (root / 'version.txt').write_text('new')
    elif args[1:3] == ['-m', 'venv']:
        root = Path(args[-1])
        (root / 'bin').mkdir(parents=True)
        (root / 'bin/python').write_text('fake python')
    if args[-3:] == ['remote', 'get-url', 'origin']:
        return SimpleNamespace(stdout='repo\n')
    return SimpleNamespace(stdout='')


def prepare_update(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_SKIP_PATH', '1')
    root = tmp_path / 'app'
    (root / '.git').mkdir(parents=True)
    (root / 'version.txt').write_text('old')
    monkeypatch.setattr(installer, 'command', staged_command)
    monkeypatch.setattr(installer, 'validate_environment', lambda *args: '0.3.0')
    monkeypatch.setattr(installer, 'read_service', lambda *args: {'running': True, 'url': 'http://localhost:1234'})
    monkeypatch.setattr(installer, 'assert_idle', lambda *args: None)
    monkeypatch.setattr(installer, 'backup_data', lambda root, service, dest: dest.write_text('backup'))
    monkeypatch.setattr(installer, 'preserve_local_files', lambda *args: None)
    return root


def test_staging_failure_never_touches_old_installation(tmp_path, monkeypatch):
    root = prepare_update(tmp_path, monkeypatch)
    actions = []
    monkeypatch.setattr(installer, 'service_action', lambda root, action: actions.append(action))
    def fail(*args):
        raise RuntimeError('package verification failed')
    monkeypatch.setattr(installer, 'validate_environment', fail)
    with pytest.raises(RuntimeError, match='verification'):
        installer.install(root, 'repo', 'v0.3.0', update=True)
    assert (root / 'version.txt').read_text() == 'old'
    assert actions == []


def test_failed_service_promotion_restores_old_code_and_restarts(tmp_path, monkeypatch):
    root = prepare_update(tmp_path, monkeypatch)
    actions = []
    monkeypatch.setattr(installer, 'service_action', lambda root, action: actions.append((action, (root / 'version.txt').read_text())))
    monkeypatch.setattr(installer, 'wait_healthy', lambda *args: (_ for _ in ()).throw(RuntimeError('unhealthy')))
    with pytest.raises(RuntimeError, match='unhealthy'):
        installer.install(root, 'repo', 'v0.3.0', update=True)
    assert (root / 'version.txt').read_text() == 'old'
    assert actions == [('stop', 'old'), ('start', 'new'), ('stop', 'new'), ('start', 'old')]
    assert not list(installer.runtime_root(root).glob('*/bin/python'))


def test_successful_promotion_and_explicit_rollback(tmp_path, monkeypatch):
    root = prepare_update(tmp_path, monkeypatch)
    actions = []
    monkeypatch.setattr(installer, 'service_action', lambda root, action: actions.append(action))
    monkeypatch.setattr(installer, 'wait_healthy', lambda *args: None)
    installer.install(root, 'repo', 'v0.3.0', update=True)
    assert (root / 'version.txt').read_text() == 'new'
    manifest = json.loads((installer.rollback_root(root) / 'previous.json').read_text())
    assert (Path(manifest['previous']) / 'version.txt').read_text() == 'old'
    installer.rollback(root)
    assert (root / 'version.txt').read_text() == 'old'
    assert actions == ['stop', 'start', 'stop', 'start']


def test_dirty_checkout_is_not_modified(tmp_path, monkeypatch):
    root = prepare_update(tmp_path, monkeypatch)
    original = installer.command
    def dirty(args, **kwargs):
        if args[-2:] == ['status', '--porcelain']:
            return SimpleNamespace(stdout=' M local.py\n')
        return original(args, **kwargs)
    monkeypatch.setattr(installer, 'command', dirty)
    with pytest.raises(ValueError, match='local source changes'):
        installer.install(root, 'repo', 'v0.3.0', update=True)
    assert (root / 'version.txt').read_text() == 'old'


def test_bootstrap_supports_piped_stdin_without_bash_source():
    import os
    import shutil
    import subprocess
    if os.name == 'nt' or not shutil.which('bash') or hasattr(os, 'getuid') and os.getuid() == 0:
        pytest.skip('POSIX bootstrap runs as a regular user; Windows uses PowerShell')
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(['bash', '-s', '--', '--help'], input=(root / 'scripts/install.sh').read_text(),
                               text=True, capture_output=True, env={**os.environ, 'PANTHEON_REPO_URL': str(root)}, timeout=20)
    assert completed.returncode == 0, completed.stderr
    assert 'Install or update Pantheon transactionally' in completed.stdout
    assert 'unbound variable' not in completed.stderr
