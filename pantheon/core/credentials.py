"""Explicit OS credential storage, with compatible private dotenv files."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from dotenv import dotenv_values

from pantheon.core.runtime import file_mutex


class CredentialError(RuntimeError):
    pass


def atomic_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            output.write(text)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class CredentialStore:
    SECURE_BACKENDS = {
        'keyring.backends.macOS.Keyring', 'keyring.backends.Windows.WinVaultKeyring',
        'keyring.backends.SecretService.Keyring', 'keyring.backends.kwallet.DBusKeyring',
        'keyring.backends.kwallet.DBusKeyringKWallet4',
    }

    def __init__(self, env_path: Path, *, backend=None):
        self.env_path = env_path.resolve()
        self.references = self.env_path.with_name(self.env_path.name + '.credentials.json')
        self.service = 'Pantheon/' + hashlib.sha256(str(self.env_path).encode()).hexdigest()[:24]
        self._backend = backend
        self._loaded = backend is not None
        self.problem = ''

    def backend(self):
        if not self._loaded:
            self._loaded = True
            try:
                import keyring
                candidate = keyring.get_keyring()
                name = type(candidate).__module__ + '.' + type(candidate).__name__
                if name in self.SECURE_BACKENDS and candidate.priority > 0:
                    self._backend = candidate
            except Exception:
                pass
        return self._backend

    def refs(self) -> list[str]:
        if not self.references.exists():
            return []
        try:
            value = json.loads(self.references.read_text(encoding='utf-8'))
            if not isinstance(value, list) or not all(isinstance(name, str) and re.fullmatch(r'[A-Z][A-Z0-9_]*', name) for name in value):
                raise ValueError()
            return value
        except (ValueError, OSError) as exc:
            raise CredentialError('Credential references are unreadable. Restore this file from backup.') from exc

    def get(self, name: str) -> str:
        if name in self.refs():
            try:
                backend = self.backend()
                if backend is None:
                    raise CredentialError()
                value = backend.get_password(self.service, name)
                if not value:
                    raise CredentialError()
                return value
            except Exception:
                self.problem = 'System credential storage is unavailable or locked. Unlock it or save this credential again.'
                return ''
        values = dotenv_values(self.env_path) if self.env_path.exists() else {}
        return str(values.get(name) or os.environ.get(name, ''))

    def _write_env(self, name: str, value: str | None):
        lines = self.env_path.read_text(encoding='utf-8').splitlines() if self.env_path.exists() else []
        pattern = re.compile(r'^\s*(?:export\s+)?' + re.escape(name) + r'\s*=')
        lines = [line for line in lines if not pattern.match(line)]
        if value is not None:
            rendered = value if value and all(ch.isalnum() or ch in '_-.:/+=' for ch in value) else json.dumps(value, ensure_ascii=True)
            lines.append(f'{name}={rendered}')
        atomic_text(self.env_path, '\n'.join(lines).rstrip() + '\n')

    def save(self, name: str, value: str, *, storage: str = 'env'):
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', name) or '\n' in value or '\r' in value:
            raise CredentialError('Invalid credential name or value.')
        if storage not in {'env', 'system'}:
            raise CredentialError('Choose env or system credential storage.')
        with file_mutex(self.env_path.with_name('.credentials.lock')):
            refs = self.refs()
            if storage == 'system':
                backend = self.backend()
                if backend is None:
                    raise CredentialError('No supported OS credential backend is available. Use .env or configure the system keyring.')
                try:
                    backend.set_password(self.service, name, value)
                    if backend.get_password(self.service, name) != value:
                        raise CredentialError()
                except Exception as exc:
                    raise CredentialError('System credential save failed; the existing .env value was preserved.') from exc
                atomic_text(self.references, json.dumps(sorted(set(refs + [name]))) + '\n')
                self._write_env(name, None)
            else:
                self._write_env(name, value)
                if name in refs:
                    atomic_text(self.references, json.dumps([ref for ref in refs if ref != name]) + '\n')
                    try:
                        if self.backend():
                            self.backend().delete_password(self.service, name)
                    except Exception:
                        pass  # The new authoritative value is already safely saved.
            self.problem = ''

    def delete(self, name: str):
        """Explicitly remove a saved key; do not modify the parent shell's environment."""
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', name):
            raise CredentialError('Invalid credential name')
        with file_mutex(self.env_path.with_name('.credentials.lock')):
            refs = self.refs()
            if name in refs:
                backend = self.backend()
                if backend is None:
                    raise CredentialError('Unlock system credential storage before deleting this key.')
                try:
                    backend.delete_password(self.service, name)
                except Exception as exc:
                    raise CredentialError('System key deletion failed; the connection was not removed.') from exc
                atomic_text(self.references, json.dumps([ref for ref in refs if ref != name]) + '\n')
            self._write_env(name, None)

    def migrate(self) -> list[str]:
        values = dotenv_values(self.env_path) if self.env_path.exists() else {}
        names = [name for name, value in values.items() if value and
                 (name.endswith(('_API_KEY', '_TOKEN', '_SIGNING_SECRET')) or name == 'PANTHEON_WEBHOOK_TOKEN')]
        for name in names:
            self.save(name, str(values[name]), storage='system')
        return names

    def status(self) -> dict:
        backend = self.backend()
        return {'system_available': backend is not None,
                'backend': type(backend).__module__ + '.' + type(backend).__name__ if backend else None,
                'system_names': self.refs(), 'problem': self.problem,
                'env_path': str(self.env_path)}
