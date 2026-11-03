"""Durable desktop sessions, detached runs, artifact review and engineering isolation.

The adapter consumes the same ask/stream handler as Web. It does not implement a
second planner, scheduler, credentials store, approval system or billing model.
"""
from __future__ import annotations

import asyncio
import base64
import difflib
import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from pantheon import __version__
from pantheon.core.context import HISTORY_MESSAGE_CHARACTERS, HISTORY_MESSAGES
from pantheon.core.credentials import atomic_text
from pantheon.core.runtime import file_mutex

ACTIVE = {'queued', 'running', 'stopping'}
ROLES = {'hermes', 'hephaestus', 'athena', 'apollo'}
PRIVATE_NAMES = {'.env', '.pantheon', '.git', '.aws', '.ssh', '.codex', '.agents'}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class DesktopRuntime:
    def __init__(self, services, conversations, workspace: Path, ask, request_type, resolve_path):
        self.services, self.conversations, self.workspace = services, conversations, workspace
        self.ask, self.request_type, self.resolve_path = ask, request_type, resolve_path
        self.token = os.environ.get('PANTHEON_DESKTOP_TOKEN') or secrets.token_urlsafe(32)
        self.instance_id = uuid.uuid4().hex
        self.db_path = services.paths.state / 'desktop.sqlite'
        self.descriptor = services.paths.state / 'desktop-runtime.json'
        self.jobs: dict[str, asyncio.Task] = {}

    @contextmanager
    def db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.db_path, timeout=10)
        os.chmod(self.db_path, 0o600)
        db.row_factory = sqlite3.Row
        try:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, request_id TEXT UNIQUE,
                session_id TEXT, task_id TEXT, status TEXT, created REAL, updated REAL, data TEXT);
                CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, run_id TEXT, data TEXT);
                CREATE INDEX IF NOT EXISTS event_run ON events(run_id,id);
                CREATE TABLE IF NOT EXISTS artifacts (id TEXT PRIMARY KEY, run_id TEXT, session_id TEXT,
                title TEXT, kind TEXT, created REAL, data TEXT);
                CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, status TEXT, data TEXT);
            ''')
            with db:
                yield db
        finally:
            db.close()

    def identity(self, challenge: str = ''):
        return {'api_version': 1, 'version': __version__, 'instance_id': self.instance_id,
                'workspace': str(self.workspace), 'workspace_name': self.workspace.name,
                'challenge': challenge, 'pid': os.getpid()}

    def start(self, host, port):
        # Registry is private local capability material, never sent to a renderer.
        atomic_text(self.descriptor, json.dumps({**self.identity(), 'host': host, 'port': port,
                                                 'token': self.token}))
        recovered = []
        with self.db() as db:
            for row in db.execute("SELECT * FROM runs WHERE status IN ('queued','running','stopping')").fetchall():
                core = self.services.tasks.get(row['task_id']) if row['task_id'] else None
                status = core['status'] if core and core['status'] not in ACTIVE else 'interrupted'
                db.execute('UPDATE runs SET status=?,updated=? WHERE id=?', (status, time.time(), row['id']))
                self.event(row['id'], 'recovered', {'status': status, 'message': 'Previous run ended. Check durable results before retrying.'}, db=db)
                if core and status == 'completed':
                    content = self.ledger_content(core)
                    data = json.loads(row['data'])
                    data['result'] = {'status': status, 'content': content, 'success': True}
                    db.execute('UPDATE runs SET data=? WHERE id=?', (json.dumps(data), row['id']))
                    recovered.append((row['id'], row['session_id'], core['id'], content))
        for run_id, session_id, task_id, content in recovered:
            try:
                def reconcile(item):
                    if not any(m.get('runId') == run_id and m['role'] == 'assistant' for m in item['messages']):
                        item['messages'].append({'role': 'assistant', 'text': content[:200000], 'runId': run_id,
                                                 'taskId': task_id, 'status': 'completed'})
                self.mutate(session_id, reconcile)
                if content:
                    self.capture_artifacts(run_id, session_id, content)
            except (ValueError, HTTPException):
                self.event(run_id, 'persistence_warning', {'message': 'Recovered result is in the task archive.'})

    async def close(self):
        for run_id, job in list(self.jobs.items()):
            self.stop(run_id)
            job.cancel()
        if self.jobs:
            await asyncio.gather(*tuple(self.jobs.values()), return_exceptions=True)
        try:
            if json.loads(self.descriptor.read_text()).get('instance_id') == self.instance_id:
                self.descriptor.unlink(missing_ok=True)
        except (OSError, ValueError):
            pass

    def sessions(self):
        return self.conversations.get()['sessions']

    @staticmethod
    def public_session(item):
        return {**{k: v for k, v in item.items() if k not in {'messages', 'editor_draft'}},
                'message_count': len(item.get('messages', [])), 'has_editor_draft': bool(item.get('editor_draft'))}

    def session(self, session_id):
        return next((item for item in self.sessions() if item['id'] == session_id), None)

    def mutate(self, session_id, edit, *, expected=None):
        with file_mutex(self.services.paths.state / 'desktop-sessions.lock'):
            for _ in range(5):
                current = self.conversations.get()
                items = current['sessions']
                item = next((value for value in items if value['id'] == session_id), None)
                if item is None:
                    raise HTTPException(404, 'Conversation not found')
                if expected is not None and item.get('desktop_version', 0) != expected:
                    raise HTTPException(409, 'This task changed in another window. Reload before editing.')
                edit(item)
                item['desktop_version'] = item.get('desktop_version', 0) + 1
                item['updatedAt'] = int(time.time() * 1000)
                if self.conversations.replace(items, current['revision']) is not None:
                    return item
            raise HTTPException(409, 'Conversations changed. Refresh and retry.')

    def new_session(self, title='New task'):
        now = int(time.time() * 1000)
        item = {'id': uuid.uuid4().hex, 'title': str(title)[:200], 'mode': 'auto', 'overrides': {},
                'messages': [], 'createdAt': now, 'updatedAt': now, 'draft': '', 'pinned': False,
                'archived': False, 'desktop_version': 0}
        with file_mutex(self.services.paths.state / 'desktop-sessions.lock'):
            for _ in range(5):
                current = self.conversations.get()
                if self.conversations.replace([item, *current['sessions']], current['revision']) is not None:
                    return item
        raise HTTPException(409, 'Conversations changed. Refresh and retry.')

    def edit_session(self, session_id, body):
        allowed = {'title', 'mode', 'overrides', 'draft', 'pinned', 'archived', 'editor_draft', 'attachment_draft', 'expected_version'}
        if set(body) - allowed or type(body.get('expected_version')) is not int:
            raise HTTPException(400, 'An edit version and supported fields are required')
        for key in ('title', 'draft', 'mode'):
            if key in body and (not isinstance(body[key], str) or len(body[key]) > (200 if key == 'title' else 24000)):
                raise HTTPException(400, f'Invalid {key}')
        for key in ('pinned', 'archived'):
            if key in body and type(body[key]) is not bool:
                raise HTTPException(400, f'Invalid {key}')
        if 'mode' in body and body['mode'] not in {'auto', 'multi', *(f'role:{name}' for name in ROLES | {'chronos'})}:
            raise HTTPException(400, 'Unsupported task mode')
        if 'editor_draft' in body:
            editor = body['editor_draft']
            if not isinstance(editor, dict) or set(editor) - {'path', 'content', 'hash'} or not isinstance(editor.get('content', ''), str) or len(editor.get('content', '').encode()) > 1000000:
                raise HTTPException(400, 'Invalid file editor draft')
            if editor.get('path'):
                self.safe_path(editor['path'])
        if 'overrides' in body:
            value = body['overrides']
            if not isinstance(value, dict) or set(value) - ROLES or any(
                not isinstance(choice, dict) or set(choice) - {'provider', 'model'} or
                any(not isinstance(v, str) or len(v) > 160 for v in choice.values()) for choice in value.values()
            ):
                raise HTTPException(400, 'Invalid role assignments')
        if 'attachment_draft' in body:
            identities = body['attachment_draft']
            if not isinstance(identities, list) or len(identities) > 5 or any(not isinstance(value, str) for value in identities):
                raise HTTPException(400, 'Use up to five attachment IDs')
            try:
                body['attachment_draft'] = [self.services.media.get(value)[0]['id'] for value in identities]
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
        item = self.mutate(session_id, lambda item: item.update({k: v for k, v in body.items() if k != 'expected_version'}), expected=body['expected_version'])
        return self.public_session(item)

    def event(self, run_id, event, data, *, db=None):
        value = json.dumps({'event': event, 'data': data}, ensure_ascii=False)
        if db is not None:
            db.execute('INSERT INTO events(run_id,data) VALUES (?,?)', (run_id, value))
            return
        with self.db() as connection:
            self.event(run_id, event, data, db=connection)

    def run(self, run_id):
        with self.db() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise HTTPException(404, 'Run not found')
        value = dict(row)
        value['data'] = json.loads(value['data'])
        return value

    def runs(self):
        with self.db() as db:
            rows = db.execute('SELECT * FROM runs ORDER BY created DESC LIMIT 500').fetchall()
        return [{**dict(row), 'data': json.loads(row['data'])} for row in rows]

    def events(self, run_id, after=0):
        run = self.run(run_id)
        with self.db() as db:
            rows = db.execute('SELECT id,data FROM events WHERE run_id=? AND id>? ORDER BY id LIMIT 300', (run_id, after)).fetchall()
        return {'run': run, 'events': [{'id': row['id'], **json.loads(row['data'])} for row in rows]}

    def start_run(self, session_id, body):
        item = self.session(session_id)
        if item is None:
            raise HTTPException(404, 'Conversation not found')
        request_id = body.get('request_id')
        prompt = body.get('prompt', '')
        if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', request_id):
            raise HTTPException(400, 'A unique request ID is required')
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 24000:
            raise HTTPException(400, 'Use a task prompt between 1 and 24000 characters')
        resume_id = body.get('resume_task_id')
        # The shared handler validates provider/attachment choices and uses bounded history.
        history = [{'role': 'user' if m['role'] == 'user' else 'assistant', 'content': m['text'][:HISTORY_MESSAGE_CHARACTERS]}
                   for m in item['messages'] if m['role'] in {'user', 'assistant'}][-HISTORY_MESSAGES:]
        try:
            req = self.request_type(task=prompt, mode=item['mode'], overrides=item.get('overrides', {}), history=history,
                                    attachments=body.get('attachments', []), resume_task_id=resume_id,
                                    acknowledge_effects=body.get('acknowledge_effects', False))
        except ValidationError as exc:
            raise HTTPException(400, 'Invalid task, attachment or model assignment') from exc
        run_id = uuid.uuid4().hex
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT id FROM runs WHERE request_id=?', (request_id,)).fetchone()
            if previous:
                if self.run(previous['id'])['session_id'] != session_id:
                    raise HTTPException(409, 'Request ID already belongs to another task')
                return self.run(previous['id'])
            if db.execute("SELECT 1 FROM runs WHERE session_id=? AND status IN ('queued','running','stopping')", (session_id,)).fetchone():
                raise HTTPException(409, 'This conversation already has an active run')
            if db.execute("SELECT COUNT(*) FROM runs WHERE status IN ('queued','running','stopping')").fetchone()[0] >= 4:
                raise HTTPException(409, 'Four runs are active. Stop or finish one before starting another.')
            now = time.time()
            db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)', (run_id, request_id, session_id, '', 'queued', now, now,
                       json.dumps({'prompt': prompt, 'mode': item['mode'], 'overrides': item.get('overrides', {}), 'resume_task_id': resume_id})))
        try:
            def append(session):
                session['messages'].append({'role': 'user', 'text': prompt, 'runId': run_id})
                session['draft'] = ''
                session['attachment_draft'] = []
            self.mutate(session_id, append, expected=body.get('expected_version'))
        except BaseException:
            with self.db() as db:
                db.execute('DELETE FROM runs WHERE id=?', (run_id,))
            raise
        job = asyncio.create_task(self.consume(run_id, session_id, req))
        self.jobs[run_id] = job
        job.add_done_callback(lambda _job: self.jobs.pop(run_id, None))
        return self.run(run_id)

    async def consume(self, run_id, session_id, req):
        final = None
        try:
            with self.db() as db:
                db.execute("UPDATE runs SET status='running' WHERE id=?", (run_id,))
            response = await self.ask(req)
            buffer = ''
            async for chunk in response.body_iterator:
                buffer += chunk.decode() if isinstance(chunk, bytes) else chunk
                while '\n\n' in buffer:
                    raw, buffer = buffer.split('\n\n', 1)
                    name = next((line[7:] for line in raw.splitlines() if line.startswith('event: ')), 'message')
                    payload = json.loads('\n'.join(line[6:] for line in raw.splitlines() if line.startswith('data: ')) or '{}')
                    self.event(run_id, name, payload)
                    if payload.get('task_id'):
                        with self.db() as db:
                            db.execute('UPDATE runs SET task_id=?,updated=? WHERE id=?', (payload['task_id'], time.time(), run_id))
                    if self.run(run_id)['status'] == 'stopping' and self.run(run_id)['task_id']:
                        self.services.tasks.cancel(self.run(run_id)['task_id'])
                    if name == 'done':
                        final = payload
                    elif name == 'error':
                        final = {'status': 'failed', 'content': payload.get('message', 'Run failed'), 'success': False}
            if final is None:
                core = self.run(run_id)
                ledger = self.services.tasks.get(core['task_id']) if core['task_id'] else None
                final = {'status': 'interrupted', 'success': False,
                         'content': 'Output ended before a final result. Check task history before retrying.'}
                if ledger and ledger['status'] not in ACTIVE:
                    final = {'status': ledger['status'], 'content': self.ledger_content(ledger), 'success': ledger['status'] == 'completed'}
        except asyncio.CancelledError:
            final = {'status': 'interrupted', 'content': 'Service stopped. Check completed work before resuming.', 'success': False}
        except Exception as exc:
            final = {'status': 'failed', 'content': str(getattr(exc, 'detail', exc)), 'success': False}
            self.event(run_id, 'error', {'message': final['content']})
        finally:
            if final:
                status = final.get('status') or ('completed' if final.get('success') else 'failed')
                with self.db() as db:
                    db.execute('UPDATE runs SET status=?,updated=?,data=? WHERE id=?',
                               (status, time.time(), json.dumps({**self.run(run_id)['data'], 'result': final}), run_id))
                self.event(run_id, 'desktop_final', final)
                try:
                    self.mutate(session_id, lambda session: session['messages'].append(
                        {'role': 'assistant', 'text': str(final.get('content', ''))[:200000], 'runId': run_id,
                         'taskId': self.run(run_id)['task_id'], 'status': status}))
                    if status == 'completed' and final.get('content'):
                        self.capture_artifacts(run_id, session_id, str(final['content']))
                except (ValueError, HTTPException):
                    self.event(run_id, 'persistence_warning', {'message': 'Task result is durable; conversation storage is full or changed. Open the task archive.'})

    def stop(self, run_id):
        run = self.run(run_id)
        if run['status'] in ACTIVE:
            with self.db() as db:
                db.execute("UPDATE runs SET status='stopping' WHERE id=?", (run_id,))
            if run['task_id']:
                self.services.tasks.cancel(run['task_id'])
        return self.run(run_id)

    def ledger_content(self, task):
        data = task.get('data', {})
        path = self.services.tasks.archive_path(task['id'])
        if path.is_file():
            try:
                return str(json.loads(path.read_text(encoding='utf-8')).get('content', ''))[:1000000]
            except (OSError, ValueError):
                pass
        return str(data.get('result', ''))

    def capture_artifacts(self, run_id, session_id, content):
        pieces = [('Task result', 'document', 'result.md', content)]
        for i, match in enumerate(re.finditer(r'```([\w.+-]*)[^\n]*\n(.*?)```', content, re.S), 1):
            language, text = match.groups()
            extension = {'javascript': 'js', 'typescript': 'ts', 'python': 'py', 'markdown': 'md'}.get(language.lower(), language.lower())
            if extension in {'html', 'css', 'js', 'ts', 'py', 'md', 'json', 'txt', 'csv', 'svg'}:
                pieces.append((f'Generated {extension.upper()}', 'web' if extension in {'html', 'css', 'js'} else 'document', f'artifact-{i}.{extension}', text))
        with self.db() as db:
            if db.execute('SELECT 1 FROM artifacts WHERE run_id=?', (run_id,)).fetchone():
                return
            for title, kind, name, text in pieces[:30]:
                db.execute('INSERT INTO artifacts VALUES (?,?,?,?,?,?,?)', (uuid.uuid4().hex, run_id, session_id, title, kind, time.time(),
                           json.dumps({'filename': name, 'content': text[:1000000], 'version': 1})))

    def artifacts(self, query=''):
        with self.db() as db:
            rows = db.execute('SELECT * FROM artifacts ORDER BY created DESC LIMIT 1000').fetchall()
        result = [{**dict(row), **json.loads(row['data'])} for row in rows]
        for item in result:
            item.pop('data', None)
        return [item for item in result if query.casefold() in (item['title'] + item['content']).casefold()]

    def safe_path(self, raw):
        if not isinstance(raw, str) or not raw or any(part in PRIVATE_NAMES or part.startswith('.env') or part.endswith(('.key', '.pem')) for part in Path(raw).parts):
            raise HTTPException(403, 'Choose a non-secret project file')
        target = self.resolve_path(raw)
        relative = target.relative_to(self.workspace)
        if any(part in PRIVATE_NAMES or part.startswith('.env') for part in relative.parts):
            raise HTTPException(403, 'Private files are not available in the desktop editor')
        return target

    def prepare_review(self, body):
        raw, content = body.get('path'), body.get('content')
        target = self.safe_path(raw)
        if target.exists() and not target.is_file():
            raise HTTPException(400, 'Choose a file path, not a directory')
        if not isinstance(content, str) or len(content.encode()) > 1000000:
            raise HTTPException(413, 'Use a UTF-8 text file up to 1 MB')
        original = target.read_bytes() if target.is_file() else b''
        if len(original) > 1000000:
            raise HTTPException(413, 'Existing file is too large to review')
        try:
            text = original.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise HTTPException(400, 'Only UTF-8 text files can be edited') from exc
        expected = digest(original) if target.exists() else None
        if 'expected_hash' in body and body['expected_hash'] != expected:
            raise HTTPException(409, 'File changed outside this editor. Reload and review again.')
        review = {'path': raw, 'content': content, 'expected_hash': expected,
                  'artifact_id': body.get('artifact_id'), 'created': time.time()}
        review_id = uuid.uuid4().hex
        with self.db() as db:
            db.execute('INSERT INTO reviews VALUES (?,?,?)', (review_id, 'pending', json.dumps(review)))
        difference = ''.join(difflib.unified_diff(text.splitlines(True), content.splitlines(True), fromfile=raw, tofile=raw))
        return {'id': review_id, 'path': raw, 'expected_hash': expected, 'diff': difference[:100000], 'truncated': len(difference) > 100000, 'new_file': not target.exists()}

    def accept_review(self, review_id):
        with file_mutex(self.services.paths.state / 'desktop-writes.lock'), self.db() as db:
            row = db.execute('SELECT * FROM reviews WHERE id=?', (review_id,)).fetchone()
            if not row or row['status'] != 'pending':
                raise HTTPException(409, 'This review is no longer pending')
            review = json.loads(row['data'])
            target = self.safe_path(review['path'])
            current = digest(target.read_bytes()) if target.is_file() else None
            if current != review['expected_hash']:
                raise HTTPException(409, 'File changed since review. Prepare a new diff before saving.')
            mode = target.stat().st_mode & 0o777 if target.exists() else 0o600
            atomic_text(target, review['content'], newline='')
            os.chmod(target, mode)
            db.execute("UPDATE reviews SET status='accepted' WHERE id=?", (review_id,))
            if review.get('artifact_id'):
                artifact = db.execute('SELECT data FROM artifacts WHERE id=?', (review['artifact_id'],)).fetchone()
                if artifact:
                    value = json.loads(artifact['data'])
                    history = value.get('saved_versions', [])
                    history.append({'path': review['path'], 'hash': digest(target.read_bytes()), 'saved_at': time.time()})
                    value.update(saved_path=review['path'], saved_versions=history[-10:], version=len(history))
                    db.execute('UPDATE artifacts SET data=? WHERE id=?', (json.dumps(value), review['artifact_id']))
            return {'path': review['path'], 'hash': digest(target.read_bytes()), 'saved': True}

    def git(self, *arguments):
        try:
            result = subprocess.run(['git', '-C', str(self.workspace), *arguments], capture_output=True, text=True, timeout=30,
                                    env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1'})
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(400, 'Git is unavailable or timed out') from exc
        if result.returncode:
            raise HTTPException(400, result.stderr.strip()[:1000] or 'Git command failed')
        return result.stdout

    def git_status(self):
        try:
            return {'available': True, 'branch': self.git('branch', '--show-current').strip(),
                    'status': self.git('status', '--short'), 'diff': self.git('diff', '--no-ext-diff', '--stat'),
                    'worktrees': self.git('worktree', 'list', '--porcelain')}
        except HTTPException as exc:
            return {'available': False, 'message': exc.detail}

    def create_worktree(self, base):
        if not isinstance(base, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]{0,150}', base):
            raise HTTPException(400, 'Use a commit or branch name')
        commit = self.git('rev-parse', '--verify', '--end-of-options', base + '^{commit}').strip()
        name = uuid.uuid4().hex[:12]
        path = self.services.paths.root / 'desktop-worktrees' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        branch = 'pantheon/' + name
        hooks = self.services.paths.state / 'desktop-empty-hooks'
        hooks.mkdir(parents=True, exist_ok=True)
        self.git('-c', 'core.hooksPath=' + str(hooks), 'worktree', 'add', '-b', branch, str(path), commit)
        return {'path': str(path), 'branch': branch, 'base_commit': commit,
                'note': 'Starts from the selected commit. Uncommitted changes were not copied.'}


def install_routes(app, desktop: DesktopRuntime):
    from fastapi import APIRouter
    router = APIRouter(prefix='/api/desktop')

    @router.get('/identity')
    async def identity(challenge: str = ''):
        return desktop.identity(challenge[:100])

    @router.get('/sessions')
    async def sessions():
        runs = desktop.runs()
        for run in runs:
            if 'result' in run['data']:
                run['data']['result'] = {k: v for k, v in run['data']['result'].items() if k != 'content'}
        return {'sessions': [desktop.public_session(item) for item in desktop.sessions()], 'runs': runs}

    @router.get('/sessions/{session_id}')
    async def session_detail(session_id: str, before: int = -1, limit: int = 80):
        item = desktop.session(session_id)
        if item is None:
            raise HTTPException(404, 'Conversation not found')
        messages = item['messages']
        end = len(messages) if before < 0 else min(before, len(messages))
        start = max(0, end - max(1, min(limit, 100)))
        attachments = []
        for identity in item.get('attachment_draft', []):
            try:
                attachments.append(desktop.services.media.get(identity)[0])
            except ValueError:
                pass
        return {**item, 'messages': messages[start:end], 'message_start': start, 'message_count': len(messages), 'attachments': attachments}

    @router.post('/sessions')
    async def new_session(body: dict):
        return desktop.new_session(body.get('title', 'New task'))

    @router.patch('/sessions/{session_id}')
    async def edit_session(session_id: str, body: dict):
        return desktop.edit_session(session_id, body)

    @router.post('/sessions/{session_id}/runs')
    async def start_run(session_id: str, body: dict):
        return desktop.start_run(session_id, body)

    @router.get('/runs/{run_id}/events')
    async def events(run_id: str, after: int = 0):
        return desktop.events(run_id, max(0, after))

    @router.post('/runs/{run_id}/stop')
    async def stop(run_id: str):
        return desktop.stop(run_id)

    @router.get('/artifacts')
    async def artifacts(query: str = ''):
        return {'artifacts': [{k: v for k, v in item.items() if k != 'content'} for item in desktop.artifacts(query[:200])]}

    @router.get('/artifacts/{artifact_id}')
    async def artifact_detail(artifact_id: str):
        item = next((value for value in desktop.artifacts() if value['id'] == artifact_id), None)
        if not item:
            raise HTTPException(404, 'Artifact not found')
        return item

    @router.post('/attachments')
    async def attachment(body: dict):
        try:
            encoded = body.get('data', '')
            if not isinstance(encoded, str) or len(encoded) > 34000000:
                raise ValueError('Attachment is too large')
            raw = base64.b64decode(encoded, validate=True)
            return desktop.services.media.upload(str(body.get('name', '')), raw)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @router.get('/file')
    async def read_file(path: str):
        target = desktop.safe_path(path)
        if not target.is_file():
            raise HTTPException(404, 'File not found')
        if target.stat().st_size > 1000000:
            raise HTTPException(413, 'File exceeds 1 MB')
        raw = target.read_bytes()
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise HTTPException(400, 'Binary preview is unavailable in this text editor') from exc
        return {'path': path, 'content': content, 'hash': digest(raw), 'modified': target.stat().st_mtime}

    @router.post('/reviews')
    async def prepare_review(body: dict):
        return desktop.prepare_review(body)

    @router.post('/reviews/{review_id}/accept')
    async def accept_review(review_id: str):
        return desktop.accept_review(review_id)

    @router.post('/reviews/{review_id}/reject')
    async def reject_review(review_id: str):
        with desktop.db() as db:
            db.execute("UPDATE reviews SET status='rejected' WHERE id=? AND status='pending'", (review_id,))
        return {'rejected': True}

    @router.get('/git')
    async def git_status():
        return await asyncio.to_thread(desktop.git_status)

    @router.post('/git/worktrees')
    async def worktree(body: dict):
        return await asyncio.to_thread(desktop.create_worktree, body.get('base', 'HEAD'))

    @router.get('/search')
    async def search(query: str = ''):
        query = query[:200].casefold().strip()
        return {'sessions': [desktop.public_session(item) for item in desktop.sessions() if query in (item['title'] + '\n' + '\n'.join(m['text'] for m in item['messages'])).casefold()],
                'artifacts': [{k: v for k, v in item.items() if k != 'content'} for item in desktop.artifacts(query)]}

    app.include_router(router)
