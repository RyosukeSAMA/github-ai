"""Windowless Windows service runner with cooperative local stop requests."""
from __future__ import annotations

import json
import os
import secrets
import sys
import threading
from pathlib import Path

from pantheon.core.runtime import RuntimeLease


def run(definition: Path):
    import uvicorn

    from pantheon import windows_service
    from pantheon.web import create_app

    config = json.loads(definition.read_text(encoding='utf-8'))
    os.environ['PANTHEON_WORKSPACE'] = config['workspace']
    os.chdir(config['workspace'])
    lease = RuntimeLease(definition.with_suffix('.lock'), {'operation': 'windows-service'})
    lease.acquire()
    stop_watch = threading.Event()
    nonce = secrets.token_hex(16)
    try:
        for channel in ('stdout', 'stderr'):
            path = Path(config[channel + '_log'])
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
                path.replace(path.with_suffix(path.suffix + '.previous'))
            setattr(sys, channel, path.open('a', buffering=1, encoding='utf-8'))
        app = create_app(config.get('config'), bind_host=config['host'], bind_port=config['port'])
        server = uvicorn.Server(uvicorn.Config(app, host=config['host'], port=config['port'], timeout_graceful_shutdown=5))
        def watch():
            while not stop_watch.wait(.2):
                try:
                    request = json.loads(definition.with_suffix('.stop.json').read_text(encoding='utf-8'))
                    if request.get('nonce') == nonce:
                        server.should_exit = True
                        return
                except (ValueError, OSError):
                    pass
        threading.Thread(target=watch, daemon=True).start()
        windows_service.write_pid(definition, nonce)
        server.run()
    finally:
        stop_watch.set()
        if windows_service.metadata(definition).get('nonce') == nonce:
            definition.with_suffix('.pid.json').unlink(missing_ok=True)
        lease.release()


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
