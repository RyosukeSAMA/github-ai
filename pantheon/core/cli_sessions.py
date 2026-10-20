"""Explicit CLI history, separate from Web chats and workspace memory."""
import json
import re
import uuid
from pathlib import Path

from pantheon.core.credentials import atomic_text
from pantheon.core.runtime import file_mutex


class CliSessions:
    def __init__(self, root: Path):
        self.root = root / 'cli-sessions'

    def path(self, identity):
        if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', identity):
            raise ValueError('Session ID needs 1–80 letters, numbers, hyphens or underscores.')
        return self.root / (identity + '.json')

    def lock(self, identity):
        self.root.mkdir(parents=True, exist_ok=True)
        return file_mutex(self.path(identity).with_suffix('.lock'))

    def load(self, identity):
        path = self.path(identity)
        if not path.exists():
            return {'id':identity, 'mode':'auto', 'messages':[]}
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError('CLI session exceeds 10 MiB. Start a new session.')
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or value.get('id') != identity or not isinstance(value.get('messages'), list):
            raise ValueError('CLI session is damaged; restore it from backup.')
        return value

    def save(self, value):
        text = json.dumps(value, ensure_ascii=False)
        if len(text.encode()) > 10 * 1024 * 1024 or len(value['messages']) > 2000:
            raise ValueError('CLI session is full. The task result is in Task history; start a new session.')
        atomic_text(self.path(value['id']), text)

    def list(self):
        return sorted(path.stem for path in self.root.glob('*.json'))

    @staticmethod
    def new_id():
        return 'chat-' + uuid.uuid4().hex[:12]
