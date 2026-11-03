"""Packaged desktop sidecar. Only the owning native process supplies its token."""
from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--locate', action='store_true')
    args = parser.parse_args()
    root = Path(args.workspace).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit('Choose an existing project directory')
    os.environ['PANTHEON_WORKSPACE'] = str(root)
    from pantheon.core.paths import DataPaths
    paths = DataPaths.for_workspace(root)
    if args.locate:
        print(json.dumps({'descriptor': str(paths.state / 'desktop-runtime.json'),
                          'runtime_lock': str(paths.state / 'runtime.lock')}), flush=True)
        return
    if len(os.environ.get('PANTHEON_DESKTOP_TOKEN', '')) < 32:
        raise SystemExit('Desktop bootstrap token is missing')
    os.chdir(root)
    import uvicorn

    from pantheon.web.app import create_app
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    app = create_app(bind_host='127.0.0.1', bind_port=port)
    print(json.dumps({'port': port, 'instance_id': app.state.desktop.instance_id}), flush=True)
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='warning',
                                         access_log=False, ws='none', timeout_graceful_shutdown=8))
    server.run(sockets=[sock])


if __name__ == '__main__':
    main()
