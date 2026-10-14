"""Verified chat callbacks, durable deduplication, and controlled bot replies."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import time
from contextlib import contextmanager

import httpx

CHANNELS = ('telegram', 'slack', 'discord')
SECRETS = {'telegram': {'bot_token': 'PANTHEON_TELEGRAM_BOT_TOKEN', 'secret_token': 'PANTHEON_TELEGRAM_SECRET_TOKEN'},
           'slack': {'bot_token': 'PANTHEON_SLACK_BOT_TOKEN', 'signing_secret': 'PANTHEON_SLACK_SIGNING_SECRET'},
           'discord': {}}
DEFAULTS = {'enabled': False, 'auto_reply': False, 'users': [], 'channels': [], 'account_id': '', 'public_key': '', 'mode': 'auto'}


class SecretURLFilter(logging.Filter):
    def filter(self, record):
        text = record.getMessage()
        text = re.sub(r'(https://api\.telegram\.org/bot)[^/\s"\']+', r'\1[redacted]', text)
        text = re.sub(r'(https://discord\.com/api/v10/webhooks/[^/\s]+/)[^/\s"\']+', r'\1[redacted]', text)
        record.msg, record.args = text, ()
        return True


logging.getLogger('httpx').addFilter(SecretURLFilter())


class ChannelAuthError(ValueError):
    pass


class ChannelQueueFullError(ValueError):
    pass


class ChannelStore:
    def __init__(self, services):
        self.services = services
        self.path = services.paths.state / 'channels.sqlite'

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        os.chmod(self.path, 0o600)
        db.row_factory = sqlite3.Row
        try:
            db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, channel TEXT, created REAL, updated REAL, state TEXT, data TEXT, result TEXT, task_id TEXT, owner INTEGER)')
            db.commit()
            with db:
                yield db
        finally:
            db.close()

    def config(self, channel):
        if channel not in CHANNELS:
            raise ValueError('Unknown chat platform')
        return {**DEFAULTS, **self.services.readiness.preference('channel:' + channel, {})}

    def save(self, channel: str, value: dict, secrets: dict | None = None, *, storage='env'):
        cfg = {**self.config(channel), **value}
        if set(cfg) != set(DEFAULTS):
            raise ValueError('Unknown channel configuration')
        if type(cfg['enabled']) is not bool or type(cfg['auto_reply']) is not bool:
            raise ValueError('enabled and auto_reply must be boolean')
        for key in ('users', 'channels'):
            if not isinstance(cfg[key], list) or len(cfg[key]) > 100 or any(not isinstance(item, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', item) for item in cfg[key]):
                raise ValueError('Provide an explicit list of user and channel IDs')
        if not isinstance(cfg['account_id'], str) or cfg['account_id'] and not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', cfg['account_id']):
            raise ValueError('Provide a valid team/application ID')
        if cfg['mode'] not in {'auto', 'multi', 'role:athena', 'role:hephaestus', 'role:apollo'}:
            raise ValueError('Use auto, multi or a supported specialist mode')
        if channel == 'discord' and (cfg['public_key'] or cfg['enabled']) and not re.fullmatch('[a-fA-F0-9]{64}', str(cfg['public_key'])):
            raise ValueError('Discord needs the application Ed25519 public key (64 hex characters)')
        if cfg['enabled'] and (not cfg['users'] or not cfg['channels'] or channel in {'slack', 'discord'} and not cfg['account_id']):
            raise ValueError('Enabling requires user/channel allowlists and the Slack team or Discord application ID')
        for key, raw in (secrets or {}).items():
            if key not in SECRETS[channel] or not isinstance(raw, str):
                raise ValueError('Unknown channel credential')
            if raw:
                if channel == 'telegram' and key == 'secret_token' and not re.fullmatch('[A-Za-z0-9_-]{1,256}', raw):
                    raise ValueError('Telegram callback secret uses letters, numbers, underscores and hyphens')
                self.services.credentials.save(SECRETS[channel][key], raw, storage=storage)
        required = SECRETS[channel] if cfg['enabled'] else {}
        if any(not self.services.env_value(name) for name in required.values()):
            raise ValueError('Configure the bot token and callback signing secret before enabling')
        self.services.readiness.set_preference('channel:' + channel, cfg)
        return self.status(channel)

    def status(self, channel):
        cfg = self.config(channel)
        credentials = {key: bool(self.services.env_value(name)) for key, name in SECRETS[channel].items()}
        with self.connect() as db:
            last = db.execute('SELECT created, state, task_id FROM events WHERE channel=? ORDER BY created DESC LIMIT 1', (channel,)).fetchone()
        return {'id': channel, 'name': channel.title(), **cfg, 'credentials': credentials,
                'endpoint': f'/api/channels/{channel}/callback', 'last_event': dict(last) if last else None,
                'state': 'receiving' if cfg['enabled'] and last else ('configured' if cfg['enabled'] else 'not_connected')}

    def history(self):
        with self.connect() as db:
            rows = db.execute('SELECT id, channel, created, updated, state, task_id FROM events ORDER BY created DESC LIMIT 30').fetchall()
        return [dict(row) for row in rows]

    def verify(self, channel, headers, body: bytes):
        cfg = self.config(channel)
        if not cfg['enabled']:
            raise ChannelAuthError('Chat platform is disabled')
        if channel == 'telegram':
            expected = self.services.env_value(SECRETS[channel]['secret_token'])
            supplied = headers.get('x-telegram-bot-api-secret-token', '')
            valid = bool(expected and supplied and hmac.compare_digest(expected, supplied))
        else:
            timestamp = headers.get('x-slack-request-timestamp' if channel == 'slack' else 'x-signature-timestamp', '')
            try:
                fresh = abs(time.time() - int(timestamp)) <= 300
            except (ValueError, TypeError):
                fresh = False
            valid = False
            if fresh and channel == 'slack':
                secret = self.services.env_value(SECRETS['slack']['signing_secret'])
                digest = 'v0=' + hmac.new(secret.encode(), b'v0:' + timestamp.encode() + b':' + body, hashlib.sha256).hexdigest()
                valid = bool(secret and hmac.compare_digest(digest, headers.get('x-slack-signature', '')))
            elif fresh:
                from cryptography.exceptions import InvalidSignature
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                try:
                    Ed25519PublicKey.from_public_bytes(bytes.fromhex(cfg['public_key'])).verify(
                        bytes.fromhex(headers.get('x-signature-ed25519', '')), timestamp.encode() + body)
                    valid = True
                except (ValueError, InvalidSignature):
                    pass
        if not valid:
            raise ChannelAuthError('Invalid or expired platform callback signature')
        return cfg

    def receive(self, channel: str, headers, body: bytes):
        cfg = self.verify(channel, headers, body)
        try:
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError()
        except ValueError as exc:
            raise ValueError('JSON object required') from exc
        if channel == 'slack' and payload.get('type') == 'url_verification':
            challenge = payload.get('challenge')
            if not isinstance(challenge, str) or len(challenge) > 500:
                raise ValueError('Invalid Slack challenge')
            return {'challenge': challenge}
        if channel == 'discord' and payload.get('type') == 1:
            return {'type': 1}
        reply = {'ok': True}
        if channel == 'telegram':
            message = payload.get('message') or {}
            user = message.get('from') or {}
            if user.get('is_bot') or not message.get('text'):
                return reply
            user_id, channel_id = str(user.get('id') or ''), str((message.get('chat') or {}).get('id') or '')
            event_id = str(payload.get('update_id', ''))
            text = message['text']
            route = {'chat_id': channel_id, 'message_id': message.get('message_id')}
        elif channel == 'slack':
            event = payload.get('event') or {}
            if payload.get('type') != 'event_callback' or event.get('type') != 'app_mention' or event.get('bot_id') or event.get('subtype'):
                return reply
            if str(payload.get('team_id') or '') != cfg['account_id']:
                raise ChannelAuthError('Slack team is not allowed')
            user_id, channel_id = str(event.get('user') or ''), str(event.get('channel') or '')
            event_id = str(payload.get('event_id') or '')
            text = re.sub(r'<@[A-Z0-9]+>', '', str(event.get('text') or '')).strip()
            route = {'channel': channel_id, 'thread_ts': event.get('thread_ts') or event.get('ts')}
        else:
            if payload.get('type') != 2 or (payload.get('data') or {}).get('name') != 'pantheon':
                return {'type': 4, 'data': {'content': 'Use /pantheon task:<request>.', 'flags': 64, 'allowed_mentions': {'parse': []}}}
            if str(payload.get('application_id') or '') != cfg['account_id']:
                raise ChannelAuthError('Discord application is not allowed')
            user = (payload.get('member') or {}).get('user') or payload.get('user') or {}
            if user.get('bot'):
                raise ChannelAuthError('Bot users are not allowed')
            user_id, channel_id = str(user.get('id') or ''), str(payload.get('channel_id') or '')
            event_id = str(payload.get('id') or '')
            options = (payload.get('data') or {}).get('options') or []
            text = next((option.get('value', '') for option in options if option.get('name') == 'task'), '')
            token = str(payload.get('token') or '')
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,400}', token):
                raise ValueError('Invalid Discord interaction token')
            route = {'application_id': cfg['account_id'], 'token': token}
            reply = {'type': 5, 'data': {'flags': 64}} if cfg['auto_reply'] else {'type': 4, 'data': {'content': 'Task accepted. Replies are disabled; see Pantheon task history.', 'flags': 64, 'allowed_mentions': {'parse': []}}}
        if user_id not in cfg['users'] or channel_id not in cfg['channels']:
            raise ChannelAuthError('User or channel is not in the allowlist')
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}', event_id) or not isinstance(text, str) or not text.strip() or len(text) > 12000:
            raise ValueError('Provide a non-empty task up to 12,000 characters and a valid event ID')
        identity = channel + ':' + event_id
        data = {'task': text.strip(), 'mode': cfg['mode'], 'user': user_id, 'destination': channel_id, 'route': route, 'auto_reply': cfg['auto_reply'], 'account_id': cfg['account_id']}
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM events WHERE id=?', (identity,)).fetchone():
                return reply  # ACK the duplicate; never execute or send it again.
            if db.execute('SELECT COUNT(*) FROM events WHERE state IN ("queued", "running")').fetchone()[0] >= 100:
                raise ChannelQueueFullError('Chat queue is full; retry later')
            if db.execute('SELECT COUNT(*) FROM events WHERE channel=? AND created>? AND json_extract(data, "$.user")=?',
                          (channel, now - 60, user_id)).fetchone()[0] >= 10:
                raise ChannelQueueFullError('User request rate limit reached; retry later')
            db.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (identity, channel, now, now, 'queued', json.dumps(data), '', '', 0))
        return reply

    def _claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM events WHERE state="queued" ORDER BY created LIMIT 1').fetchone()
            if row:
                db.execute('UPDATE events SET state="running", owner=?, updated=? WHERE id=?', (os.getpid(), time.time(), row['id']))
                return dict(row)
        return None

    def _finish(self, identity, state, *, result='', task_id=''):
        with self.connect() as db:
            db.execute('UPDATE events SET state=?, result=?, task_id=?, updated=?, data=json_remove(data, "$.route.token") WHERE id=?',
                       (state, result[:200000], task_id, time.time(), identity))

    def recover_interrupted(self):
        # The Web runtime lease guarantees no other channel worker is active for this workspace.
        with self.connect() as db:
            db.execute('UPDATE events SET state="interrupted", updated=?, data=json_remove(data, "$.route.token") WHERE state="running"', (time.time(),))
            db.execute('DELETE FROM events WHERE updated<? AND state NOT IN ("queued", "running")', (time.time() - 30 * 86400,))

    def process_next(self, execute):
        event = self._claim()
        if not event:
            return False
        data = json.loads(event['data'])
        channel = event['channel']
        cfg = self.config(channel)
        if not cfg['enabled'] or data['user'] not in cfg['users'] or data['destination'] not in cfg['channels']:
            self._finish(event['id'], 'cancelled')
            return True
        if channel == 'discord' and time.time() - event['created'] > 14 * 60:
            self._finish(event['id'], 'expired')
            return True
        try:
            result = execute(data['task'], data['mode'])
        except Exception:
            self._finish(event['id'], 'failed', result='Task failed. Check Pantheon task history and model configuration.')
            return True
        content, task_id = str(result.get('content') or ''), str(result.get('task_id') or '')
        current = self.config(channel)
        allowed = (current['enabled'] and data['user'] in current['users'] and data['destination'] in current['channels']
                   and (channel == 'telegram' or current['account_id'] == data.get('account_id')))
        if not data['auto_reply'] or not current['auto_reply'] or not allowed:
            self._finish(event['id'], 'processed', result=content, task_id=task_id)
            return True
        try:
            self.send(channel, data['route'], content or 'No answer was returned. Check Pantheon task history.')
        except Exception:
            # Delivery may have succeeded before a timeout; never automatically repeat it.
            self._finish(event['id'], 'reply_failed', result=content, task_id=task_id)
        else:
            self._finish(event['id'], 'delivered', result=content, task_id=task_id)
        return True

    def send(self, channel, route, content):
        maximum = 1900 if channel == 'discord' else 3900
        text = content[:maximum] + ('\n… Full result is available in Pantheon task history.' if len(content) > maximum else '')
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            if channel == 'telegram':
                token = self.services.env_value(SECRETS[channel]['bot_token'])
                response = client.post(f'https://api.telegram.org/bot{token}/sendMessage', json={
                    'chat_id': route['chat_id'], 'text': text, 'link_preview_options': {'is_disabled': True},
                    'reply_parameters': {'message_id': route['message_id'], 'allow_sending_without_reply': True}})
            elif channel == 'slack':
                token = self.services.env_value(SECRETS[channel]['bot_token'])
                response = client.post('https://slack.com/api/chat.postMessage', headers={'Authorization': 'Bearer ' + token},
                                       json={**route, 'text': text, 'mrkdwn': False, 'parse': 'none', 'unfurl_links': False, 'unfurl_media': False})
            else:
                response = client.patch(f'https://discord.com/api/v10/webhooks/{route["application_id"]}/{route["token"]}/messages/@original',
                                        json={'content': text, 'allowed_mentions': {'parse': []}})
            response.raise_for_status()
            if channel in {'telegram', 'slack'} and not response.json().get('ok'):
                raise ValueError('The platform rejected the bot reply')
