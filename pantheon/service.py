"""Manage Pantheon Web as a per-user background service."""

from __future__ import annotations

import json
import os
import platform
import plistlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SERVICE_LABEL = "ai.pantheon.web"
SYSTEMD_UNIT = "pantheon-web.service"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class ServiceError(RuntimeError):
    """Raised when the local service cannot be managed."""


@dataclass(frozen=True)
class ServicePaths:
    definition: Path
    stdout_log: Path
    stderr_log: Path
    startup: Path | None = None


@dataclass(frozen=True)
class ServiceStatus:
    platform: str
    installed: bool
    running: bool
    healthy: bool
    definition: Path
    url: str
    detail: str = ""


def service_platform(system: str | None = None) -> str:
    """Return the supported service backend for the current operating system."""
    name = (system or platform.system()).lower()
    if name == "darwin":
        return "launchd"
    if name == "linux":
        return "systemd"
    if name == "windows":
        return "windows"
    raise ServiceError("Pantheon background services support macOS, Linux and Windows.")


def service_paths(
    workspace: Path,
    *,
    backend: str | None = None,
    home: Path | None = None,
) -> ServicePaths:
    """Return service definition and log paths without changing the filesystem."""
    selected = backend or service_platform()
    user_home = (home or Path.home()).expanduser().resolve()
    if selected == "launchd":
        definition = user_home / "Library" / "LaunchAgents" / f"{SERVICE_LABEL}.plist"
        logs = user_home / "Library" / "Logs" / "Pantheon"
    elif selected == "systemd":
        definition = user_home / ".config" / "systemd" / "user" / SYSTEMD_UNIT
        logs = user_home / ".local" / "state" / "pantheon"
    elif selected == "windows":
        local = user_home / 'AppData' / 'Local' if home else Path(os.environ.get('LOCALAPPDATA', user_home / 'AppData/Local'))
        definition = local / 'Pantheon' / 'service.json'
        logs = local / 'Pantheon' / 'logs'
    else:
        raise ServiceError(f"Unsupported service backend: {selected}")
    return ServicePaths(
        definition=definition,
        stdout_log=logs / "web.stdout.log",
        stderr_log=logs / "web.stderr.log",
        startup=((user_home / 'AppData/Roaming' if home else Path(os.environ.get('APPDATA', user_home / 'AppData/Roaming'))) / 'Microsoft/Windows/Start Menu/Programs/Startup/Pantheon.lnk') if selected == 'windows' else None,
    )


def _web_arguments(
    workspace: Path,
    host: str,
    port: int,
    config: Path | None,
    python_executable: Path,
) -> list[str]:
    args = [
        str(python_executable),
        "-m",
        "pantheon.cli",
        "web",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if config is not None:
        config_path = config.expanduser()
        if not config_path.is_absolute():
            config_path = workspace / config_path
        args.extend(["--config", str(config_path.resolve())])
    return args


def _launchd_definition(
    workspace: Path,
    paths: ServicePaths,
    arguments: list[str],
) -> bytes:
    payload: dict[str, Any] = {
        "Label": SERVICE_LABEL,
        "ProgramArguments": arguments,
        "WorkingDirectory": str(workspace),
        "EnvironmentVariables": {
            "PANTHEON_WORKSPACE": str(workspace),
            "PYTHONUNBUFFERED": "1",
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"),
        },
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ProcessType": "Background",
        "StandardOutPath": str(paths.stdout_log),
        "StandardErrorPath": str(paths.stderr_log),
    }
    return plistlib.dumps(payload, sort_keys=False)


def _systemd_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return f'"{escaped}"'


def _systemd_definition(workspace: Path, arguments: list[str]) -> str:
    command = " ".join(_systemd_quote(argument) for argument in arguments)
    inherited_path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
    return "\n".join(
        [
            "[Unit]",
            "Description=Pantheon local multi-agent workspace",
            "After=network-online.target",
            "Wants=network-online.target",
            "",
            "[Service]",
            "Type=simple",
            f"WorkingDirectory={_systemd_quote(str(workspace))}",
            f"Environment={_systemd_quote(f'PANTHEON_WORKSPACE={workspace}')}",
            'Environment="PYTHONUNBUFFERED=1"',
            f"Environment={_systemd_quote(f'PATH={inherited_path}')}",
            f"ExecStart={command}",
            "Restart=on-failure",
            "RestartSec=3",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=check,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ServiceError(f"Required service command was not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise ServiceError(detail) from exc


def install_service(
    workspace: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    config: Path | None = None,
    python_executable: Path | None = None,
    allow_network: bool = False,
    start: bool = True,
    backend: str | None = None,
    home: Path | None = None,
) -> ServicePaths:
    """Install and optionally start the current environment as a user service."""
    selected = backend or service_platform()
    root = workspace.expanduser().resolve()
    if not root.is_dir():
        raise ServiceError(f"Workspace does not exist: {root}")
    if host not in LOOPBACK_HOSTS and not allow_network:
        raise ServiceError(
            "Refusing to expose the file and terminal APIs to the network. "
            "Use --allow-network only after enabling Settings -> Security."
        )
    if not 1 <= port <= 65535:
        raise ServiceError("Port must be between 1 and 65535.")

    interpreter = (python_executable or Path(sys.executable)).expanduser()
    if not interpreter.is_absolute():
        interpreter = Path.cwd() / interpreter
    interpreter = Path(os.path.abspath(interpreter))
    if not interpreter.exists():
        raise ServiceError(f"Python executable does not exist: {interpreter}")

    paths = service_paths(root, backend=selected, home=home)
    paths.definition.parent.mkdir(parents=True, exist_ok=True)
    paths.stdout_log.parent.mkdir(parents=True, exist_ok=True)
    arguments = _web_arguments(root, host, port, config, interpreter)

    if selected == "launchd":
        paths.definition.write_bytes(_launchd_definition(root, paths, arguments))
        if start:
            target = f"gui/{os.getuid()}"
            _run(["launchctl", "bootout", target, str(paths.definition)], check=False)
            _run(["launchctl", "bootstrap", target, str(paths.definition)])
            _run(["launchctl", "enable", f"{target}/{SERVICE_LABEL}"])
            _run(["launchctl", "kickstart", "-k", f"{target}/{SERVICE_LABEL}"])
    elif selected == "systemd":
        paths.definition.write_text(
            _systemd_definition(root, arguments),
            encoding="utf-8",
        )
        _run(["systemctl", "--user", "daemon-reload"])
        if start:
            _run(["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT])
    elif selected == "windows":
        from pantheon import windows_service
        from pantheon.core.credentials import atomic_text
        if paths.definition.exists():
            windows_service.stop(paths.definition)
        config_path = config.expanduser() if config else None
        if config_path and not config_path.is_absolute():
            config_path = root / config_path
        atomic_text(paths.definition, json.dumps({'workspace': str(root), 'host': host, 'port': port,
                    'config': str(config_path.resolve()) if config_path else None,
                    'arguments': arguments, 'stdout_log': str(paths.stdout_log), 'stderr_log': str(paths.stderr_log)}))
        try:
            windows_service.install_shortcut(paths.definition, paths.startup, interpreter)
            if start:
                windows_service.start(paths.definition)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            raise ServiceError(str(exc)) from exc
    else:
        raise ServiceError(f"Unsupported service backend: {selected}")
    return paths


def start_service(*, backend: str | None = None, home: Path | None = None) -> None:
    selected = backend or service_platform()
    paths = service_paths(Path.cwd(), backend=selected, home=home)
    if not paths.definition.exists():
        raise ServiceError("Pantheon service is not installed. Run `pantheon service install` first.")
    if selected == "launchd":
        target = f"gui/{os.getuid()}"
        _run(["launchctl", "bootstrap", target, str(paths.definition)], check=False)
        _run(["launchctl", "kickstart", "-k", f"{target}/{SERVICE_LABEL}"])
    elif selected == 'windows':
        from pantheon import windows_service
        windows_service.start(paths.definition)
    else:
        _run(["systemctl", "--user", "start", SYSTEMD_UNIT])


def stop_service(*, backend: str | None = None, home: Path | None = None) -> None:
    selected = backend or service_platform()
    paths = service_paths(Path.cwd(), backend=selected, home=home)
    if not paths.definition.exists():
        raise ServiceError("Pantheon service is not installed.")
    if selected == "launchd":
        _run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(paths.definition)],
            check=False,
        )
    elif selected == 'windows':
        from pantheon import windows_service
        windows_service.stop(paths.definition)
    else:
        _run(["systemctl", "--user", "stop", SYSTEMD_UNIT])


def restart_service(*, backend: str | None = None, home: Path | None = None) -> None:
    selected = backend or service_platform()
    paths = service_paths(Path.cwd(), backend=selected, home=home)
    if not paths.definition.exists():
        raise ServiceError("Pantheon service is not installed. Run `pantheon service install` first.")
    if selected == "launchd":
        domain = f"gui/{os.getuid()}"
        _run(["launchctl", "bootstrap", domain, str(paths.definition)], check=False)
        _run(["launchctl", "kickstart", "-k", f"{domain}/{SERVICE_LABEL}"])
    elif selected == 'windows':
        stop_service(backend=selected, home=home)
        start_service(backend=selected, home=home)
    else:
        _run(["systemctl", "--user", "restart", SYSTEMD_UNIT])


def uninstall_service(*, backend: str | None = None, home: Path | None = None) -> bool:
    selected = backend or service_platform()
    paths = service_paths(Path.cwd(), backend=selected, home=home)
    if not paths.definition.exists():
        return False
    if selected == "launchd":
        _run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(paths.definition)],
            check=False,
        )
    elif selected == 'windows':
        stop_service(backend=selected, home=home)
        paths.startup.unlink(missing_ok=True)
    else:
        _run(["systemctl", "--user", "disable", "--now", SYSTEMD_UNIT], check=False)
    paths.definition.unlink(missing_ok=True)
    if selected == "systemd":
        _run(["systemctl", "--user", "daemon-reload"], check=False)
    return True


def _health(url: str, timeout: float = 1.5) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/health", timeout=timeout) as response:
            return response.status == 200, f"HTTP {response.status}"
    except (OSError, urllib.error.URLError) as exc:
        return False, str(exc)


def service_status(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    backend: str | None = None,
    home: Path | None = None,
) -> ServiceStatus:
    selected = backend or service_platform()
    paths = service_paths(Path.cwd(), backend=selected, home=home)
    installed = paths.definition.exists()
    running = False
    detail = "not installed"
    if installed and selected == "launchd":
        target = f"gui/{os.getuid()}/{SERVICE_LABEL}"
        result = _run(["launchctl", "print", target], check=False)
        running = result.returncode == 0 and "state = running" in result.stdout
        detail = (result.stderr or result.stdout or "loaded").strip().splitlines()[0]
    elif installed and selected == 'windows':
        from pantheon import windows_service
        running = windows_service.running(paths.definition)
        detail = 'running' if running else 'stopped'
        config = json.loads(paths.definition.read_text(encoding='utf-8'))
        host, port = config['host'], config['port']
    elif installed:
        result = _run(["systemctl", "--user", "is-active", SYSTEMD_UNIT], check=False)
        running = result.returncode == 0 and result.stdout.strip() == "active"
        detail = (result.stdout or result.stderr or "unknown").strip()
    url = f"http://{host}:{port}"
    healthy, health_detail = _health(url)
    if healthy:
        detail = health_detail
    return ServiceStatus(
        platform=selected,
        installed=installed,
        running=running,
        healthy=healthy,
        definition=paths.definition,
        url=url,
        detail=detail,
    )


def read_service_logs(
    *,
    lines: int = 80,
    follow: bool = False,
    backend: str | None = None,
    home: Path | None = None,
) -> int:
    selected = backend or service_platform()
    if selected == "systemd":
        command = ["journalctl", "--user", "-u", SYSTEMD_UNIT, "-n", str(max(1, lines))]
        if follow:
            command.append("-f")
        return subprocess.call(command)

    paths = service_paths(Path.cwd(), backend=selected, home=home)
    existing = [path for path in (paths.stdout_log, paths.stderr_log) if path.exists()]
    if not existing:
        raise ServiceError(f"No service logs found under {paths.stdout_log.parent}")
    if selected == 'windows':
        streams = []
        try:
            for path in existing:
                stream = path.open('r', encoding='utf-8', errors='replace')
                print(f'==> {path} <==')
                print(''.join(stream.readlines()[-max(1, lines):]), end='')
                streams.append(stream)
            while follow:
                for stream in streams:
                    print(stream.read(), end='', flush=True)
                time.sleep(.5)
        except KeyboardInterrupt:
            pass
        finally:
            for stream in streams:
                stream.close()
        return 0
    command = ["tail", "-n", str(max(1, lines))]
    if follow:
        command.append("-f")
    command.extend(str(path) for path in existing)
    return subprocess.call(command)
