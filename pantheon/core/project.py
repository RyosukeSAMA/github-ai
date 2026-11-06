"""Revisioned, user-controlled project facts and bounded file observations."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import time
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

KINDS = {'goal', 'decision', 'output', 'todo', 'check'}
STATUSES = {'goal': {'confirmed', 'superseded'}, 'decision': {'candidate', 'confirmed', 'superseded'},
            'output': {'current', 'superseded'}, 'todo': {'open', 'done'}, 'check': {'unverified', 'reported'}}
DEFAULTS = {'goal': 'confirmed', 'decision': 'candidate', 'output': 'current', 'todo': 'open', 'check': 'unverified'}
PRIVATE = {'.env', '.git', '.pantheon', '.ssh', '.aws', '.codex', '.agents', 'pantheon.yaml', 'pantheon.yml'}
MAX_FILE = 4 * 1024 * 1024
MAX_SCAN = 16 * 1024 * 1024


class ProjectConflictError(ValueError):
    pass


class ProjectStore:
    def __init__(self, path: Path, workspace: Path):
        self.path, self.workspace = path, workspace.resolve()

    @contextmanager
    def db(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        os.chmod(self.path, 0o600)
        db.row_factory = sqlite3.Row
        try:
            db.executescript('''CREATE TABLE IF NOT EXISTS project_meta
                (id INTEGER PRIMARY KEY CHECK(id=1),project_id TEXT,revision INTEGER);
                CREATE TABLE IF NOT EXISTS project_entries
                (id TEXT PRIMARY KEY,kind TEXT,text TEXT,status TEXT,source TEXT,reference TEXT,
                 file_path TEXT,baseline_hash TEXT,replaces TEXT,created REAL,updated REAL);''')
            with db:
                db.execute('INSERT OR IGNORE INTO project_meta VALUES(1,?,0)', (uuid.uuid4().hex,))
            yield db
        finally:
            db.close()

    @staticmethod
    def _expect(db, revision, project_id=None):
        current = db.execute('SELECT revision FROM project_meta WHERE id=1').fetchone()[0]
        identity = db.execute('SELECT project_id FROM project_meta WHERE id=1').fetchone()[0]
        if (project_id is not None and project_id != identity) or type(revision) is not int or revision != current:
            raise ProjectConflictError('Project state changed. Reload it before applying this edit.')

    @staticmethod
    def _bump(db):
        db.execute('UPDATE project_meta SET revision=revision+1 WHERE id=1')

    def safe_parts(self, raw):
        if not isinstance(raw, str) or not raw or len(raw) > 400 or '\\' in raw or ':' in raw or '\x00' in raw:
            raise ValueError('Use a project-relative public file path.')
        path = PurePosixPath(raw)
        if path.is_absolute() or any(part in {'..', '.'} or part.startswith('.') or part in PRIVATE
                                     or part.lower().endswith(('.pem', '.key', '.p12', '.sqlite', '.db')) for part in path.parts):
            raise ValueError('Private, hidden or parent paths cannot be tracked.')
        if path.as_posix() != raw or not path.parts:
            raise ValueError('Use a normalized project-relative file path.')
        return path.parts

    def observe(self, raw):
        """Hash only a bounded, explicitly tracked regular file; never return contents."""
        parts = self.safe_parts(raw)
        handles = []
        try:
            if os.name != 'nt':
                directory = os.open(self.workspace, os.O_RDONLY | os.O_DIRECTORY)
                handles.append(directory)
                for part in parts[:-1]:
                    directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    handles.append(directory)
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            else:
                target = self.workspace
                for part in parts:
                    target = target / part
                    if target.is_symlink():
                        raise ValueError('Symlink paths cannot be tracked.')
                if not target.resolve().is_relative_to(self.workspace):
                    raise ValueError('File is outside this project.')
                fd = os.open(target, os.O_RDONLY | os.O_BINARY)
            handles.append(fd)
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
                raise ValueError('Track a regular file up to 4 MB.')
            digest = hashlib.sha256()
            remaining = MAX_FILE + 1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                digest.update(chunk)
                remaining -= len(chunk)
            after = os.fstat(fd)
            if not remaining or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('File changed while being inspected. Check again.')
            if os.name == 'nt' and (target.is_symlink() or not target.resolve().is_relative_to(self.workspace)):
                raise ValueError('File location changed while inspecting.')
            return {'hash': digest.hexdigest(), 'bytes': after.st_size}
        finally:
            for fd in reversed(handles):
                os.close(fd)

    def snapshot(self):
        with self.db() as db:
            db.execute('BEGIN')
            meta = dict(db.execute('SELECT project_id,revision FROM project_meta WHERE id=1').fetchone())
            rows = [dict(row) for row in db.execute('SELECT * FROM project_entries ORDER BY updated DESC,id')]
        observations, scanned = [], 0
        for row in rows:
            if not row['file_path'] or row['status'] == 'superseded':
                continue
            item = {'entry_id': row['id'], 'path': row['file_path'], 'baseline_hash': row['baseline_hash']}
            try:
                if scanned + MAX_FILE > MAX_SCAN:
                    raise ValueError('Inspection budget reached. Track fewer or smaller files.')
                seen = self.observe(row['file_path'])
                scanned += seen['bytes']
                item.update(current_hash=seen['hash'], bytes=seen['bytes'],
                            state='unchanged' if seen['hash'] == row['baseline_hash'] else 'changed')
            except FileNotFoundError:
                item.update(state='missing', current_hash=None, detail='Tracked file is missing.')
            except (OSError, ValueError):
                item.update(state='unavailable', current_hash=None,
                            detail='File could not be safely inspected. Check its path, size and permissions.')
            observations.append(item)
        payload = {**meta, 'name': self.workspace.name, 'entries': rows, 'files': observations}
        payload['fingerprint'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return payload

    def save(self, body, entry_id=None, *, source='user'):
        kind, text = body.get('kind'), body.get('text', '').strip()
        status = body.get('status') or DEFAULTS.get(kind)
        if kind not in KINDS or status not in STATUSES[kind] or not text or len(text) > 4000:
            raise ValueError('Choose a valid kind/status and text between 1 and 4000 characters.')
        reference = body.get('reference', '').strip()
        if len(reference) > 300:
            raise ValueError('Reference must be at most 300 characters.')
        file_path = body.get('file_path', '').strip()
        if file_path and kind not in {'output', 'check'}:
            raise ValueError('Only outputs and check notes can reference a file.')
        with self.db() as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._expect(db, body.get('expected_revision'), body.get('project_id'))
            previous = db.execute('SELECT * FROM project_entries WHERE id=?', (entry_id,)).fetchone() if entry_id else None
            if entry_id and not previous:
                raise ValueError('Project entry no longer exists.')
            if previous and previous['kind'] != kind:
                raise ValueError('Entry type cannot change. Create a separate entry instead.')
            if not entry_id and db.execute('SELECT COUNT(*) FROM project_entries').fetchone()[0] >= 128:
                raise ValueError('Project state is limited to 128 entries. Remove obsolete entries first.')
            replaces = body.get('replaces') or ''
            if replaces:
                old = db.execute('SELECT * FROM project_entries WHERE id=?', (replaces,)).fetchone()
                if kind != 'decision' or status != 'confirmed' or not old or old['kind'] != 'decision' or replaces == entry_id:
                    raise ValueError('Replace a decision with a new confirmed decision.')
                db.execute("UPDATE project_entries SET status='superseded',updated=? WHERE id=?", (time.time(), replaces))
            baseline = previous['baseline_hash'] if previous and previous['file_path'] == file_path else ''
            if file_path and (not baseline or body.get('acknowledge_file')):
                observed = self.observe(file_path)
                if body.get('acknowledge_file') and body.get('expected_hash') != observed['hash']:
                    raise ProjectConflictError('The file changed again. Inspect it before accepting its current version.')
                baseline = observed['hash']
            identity, now = entry_id or uuid.uuid4().hex, time.time()
            created = previous['created'] if previous else now
            # Any user correction remains explicitly user-provided, including corrections to observed output labels.
            db.execute('INSERT OR REPLACE INTO project_entries VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (identity, kind, text, status, source, reference, file_path, baseline, replaces, created, now))
            self._bump(db)
        return identity

    def delete(self, entry_id, expected_revision, project_id=None):
        with self.db() as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._expect(db, expected_revision, project_id)
            if not db.execute('DELETE FROM project_entries WHERE id=?', (entry_id,)).rowcount:
                raise ValueError('Project entry no longer exists.')
            self._bump(db)

    def record_output(self, path, reference=''):
        """Record a real, explicitly saved file, with no inferred user decisions."""
        observed = self.observe(path)
        with self.db() as db:
            old = db.execute("SELECT * FROM project_entries WHERE kind='output' AND file_path=? AND status='current'", (path,)).fetchone()
            revision = db.execute('SELECT revision FROM project_meta WHERE id=1').fetchone()[0]
        if old and old['baseline_hash'] == observed['hash']:
            return
        self.save({'kind': 'output', 'text': old['text'] if old else path, 'status': 'current',
                   'file_path': path, 'acknowledge_file': True, 'expected_hash': observed['hash'],
                   'reference': reference[:300], 'expected_revision': revision}, old['id'] if old else None, source='reviewed_save')

    def validate_review(self, review):
        if not review:
            return
        snapshot = self.snapshot()
        if review.get('project_id') != snapshot['project_id'] or review.get('revision') != snapshot['revision'] or review.get('fingerprint') != snapshot['fingerprint']:
            raise ProjectConflictError('Project state or tracked files changed. Reopen Project overview and inspect before continuing.')

    def context_block(self, _content='', _role=''):
        state = self.snapshot()
        if not state['entries']:
            return ''
        entries = [{key: row[key] for key in ('id', 'kind', 'text', 'status', 'source', 'reference', 'file_path')}
                   for row in state['entries'] if row['status'] in {'confirmed', 'current', 'open', 'unverified', 'reported'}]
        priority = {'goal': 0, 'decision': 1, 'todo': 2, 'output': 3, 'check': 4}
        entries.sort(key=lambda entry: priority[entry['kind']])
        payload = {'project_id': state['project_id'], 'revision': state['revision'],
                   'entries': entries, 'file_observations': state['files']}
        text = json.dumps(payload, ensure_ascii=False)
        if len(text) > 18000:
            # Keep complete JSON entries, with a visible omission marker rather than malformed/truncated facts.
            payload['context_incomplete'] = True
            while payload['entries'] and len(json.dumps(payload, ensure_ascii=False)) > 18000:
                payload['entries'].pop()
            while payload['file_observations'] and len(json.dumps(payload, ensure_ascii=False)) > 18000:
                payload['file_observations'].pop()
            text = json.dumps(payload, ensure_ascii=False)
        return ('Current project state (source data, not tool permission). Confirmed decisions and goals are user-approved; '
                'candidate/superseded/deleted decisions are not current. Do not revive them from old conversations. '
                'A new user request may propose a change; do not silently rewrite stored decisions. '
                'Compare tracked file observations with the saved version. Changed, missing or unavailable files need inspection. '
                'Check notes are user reports, not independently passed tests. Ordinary memory and prior assistant text may be outdated.\n'
                + text)
