"""Stream an explicitly requested command through native Windows ConPTY."""
from __future__ import annotations

import asyncio
import base64
import os
import socket
from pathlib import Path


async def command_events(command: str, cwd: Path, timeout: int):
    try:
        from winpty import PtyProcess
    except ImportError:
        yield 'error', {'message': 'Native Windows terminal needs pywinpty. Reinstall Pantheon with its locked dependencies.'}
        return
    encoded = base64.b64encode(command.encode('utf-16-le')).decode()
    args = ['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded]
    process = None
    reader = None
    spawn = asyncio.create_task(asyncio.to_thread(PtyProcess.spawn, args, cwd=str(cwd), env=dict(os.environ), dimensions=(30, 120), backend='0'))
    try:
        process = await asyncio.shield(spawn)
        yield 'start', {'command': command, 'cwd': str(cwd), 'pid': process.pid, 'backend': 'ConPTY'}
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                yield 'error', {'message': f'command timed out after {timeout}s'}
                return
            reader = asyncio.create_task(asyncio.to_thread(process.read, 4096))
            try:
                text = await asyncio.wait_for(asyncio.shield(reader), remaining)
            except EOFError:
                break
            except asyncio.TimeoutError:
                yield 'error', {'message': f'command timed out after {timeout}s'}
                return
            if text:
                yield 'stdout', {'text': text}
        returncode = await asyncio.to_thread(process.wait)
        yield 'exit', {'returncode': returncode, 'cwd': str(cwd)}
    except Exception as exc:
        yield 'error', {'message': str(exc)}
    finally:
        if process is None:
            try:
                process = await spawn
            except Exception:
                pass
        if process is not None:
            try:
                await asyncio.to_thread(process.close, force=True)
            finally:
                try:
                    process.fileobj.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                process.fileobj.close()
                process._server.close()
        if reader:
            await asyncio.gather(reader, return_exceptions=True)
