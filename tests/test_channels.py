import hashlib
import hmac
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from pantheon.core.channels import ChannelAuthError, SecretURLFilter
from pantheon.core.paths import DataPaths
from pantheon.core.services import WorkspaceServices
from pantheon.web import create_app


def setup(tmp_path):
    return WorkspaceServices(DataPaths.for_workspace(tmp_path)).channels


def telegram(store, *, reply=False):
    return store.save('telegram', {'enabled': True, 'auto_reply': reply, 'users': ['11'], 'channels': ['22']},
                      {'bot_token': '123:bot-secret', 'secret_token': 'callback-secret'})


def telegram_body(identity=1, user=11, chat=22):
    return json.dumps({'update_id': identity, 'message': {'text': 'Research this', 'message_id': 8,
                        'from': {'id': user, 'is_bot': False}, 'chat': {'id': chat}}}).encode()


def slack_headers(body, timestamp=None):
    timestamp = str(timestamp or int(time.time()))
    signature = 'v0=' + hmac.new(b'slack-secret', b'v0:' + timestamp.encode() + b':' + body, hashlib.sha256).hexdigest()
    return {'x-slack-request-timestamp': timestamp, 'x-slack-signature': signature}


def test_activation_allowlists_and_concurrent_deduplication(tmp_path, monkeypatch):
    store = setup(tmp_path)
    with pytest.raises(ValueError, match='allowlists'):
        store.save('telegram', {'enabled': True})
    with pytest.raises(ValueError, match='Configure'):
        store.save('telegram', {'enabled': True, 'users': ['11'], 'channels': ['22']})
    telegram(store, reply=True)
    headers = {'x-telegram-bot-api-secret-token': 'callback-secret'}
    for invalid in [{}, {'x-telegram-bot-api-secret-token': 'wrong'}]:
        with pytest.raises(ChannelAuthError, match='signature'):
            store.receive('telegram', invalid, telegram_body())
    with pytest.raises(ChannelAuthError, match='allowlist'):
        store.receive('telegram', headers, telegram_body(user=99))
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.receive('telegram', headers, telegram_body()), range(16)))
    assert all(result['ok'] for result in results)
    assert len(store.history()) == 1
    calls, replies = [], []
    monkeypatch.setattr(store, 'send', lambda *args: replies.append(args))
    def execute(task, mode):
        calls.append(task)
        return {'content': 'answer', 'task_id': 'saved-task'}
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(lambda _: store.process_next(execute), range(4))) == 1
    assert calls == ['Research this']
    assert len(replies) == 1
    assert store.history()[0]['state'] == 'delivered'
    assert store.history()[0]['task_id'] == 'saved-task'
    assert 'bot-secret' not in json.dumps(store.status('telegram'))


def test_slack_fresh_signature_challenge_mention_and_team(tmp_path):
    store = setup(tmp_path)
    store.save('slack', {'enabled': True, 'users': ['U11'], 'channels': ['C22'], 'account_id': 'T33'},
               {'bot_token': 'xoxb-test', 'signing_secret': 'slack-secret'})
    body = json.dumps({'type': 'url_verification', 'challenge': 'challenge'}).encode()
    assert store.receive('slack', slack_headers(body), body) == {'challenge': 'challenge'}
    with pytest.raises(ChannelAuthError):
        store.receive('slack', slack_headers(body, int(time.time()) - 600), body)
    with pytest.raises(ChannelAuthError):
        store.receive('slack', slack_headers(body), body + b' ')
    payload = {'type': 'event_callback', 'team_id': 'T33', 'event_id': 'Ev1',
               'event': {'type': 'app_mention', 'user': 'U11', 'channel': 'C22', 'text': '<@B44> Research this', 'ts': '1.2'}}
    body = json.dumps(payload).encode()
    assert store.receive('slack', slack_headers(body), body)['ok']
    payload['team_id'] = 'OTHER'
    body = json.dumps(payload).encode()
    with pytest.raises(ChannelAuthError, match='team'):
        store.receive('slack', slack_headers(body), body)
    assert len(store.history()) == 1


def test_discord_ed25519_defer_and_application_allowlist(tmp_path, monkeypatch):
    store = setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes_raw().hex()
    store.save('discord', {'enabled': True, 'auto_reply': True, 'users': ['11'], 'channels': ['22'], 'account_id': '33', 'public_key': public_key})
    def send(payload, valid=True):
        body = json.dumps(payload).encode()
        timestamp = str(int(time.time()))
        headers = {'x-signature-timestamp': timestamp, 'x-signature-ed25519': key.sign(timestamp.encode() + body).hex() if valid else '00' * 64}
        return store.receive('discord', headers, body)
    assert send({'type': 1}) == {'type': 1}
    with pytest.raises(ChannelAuthError):
        send({'type': 1}, valid=False)
    payload = {'type': 2, 'id': '44', 'application_id': '33', 'channel_id': '22', 'token': 'interaction-secret',
               'member': {'user': {'id': '11'}}, 'data': {'name': 'pantheon', 'options': [{'name': 'task', 'value': 'Explain this'}]}}
    assert send(payload) == {'type': 5, 'data': {'flags': 64}}
    payload['application_id'] = 'wrong'
    with pytest.raises(ChannelAuthError):
        send(payload)
    replies = []
    monkeypatch.setattr(store, 'send', lambda *args: replies.append(args))
    assert store.process_next(lambda *args: {'content': 'answer', 'task_id': 'task'})
    assert len(replies) == 1
    with store.connect() as db:
        data = db.execute('SELECT data FROM events').fetchone()['data']
    assert 'interaction-secret' not in data


def test_reply_timeout_is_not_repeated_and_disabled_queue_is_cancelled(tmp_path, monkeypatch):
    store = setup(tmp_path)
    telegram(store, reply=True)
    headers = {'x-telegram-bot-api-secret-token': 'callback-secret'}
    store.receive('telegram', headers, telegram_body())
    calls = []
    def timeout(*args):
        calls.append(args)
        raise TimeoutError('delivery may have succeeded')
    monkeypatch.setattr(store, 'send', timeout)
    def execute(*args):
        return {'content': 'answer', 'task_id': 'task'}
    store.process_next(execute)
    store.receive('telegram', headers, telegram_body())
    assert not store.process_next(execute)
    assert len(calls) == 1
    assert store.history()[0]['state'] == 'reply_failed'
    store.receive('telegram', headers, telegram_body(identity=2))
    store.save('telegram', {'enabled': False})
    assert store.process_next(lambda *args: pytest.fail('Disabled platform must not execute'))
    assert store.history()[0]['state'] == 'cancelled'


def test_replies_have_fixed_destinations_no_mentions_and_redacted_logs(tmp_path, monkeypatch):
    store = setup(tmp_path)
    telegram(store)
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'ok': True})
    real_client = httpx.Client
    monkeypatch.setattr('pantheon.core.channels.httpx.Client', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    store.send('telegram', {'chat_id': '22', 'message_id': 1}, 'answer')
    store.services.credentials.save('PANTHEON_SLACK_BOT_TOKEN', 'slack-test')
    store.send('slack', {'channel': 'C22', 'thread_ts': '1.2'}, '<!everyone> answer')
    store.send('discord', {'application_id': '33', 'token': 'interaction-secret'}, '@everyone answer')
    assert [request.url.host for request in requests] == ['api.telegram.org', 'slack.com', 'discord.com']
    assert json.loads(requests[1].content)['mrkdwn'] is False
    assert json.loads(requests[2].content)['allowed_mentions'] == {'parse': []}
    record = logging.LogRecord('httpx', logging.INFO, '', 1, 'HTTP %s %s',
                               ('https://api.telegram.org/bot123:bot-secret/sendMessage', 'https://discord.com/api/v10/webhooks/33/interaction-secret/messages/@original'), None)
    SecretURLFilter().filter(record)
    assert 'bot-secret' not in record.getMessage()
    assert 'interaction-secret' not in record.getMessage()


def test_web_callbacks_bypass_ui_login_but_configs_remain_protected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = setup(tmp_path)
    telegram(store)
    (tmp_path / '.env').write_text((tmp_path / '.env').read_text() + 'PANTHEON_UI_AUTH_ENABLED=1\nPANTHEON_UI_PASSWORD=secret\n')
    client = TestClient(create_app())
    assert client.get('/api/channels').status_code == 401
    assert client.post('/api/channels/telegram/config', json={}).status_code == 401
    assert client.post('/api/channels/telegram/callback', content=telegram_body()).status_code == 401
    assert client.post('/api/channels/telegram/callback', headers={'x-telegram-bot-api-secret-token': 'callback-secret'}, content=telegram_body()).status_code == 200
    assert len(store.history()) == 1


def test_lifespan_worker_runs_queued_tasks_without_replies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = setup(tmp_path)
    telegram(store)
    store.receive('telegram', {'x-telegram-bot-api-secret-token': 'callback-secret'}, telegram_body())
    calls = []
    class FakePantheon:
        def __init__(self, **kwargs):
            self.config = {}
            self.hermes = SimpleNamespace(cancel_event=None)
        def get_role(self, name):
            return None
        def ask(self, content, mode, on_event):
            calls.append(content)
            return {'content': 'queued result', 'task_id': 'saved'}
    monkeypatch.setattr('pantheon.web.app.Pantheon', FakePantheon)
    with TestClient(create_app()):
        deadline = time.monotonic() + 3
        while not calls and time.monotonic() < deadline:
            time.sleep(.01)
        assert calls == ['Research this']
    assert store.history()[0]['state'] == 'processed'
