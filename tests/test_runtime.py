import json

import pytest

from pantheon.core.runtime import RuntimeLease


def test_runtime_lock_prevents_duplicates_and_can_be_reacquired(tmp_path):
    first = RuntimeLease(tmp_path / 'runtime.lock', {'port': 8000})
    second = RuntimeLease(tmp_path / 'runtime.lock', {'port': 9000})
    first.acquire()
    first.file.seek(0)
    assert json.loads(first.file.read())['port'] == 8000
    with pytest.raises(RuntimeError, match='already running'):
        second.acquire()
    first.release()
    second.acquire()
    second.file.seek(0)
    assert json.loads(second.file.read())['port'] == 9000
    second.release()


def test_runtime_lock_is_exclusive_across_processes(tmp_path):
    import subprocess
    import sys
    lock = tmp_path / 'runtime.lock'
    first = RuntimeLease(lock, {})
    first.acquire()
    try:
        result = subprocess.run([sys.executable, '-c',
            'import sys; from pathlib import Path; from pantheon.core.runtime import RuntimeLease; '
            'RuntimeLease(Path(sys.argv[1]), {}).acquire()', str(lock)],
            capture_output=True, text=True, timeout=20)
        assert result.returncode != 0
        assert 'already running' in result.stderr
    finally:
        first.release()


def test_runtime_can_restart_after_owner_crashes(tmp_path):
    import subprocess
    import sys

    lock = tmp_path / 'runtime.lock'
    child = subprocess.Popen([sys.executable, '-u', '-c', '''
import sys
from pathlib import Path
from pantheon.core.runtime import RuntimeLease
lease = RuntimeLease(Path(sys.argv[1]), {})
lease.acquire()
print('ready', flush=True)
sys.stdin.readline()
''', str(lock)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'ready'
        child.kill()
        child.communicate(timeout=10)
        with RuntimeLease(lock, {'restarted': True}):
            pass
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)
