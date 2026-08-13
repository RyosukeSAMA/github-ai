from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def e2e_workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    workspace = tmp_path_factory.mktemp("pantheon-e2e-workspace")
    config_dir = workspace / "config"
    config_dir.mkdir()
    (workspace / ".env").write_text("", encoding="utf-8")
    (config_dir / "pantheon.yaml").write_text(
        """
pantheon:
  hermes:
    model: e2e-model
    provider: openai
  roles:
    hephaestus: {model: e2e-model, provider: openai}
    athena: {model: e2e-model, provider: openai}
    apollo: {model: e2e-model, provider: openai}
    chronos: {model: none, provider: none}
llm_providers:
  openai:
    api_key: ""
    base_url: https://api.openai.com/v1
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return workspace


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def live_server_url(e2e_workspace: Path) -> str:
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "PANTHEON_WORKSPACE": str(e2e_workspace),
            "PANTHEON_UI_AUTH_ENABLED": "false",
            "PYTHONUNBUFFERED": "1",
        }
    )
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "PANTHEON_CONFIG",
        "PANTHEON_UI_PASSWORD",
        "PANTHEON_UI_PASSWORD_HASH",
        "PANTHEON_UI_SESSION_SECRET",
    ):
        env.pop(key, None)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pantheon.cli",
            "web",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--config",
            str(e2e_workspace / "config" / "pantheon.yaml"),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                pytest.fail(f"Pantheon server exited before E2E tests:\n{output}")
            try:
                with urllib.request.urlopen(f"{url}/api/health", timeout=0.5) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("Pantheon E2E server did not become healthy in 20 seconds")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
