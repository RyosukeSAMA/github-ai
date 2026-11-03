"""Run on each target OS: bundle the core without depending on a user Python install."""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
    '--name', 'pantheon-runtime', '--distpath', str(root / 'dist'),
    '--workpath', str(root / 'build' / 'desktop-runtime'),
    '--specpath', str(root / 'build'), '--paths', str(root),
    '--collect-all', 'pantheon', '--collect-all', 'uvicorn',
    '--collect-all', 'keyring', '--collect-all', 'mcp',
    '--collect-all', 'openai', '--collect-all', 'anthropic',
    '--copy-metadata', 'pantheon-ai',
    str(root / 'scripts' / 'desktop' / 'runtime_entry.py'),
], check=True, cwd=root, env={**os.environ, 'PYINSTALLER_CONFIG_DIR': str(root / 'build' / 'pyinstaller-cache')})
