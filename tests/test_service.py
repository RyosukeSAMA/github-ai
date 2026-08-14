from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path

import pytest

import pantheon.service as service


def test_service_platform_maps_supported_systems() -> None:
    assert service.service_platform("Darwin") == "launchd"
    assert service.service_platform("Linux") == "systemd"
    with pytest.raises(service.ServiceError, match="macOS and Linux"):
        service.service_platform("Windows")


def test_install_launchd_writes_loopback_service(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    environment = workspace / ".venv"
    (environment / "bin").mkdir(parents=True)
    environment_python = environment / "bin" / "python"
    environment_python.symlink_to(Path(sys.executable))
    home = tmp_path / "home"
    commands: list[tuple[list[str], bool]] = []

    def fake_run(command: list[str], *, check: bool = True):
        commands.append((command, check))
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(service, "_run", fake_run)
    paths = service.install_service(
        workspace,
        backend="launchd",
        home=home,
        python_executable=environment_python,
    )

    assert paths.definition == home / "Library/LaunchAgents/ai.pantheon.web.plist"
    assert paths.stdout_log == home / "Library/Logs/Pantheon/web.stdout.log"
    payload = plistlib.loads(paths.definition.read_bytes())
    assert payload["Label"] == service.SERVICE_LABEL
    assert payload["WorkingDirectory"] == str(workspace)
    assert payload["RunAtLoad"] is True
    assert payload["KeepAlive"] == {"SuccessfulExit": False}
    assert payload["ProcessType"] == "Background"
    assert payload["EnvironmentVariables"]["PANTHEON_WORKSPACE"] == str(workspace)
    assert payload["EnvironmentVariables"]["PATH"] == os.environ["PATH"]
    assert payload["ProgramArguments"] == [
        str(environment_python),
        "-m",
        "pantheon.cli",
        "web",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    assert any(command[0][0:2] == ["launchctl", "bootstrap"] for command in commands)


def test_install_systemd_writes_user_unit_without_start(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool = True):
        commands.append(command)
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(service, "_run", fake_run)
    paths = service.install_service(
        workspace,
        backend="systemd",
        home=home,
        python_executable=Path(sys.executable),
        config=Path("config/pantheon.yaml"),
        start=False,
    )

    unit = paths.definition.read_text(encoding="utf-8")
    assert "Restart=on-failure" in unit
    assert f'WorkingDirectory="{workspace}"' in unit
    assert f'"--config" "{workspace / "config/pantheon.yaml"}"' in unit
    assert commands == [["systemctl", "--user", "daemon-reload"]]


def test_install_refuses_network_binding_without_explicit_override(tmp_path) -> None:
    with pytest.raises(service.ServiceError, match="Refusing to expose"):
        service.install_service(
            tmp_path,
            host="0.0.0.0",
            backend="launchd",
            home=tmp_path / "home",
            python_executable=Path(sys.executable),
            start=False,
        )


def test_uninstall_missing_service_is_idempotent(tmp_path) -> None:
    assert service.uninstall_service(backend="launchd", home=tmp_path) is False
