"""Real Windows startup and ConPTY checks run on the Windows CI runner."""
import asyncio
import socket
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='requires native Windows')


def test_native_windows_service_health_and_stop(tmp_path, monkeypatch):
    from pantheon import windows_service
    from pantheon.installer import wait_healthy
    from pantheon.service import install_service, stop_service, uninstall_service
    monkeypatch.setenv('PANTHEON_MODEL_DOCS_SYNC', '0')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    workspace = tmp_path / 'workspace with spaces'
    workspace.mkdir()
    (workspace / '.env').write_text('PANTHEON_UI_AUTH_ENABLED=0\n')
    home = tmp_path / 'home'
    paths = install_service(workspace, port=port, backend='windows', home=home, python_executable=Path(sys.executable))
    try:
        assert paths.startup.exists()
        wait_healthy(f'http://127.0.0.1:{port}')
        assert windows_service.running(paths.definition)
        stop_service(backend='windows', home=home)
        assert not windows_service.running(paths.definition)
    finally:
        uninstall_service(backend='windows', home=home)


def test_native_conpty_stream_and_timeout(tmp_path):
    from pantheon.web.windows_terminal import command_events
    async def collect(command, timeout):
        return [item async for item in command_events(command, tmp_path, timeout)]
    result = asyncio.run(collect("Write-Output 'Pantheon native Windows'; exit 0", 10))
    assert any(event == 'stdout' and 'Pantheon native Windows' in value['text'] for event, value in result)
    assert result[-1][0] == 'exit'
    timed = asyncio.run(collect('Start-Sleep -Seconds 15', 1))
    assert any(event == 'error' and 'timed out' in value['message'] for event, value in timed)
