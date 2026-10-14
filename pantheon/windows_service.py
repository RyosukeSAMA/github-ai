"""Windows per-user startup and verified process management (no administrator)."""
from __future__ import annotations

import base64
import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

from pantheon.core.credentials import atomic_text


def process_identity(pid: int, *, terminate: bool = False, expected: int | None = None) -> int | None:
    """Hold a process handle while checking its creation time to avoid PID reuse."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000 | (1 if terminate else 0), False, pid)
    if not handle:
        return None
    try:
        creation, exit_time, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        status = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(status)) or status.value != 259:
            return None
        if not kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return None
        identity = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        if terminate and identity == expected:
            if not kernel.TerminateProcess(handle, 0):
                raise OSError('Could not stop the verified Pantheon service process')
        return identity
    finally:
        kernel.CloseHandle(handle)


def metadata(definition: Path) -> dict:
    try:
        value = json.loads(definition.with_suffix('.pid.json').read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (ValueError, OSError):
        return {}


def running(definition: Path) -> bool:
    saved = metadata(definition)
    pid, identity = saved.get('pid'), saved.get('created')
    return type(pid) is int and pid > 0 and type(identity) is int and process_identity(pid) == identity


def install_shortcut(definition: Path, shortcut: Path, interpreter: Path):
    shortcut.parent.mkdir(parents=True, exist_ok=True)
    pythonw = interpreter.with_name('pythonw.exe')
    target = str(pythonw if pythonw.exists() else interpreter)
    arguments = subprocess.list2cmdline(['-m', 'pantheon.service_runner', str(definition)])
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"
    script = ("$ErrorActionPreference='Stop'; $w=New-Object -ComObject WScript.Shell; "
              f"$s=$w.CreateShortcut({quote(shortcut)}); $s.TargetPath={quote(target)}; "
              f"$s.Arguments={quote(arguments)}; $s.WorkingDirectory={quote(definition.parent)}; "
              "$s.WindowStyle=7; $s.Description='Pantheon local workspace'; $s.Save()")
    encoded = base64.b64encode(script.encode('utf-16-le')).decode()
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded], check=True, capture_output=True)


def start(definition: Path):
    if running(definition):
        return
    config = json.loads(definition.read_text(encoding='utf-8'))
    interpreter = Path(config['arguments'][0])
    pythonw = interpreter.with_name('pythonw.exe')
    definition.with_suffix('.stop.json').unlink(missing_ok=True)
    log = Path(config['stderr_log'])
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('a', encoding='utf-8') as output:
        child = subprocess.Popen([str(pythonw if pythonw.exists() else interpreter), '-m', 'pantheon.service_runner', str(definition)],
                                 cwd=config['workspace'], stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                 creationflags=0x08000000, close_fds=True)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if running(definition):
            return
        if child.poll() is not None:
            raise RuntimeError(f'Pantheon failed to start. Check {log}')
        time.sleep(.1)
    raise RuntimeError(f'Pantheon startup timed out. Check {log}')


def stop(definition: Path):
    if not running(definition):
        return
    saved = metadata(definition)
    atomic_text(definition.with_suffix('.stop.json'), json.dumps({'nonce': saved['nonce']}))
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if not running(definition):
            return
        time.sleep(.1)
    process_identity(saved['pid'], terminate=True, expected=saved['created'])


def write_pid(definition: Path, nonce: str):
    identity = process_identity(os.getpid())
    if identity is None:
        raise RuntimeError('Cannot identify the Windows service process')
    atomic_text(definition.with_suffix('.pid.json'), json.dumps({'pid': os.getpid(), 'created': identity, 'nonce': nonce}))
