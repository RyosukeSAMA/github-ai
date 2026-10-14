"""Persist connection evidence without storing credentials or provider responses."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


class ReadinessStore:
    TTL = 24 * 60 * 60

    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        try:
            os.chmod(self.path, 0o600)
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS probes (identity TEXT PRIMARY KEY, checked REAL, ok INTEGER)')
                db.execute('CREATE TABLE IF NOT EXISTS preferences (name TEXT PRIMARY KEY, value TEXT)')
                yield db
        finally:
            db.close()

    @staticmethod
    def identity(provider: str, model: str, endpoint: str, key: str) -> str:
        endpoint = endpoint or {'openai': 'https://api.openai.com/v1', 'anthropic': 'https://api.anthropic.com',
                                'deepseek': 'https://api.deepseek.com', 'ollama': 'http://localhost:11434'}.get(provider, '')
        if provider == 'ollama' and endpoint.rstrip('/').endswith('/v1'):
            endpoint = endpoint.rstrip('/')[:-3]
        payload = [provider, model, endpoint.rstrip('/'), hashlib.sha256(key.encode()).hexdigest()]
        return hashlib.sha256(json.dumps(payload).encode()).hexdigest()

    def record(self, provider: str, model: str, endpoint: str, key: str, ok: bool):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO probes VALUES (?, ?, ?)',
                       (self.identity(provider, model, endpoint, key), time.time(), int(ok)))

    def health(self, provider: str, model: str, endpoint: str, key: str) -> dict:
        with self.connect() as db:
            row = db.execute('SELECT checked, ok FROM probes WHERE identity=?',
                             (self.identity(provider, model, endpoint, key),)).fetchone()
        if not row:
            return {'state': 'untested', 'checked_at': None}
        checked, ok = row
        return {'state': ('verified' if ok else 'failed') if time.time() - checked < self.TTL else 'expired',
                'checked_at': checked}

    def preference(self, name: str, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM preferences WHERE name=?', (name,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_preference(self, name: str, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO preferences VALUES (?, ?)', (name, json.dumps(value)))
