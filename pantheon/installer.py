"""Standalone transactional installer; runs before Pantheon dependencies exist."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

REPOSITORY = 'https://github.com/RyosukeSAMA/github-ai.git'
SKIP_PARTS = {'.venv', 'venv', '__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache', 'build', 'dist'}


def command(args, *, cwd=None, capture=False, env=None):
    return subprocess.run([str(arg) for arg in args], cwd=cwd, check=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None, text=True, env=env)


def interpreter(root: Path) -> Path:
    return root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def release(repo: str, requested: str) -> str:
    if requested != 'latest':
        if not re.fullmatch(r'v\d+\.\d+\.\d+', requested):
            raise ValueError('Choose latest or a stable tag such as v0.3.0')
        return requested
    tags = command(['git', 'ls-remote', '--tags', '--refs', repo], capture=True).stdout
    versions = []
    for line in tags.splitlines():
        tag = line.split('/')[-1]
        if re.fullmatch(r'v\d+\.\d+\.\d+', tag):
            versions.append((tuple(map(int, tag[1:].split('.'))), tag))
    if not versions:
        raise ValueError('No stable Pantheon release found')
    return max(versions)[1]


def repository_identity(value: str) -> str:
    if '://' in value or value.startswith('git@'):
        return value.rstrip('/')
    return os.path.normcase(str(Path(value).resolve()))


def read_service(root: Path) -> dict:
    if not interpreter(root).exists():
        return {}
    code = '''import json, plistlib, shlex
from pathlib import Path
from pantheon.service import service_status
s = service_status()
payload = dict(installed=s.installed, running=s.running, url=s.url)
if s.installed:
    if s.platform == 'launchd':
        definition = plistlib.loads(s.definition.read_bytes())
        payload.update(python=definition['ProgramArguments'][0], workspace=definition['WorkingDirectory'])
    elif s.platform == 'windows':
        definition = json.loads(s.definition.read_text())
        payload.update(python=definition['arguments'][0], workspace=definition['workspace'])
    else:
        definition = dict(line.split('=',1) for line in s.definition.read_text().splitlines() if '=' in line)
        payload.update(python=shlex.split(definition['ExecStart'])[0].replace('%%','%'), workspace=shlex.split(definition['WorkingDirectory'])[0].replace('%%','%'))
print(json.dumps(payload))'''
    result = command([interpreter(root), '-c', code], cwd=root, capture=True)
    payload = json.loads(result.stdout)
    managed = payload.get('python', '')
    if not managed or not (Path(managed).is_relative_to(root) or Path(managed).is_relative_to(runtime_root(root))):
        return {}  # Never stop a service belonging to a different installation.
    return payload


def service_action(root: Path, action: str):
    command([interpreter(root), '-m', 'pantheon.cli', 'service', action], cwd=root)


def runtime_root(root: Path) -> Path:
    return root.parent / ('.' + root.name + '.runtimes')


def rollback_root(root: Path) -> Path:
    return root.parent / ('.' + root.name + '.rollback')


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def install_launcher(root: Path):
    if os.environ.get('PANTHEON_SKIP_PATH') == '1':
        return
    if os.name == 'nt':
        import winreg
        directory = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Pantheon/bin'
        launcher = directory / 'pantheon.cmd'
        content = '@echo off\r\nREM Pantheon managed launcher\r\n' + '"' + str(interpreter(root)).replace('%', '%%') + '" -m pantheon.cli %*\r\n'
    else:
        directory = Path.home() / '.local/bin'
        launcher = directory / 'pantheon'
        content = '#!/bin/sh\n# Pantheon managed launcher\nexec ' + shlex.quote(str(interpreter(root))) + ' -m pantheon.cli "$@"\n'
    directory.mkdir(parents=True, exist_ok=True)
    if launcher.exists() and 'Pantheon managed launcher' not in launcher.read_text(encoding='utf-8', errors='replace'):
        raise ValueError(f'An existing unrelated launcher was preserved: {launcher}')
    launcher.write_text(content, encoding='utf-8')
    os.chmod(launcher, 0o755)
    if os.name == 'nt':
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            try:
                path, kind = winreg.QueryValueEx(key, 'Path')
            except FileNotFoundError:
                path, kind = '', winreg.REG_EXPAND_SZ
            if os.path.normcase(str(directory)) not in {os.path.normcase(item.rstrip('\\/')) for item in path.split(';')}:
                winreg.SetValueEx(key, 'Path', 0, kind, path.rstrip(';') + ';' + str(directory))
    elif str(directory) not in os.environ.get('PATH', '').split(os.pathsep):
        shell = Path(os.environ.get('SHELL', '')).name
        profiles = ['.zprofile', '.zshrc'] if shell == 'zsh' else ['.bashrc', '.bash_profile' if (Path.home() / '.bash_profile').exists() else '.profile']
        marker = '# Pantheon CLI path'
        for name in profiles:
            profile = Path.home() / name
            original = profile.read_text(encoding='utf-8') if profile.exists() else ''
            if marker not in original:
                with profile.open('a', encoding='utf-8') as output:
                    output.write('\n' + marker + '\nexport PATH="$HOME/.local/bin:$PATH"\n')
    print('Open a new terminal to use: pantheon web')


def preserve_local_files(old: Path, candidate: Path):
    ignored = command(['git', '-C', old, 'ls-files', '--others', '--ignored', '--exclude-standard', '-z'], capture=True).stdout
    tracked = set(command(['git', '-C', candidate, 'ls-files', '-z'], capture=True).stdout.split('\0'))
    # Rollback carries the current state tree, including deletions, rather than reviving old records.
    if (candidate / '.pantheon').is_dir() and '.pantheon' not in tracked:
        shutil.rmtree(candidate / '.pantheon')
    for name in ignored.split('\0'):
        if not name:
            continue
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe local file path')
        if SKIP_PARTS.intersection(relative.parts) or any(part.endswith('.egg-info') for part in relative.parts):
            continue
        if name in tracked:
            raise ValueError(f'A local ignored file conflicts with a tracked release file: {name}')
        source, destination = old / relative, candidate / relative
        if source.is_file() or source.is_symlink():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination, follow_symlinks=False)


def link_environment(candidate: Path, environment: Path):
    destination = candidate / '.venv'
    if os.name == 'nt':
        # Directory junctions work for normal Windows users without Developer Mode.
        def quote(value):
            return "'" + str(value).replace("'", "''") + "'"
        script = ("$ErrorActionPreference='Stop'; New-Item -ItemType Junction "
                  f"-Path {quote(destination)} -Target {quote(environment)} | Out-Null")
        encoded = base64.b64encode(script.encode('utf-16-le')).decode()
        command(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded])
    else:
        destination.symlink_to(environment, target_is_directory=True)


def validate_environment(environment: Path, candidate: Path) -> str:
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    command([python, '-m', 'pip', 'check'])
    env = dict(os.environ, PANTHEON_WORKSPACE=str(candidate), PANTHEON_STATE_MODE='workspace', PANTHEON_MODEL_DOCS_SYNC='0')
    code = 'from pantheon import __version__; from pantheon.web import create_app; create_app(); print(__version__)'
    return command([python, '-c', code], cwd=environment, capture=True, env=env).stdout.strip()


def wait_healthy(url: str, version: str | None = None):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url.rstrip('/') + '/api/health', timeout=1) as response:
                payload = json.load(response)
                if payload.get('status') == 'ok' and (version is None or payload.get('version') == version):
                    return
        except (OSError, ValueError):
            pass
        time.sleep(.25)
    raise RuntimeError('The updated service did not pass its health check')


def assert_idle(root: Path, service: dict):
    python = interpreter(root)
    if not python.exists():
        return
    code = '''from pathlib import Path
from pantheon.core.paths import DataPaths
from pantheon.core.tasks import TaskStore
import sys
p=DataPaths.for_workspace(Path(sys.argv[1]))
if (p.state / 'tasks.sqlite').exists() and any(t['status']=='running' for t in TaskStore(p.state / 'tasks.sqlite').list()):
    raise SystemExit('Wait for running tasks to finish before updating or rolling back.')'''
    command([python, '-c', code, service.get('workspace', str(root))], cwd=root)


def backup_data(root: Path, service: dict, destination: Path):
    code = '''from pathlib import Path
from pantheon.core.paths import DataPaths
from pantheon.core.backup import export_backup
import sys
export_backup(DataPaths.for_workspace(Path(sys.argv[1])), Path(sys.argv[2]))'''
    command([interpreter(root), '-c', code, service.get('workspace', str(root)), destination], cwd=root)


def rollback(root: Path):
    manifest = rollback_root(root) / 'previous.json'
    saved = json.loads(manifest.read_text(encoding='utf-8'))
    previous = Path(saved['previous'])
    if previous.parent != rollback_root(root) or not previous.is_dir() or previous.is_symlink():
        raise ValueError('No valid previous installation is available')
    service = read_service(root)
    assert_idle(root, service)
    if service.get('running'):
        service_action(root, 'stop')
    preserve_local_files(root, previous)
    current = rollback_root(root) / ('replaced-' + uuid.uuid4().hex)
    root.rename(current)
    try:
        previous.rename(root)
        if service.get('running'):
            service_action(root, 'start')
            wait_healthy(service['url'])
    except Exception:
        if root.exists():
            root.rename(previous)
        current.rename(root)
        if service.get('running'):
            service_action(root, 'start')
        raise
    atomic_json(manifest, {'previous': str(current), 'restored_from': str(previous), 'data_backup': saved.get('data_backup')})
    print(f'Restored the previous version. Workspace data and credentials were preserved at {root}.')


def install(root: Path, repo: str, version: str, *, update: bool):
    if not root.is_absolute() or not root.parent.is_dir() or root == root.parent:
        raise ValueError('Choose an absolute installation path with an existing parent folder')
    existing = root.exists()
    if existing:
        if not update or not (root / '.git').is_dir():
            raise ValueError('Destination exists. Use update mode only for a Pantheon Git installation.')
        if repository_identity(command(['git', '-C', root, 'remote', 'get-url', 'origin'], capture=True).stdout.strip()) != repository_identity(repo):
            raise ValueError('Destination belongs to a different repository')
        status = command(['git', '-C', root, 'status', '--porcelain'], capture=True).stdout.strip()
        linked_environment = (root / '.venv').resolve().is_relative_to(runtime_root(root))
        dirty = [line for line in status.splitlines() if not (line == '?? .venv' and linked_environment)]
        if dirty:
            raise ValueError('Save or commit local source changes before updating')
    selected = release(repo, version)
    candidate = Path(tempfile.mkdtemp(prefix='.' + root.name + '.candidate-', dir=root.parent))
    identity = uuid.uuid4().hex
    environment = runtime_root(root) / identity
    previous = rollback_root(root) / identity
    service = {}
    stopped = promoted = False
    data_backup = rollback_root(root) / ('data-' + identity + '.zip')
    try:
        command(['git', 'clone', '--depth', '1', '--branch', selected, repo, candidate])
        command([sys.executable, '-m', 'venv', environment])
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        lock = candidate / 'requirements.lock'
        if not lock.exists():
            raise ValueError('Transactional installation requires a release with requirements.lock (v0.2.6 or newer).')
        command([python, '-m', 'pip', 'install', '--require-hashes', '-r', lock])
        # New releases lock their build tools. Older releases use pip's isolated builder.
        build_flags = ['--no-build-isolation'] if re.search(r'^wheel==', lock.read_text(), re.MULTILINE) else []
        command([python, '-m', 'pip', 'install', '--no-deps', *build_flags, candidate])
        atomic_json(environment / 'pantheon-install.json', {'target': str(root), 'repo': repo})
        installed_version = validate_environment(environment, candidate)
        if 'v' + installed_version != selected:
            raise ValueError('Release tag and installed package version do not match')
        link_environment(candidate, environment)
        if existing:
            service = read_service(root)
            assert_idle(root, service)
            if service.get('running'):
                service_action(root, 'stop')
                stopped = True
            rollback_root(root).mkdir(parents=True, exist_ok=True)
            backup_data(root, service, data_backup)
            preserve_local_files(root, candidate)
            root.rename(previous)
        candidate.rename(root)
        promoted = True
        if stopped:
            service_action(root, 'start')
            wait_healthy(service['url'], installed_version)
        install_launcher(root)
        if existing:
            atomic_json(rollback_root(root) / 'previous.json', {'previous': str(previous), 'data_backup': str(data_backup)})
        print(f'Pantheon {selected} installed at {root}.')
        print(f'Start: {interpreter(root)} -m pantheon.cli web')
        if existing:
            print(f'Rollback: {interpreter(root)} -m pantheon.cli update --rollback')
    except Exception:
        if promoted and root.exists():
            if stopped:
                try:
                    service_action(root, 'stop')
                except Exception:
                    pass
            root.rename(candidate)
        if previous.exists():
            previous.rename(root)
        if stopped and root.exists():
            service_action(root, 'start')
        # Failed staging must not remove the old installation or its environment.
        shutil.rmtree(environment, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(candidate, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description='Install or update Pantheon transactionally')
    default = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Pantheon/app' if os.name == 'nt' else Path.home() / 'github-ai'
    parser.add_argument('--target', type=Path, default=Path(os.environ.get('PANTHEON_INSTALL_DIR', default)))
    parser.add_argument('--repo', default=os.environ.get('PANTHEON_REPO_URL', REPOSITORY))
    parser.add_argument('--version', default=os.environ.get('PANTHEON_VERSION', 'latest'))
    parser.add_argument('--update', action='store_true', default=os.environ.get('PANTHEON_UPDATE') == '1')
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    root = args.target.expanduser().absolute()
    if root.is_symlink():
        raise ValueError('The installation directory must not be a symbolic link')
    root = root.resolve()
    # Exclusive OS lock works even when the target directory is moved during promotion.
    lock_path = root.parent / ('.' + root.name + '.install.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as lock:
        lock.seek(0)
        lock.write(b' ')
        lock.flush()
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.rollback:
            rollback(root)
        else:
            install(root, args.repo, args.version, update=args.update)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Pantheon installer failed: {error}', file=sys.stderr)
        raise SystemExit(1) from error
