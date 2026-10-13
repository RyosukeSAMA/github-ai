import base64
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pantheon.core.base import Task, TaskResult
from pantheon.core.budgets import TASK_ID, BudgetExceededError
from pantheon.core.hermes import Hermes
from pantheon.core.paths import DataPaths
from pantheon.core.services import WorkspaceServices
from pantheon.web import create_app

PNG = b'\x89PNG\r\n\x1a\n' + b'fixture'
PDF = b'%PDF-1.7\nfixture'
WAV = b'RIFF' + b'\x00' * 4 + b'WAVE' + b'fixture'


def service(tmp_path):
    return WorkspaceServices(DataPaths.for_workspace(tmp_path)).media


def test_private_files_validate_type_size_ids_and_workspace(tmp_path):
    media = service(tmp_path)
    artifact = media.upload('test.png', PNG)
    meta, path = media.get(artifact['id'])
    assert path.read_bytes() == PNG
    assert meta['type'] == 'image/png'
    if __import__('os').name != 'nt':
        assert path.stat().st_mode & 0o777 == 0o600
    for name, data in [('test.png', PDF), ('test.html', b'<script>'), ('test.pdf', b'x' * (8 * 1024 * 1024 + 1))]:
        with pytest.raises(ValueError):
            media.upload(name, data)
    with pytest.raises(ValueError):
        media.get('../../.env')
    with pytest.raises(ValueError):
        service(tmp_path / 'other').get(artifact['id'])
    with pytest.raises(ValueError):
        media.validate_attachments([artifact['id']] * 2)
    audio = media.upload('sample.wav', WAV)
    with pytest.raises(ValueError, match='Chat attachments'):
        media.validate_attachments([audio['id']])


def test_provider_payloads_and_media_budget(tmp_path, monkeypatch):
    media = service(tmp_path)
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text='visible evidence', content=[SimpleNamespace(text='visible evidence')], usage=SimpleNamespace(input_tokens=20, output_tokens=5))
    client = SimpleNamespace(responses=SimpleNamespace(create=create), messages=SimpleNamespace(create=create))
    monkeypatch.setattr(media, 'connection', lambda provider: client)
    image = media.upload('sample.png', PNG)
    pdf = media.upload('sample.pdf', PDF)
    task = Task('summarize', attachments=[image['id'], pdf['id']])
    media.services.budget.save_policy({'task_usd': 1, 'operation_prices': {'openai/gpt-6-astra': .1, 'anthropic/claude-opus-5-5': .2}})
    token = TASK_ID.set(task.task_id)
    try:
        assert 'visible evidence' in media.understand(task)
    finally:
        TASK_ID.reset(token)
    blocks = calls[0]['input'][0]['content']
    assert blocks[0]['image_url'].startswith('data:image/png;base64,')
    assert blocks[1]['file_data'].startswith('data:application/pdf;base64,')
    media.save_settings({'vision_provider': 'anthropic', 'vision_model': 'claude-opus-5-5'})
    media.understand(task)
    blocks = calls[1]['messages'][0]['content']
    assert [block['type'] for block in blocks] == ['image', 'document', 'text']
    assert blocks[1]['source']['media_type'] == 'application/pdf'
    assert media.services.budget.summary()['last_24_hours']['estimated_usd'] == pytest.approx(.3)
    media.services.budget.save_policy({'daily_requests': 2})
    with pytest.raises(BudgetExceededError):
        media.understand(task)
    assert len(calls) == 2


def test_generation_transcription_outputs_and_no_foreign_provider_key(tmp_path, monkeypatch):
    media = service(tmp_path)
    # DeepSeek uses the OpenAI adapter, but its key must never become the OpenAI media key.
    media.connection_provider = lambda: {'llm_providers': {'openai': {'provider_id': 'deepseek', 'api_key': 'deepseek-test'}}}
    assert not media.status()['configured']['openai']
    with pytest.raises(ValueError, match='Openai API key'):
        media.connection('openai')
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(PNG).decode())])
    def transcribe(**kwargs):
        assert kwargs['file'][1].read() == WAV
        return SimpleNamespace(text='a useful transcript')
    client = SimpleNamespace(images=SimpleNamespace(generate=generate), audio=SimpleNamespace(transcriptions=SimpleNamespace(create=transcribe)))
    monkeypatch.setattr(media, 'connection', lambda _: client)
    output = media.generate_image('a temple')
    assert media.get(output['id'])[1].read_bytes() == PNG
    transcript = media.transcribe(media.upload('voice.wav', WAV)['id'])
    assert transcript['text'] == 'a useful transcript'
    assert media.get(transcript['artifact']['id'])[1].read_text() == transcript['text']
    assert calls[0]['model'] == 'gpt-image-2.5-flare'
    media.services.budget.save_policy({'daily_usd': 1})
    with pytest.raises(BudgetExceededError, match='No price'):
        media.generate_image('a temple')
    assert len(calls) == 1


def test_understanding_checkpoint_avoids_second_vision_request(tmp_path):
    media = service(tmp_path)
    calls = []
    class Agent:
        name = 'athena'
        description = 'research'
        config = {}
        def run(self, task, context=None):
            assert '<attachment_data>' in task.content
            return TaskResult('athena', 'provider failure', success=False)
    hermes = Hermes({'athena': Agent()}, SimpleNamespace())
    hermes.task_store = media.services.tasks
    def understand(task):
        calls.append(task.task_id)
        return '<attachment_data>evidence</attachment_data>'
    hermes.attachment_processor = understand
    original = Task('summarize', mode='role:athena', attachments=['fake'])
    hermes.dispatch(original)
    checkpoint = hermes.task_store.get(original.task_id)['data']['checkpoint']
    assert checkpoint['task']['content'] == 'summarize'
    assert checkpoint['task']['attachments'] == ['fake']
    hermes.dispatch(Task('summarize', mode='role:athena', attachments=['fake']), resume_checkpoint=checkpoint)
    assert calls == [original.task_id]


def test_media_web_upload_and_auth_without_paid_requests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())
    upload = client.post('/api/media/upload?filename=sample.pdf', content=PDF)
    assert upload.status_code == 200
    identity = upload.json()['id']
    response = client.get(f'/api/media/{identity}/file')
    assert response.content == PDF
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert client.post('/api/media/upload?filename=sample.png', content=PDF).status_code == 400
    assert client.post('/api/media/settings', json={'vision_provider': 'deepseek'}).status_code == 400
    assert client.post('/api/media/generate', json={'prompt': 'temple'}).status_code == 400
    assert client.get('/api/budgets').json()['last_24_hours']['requests'] == 0
    (tmp_path / '.env').write_text('PANTHEON_UI_AUTH_ENABLED=1\nPANTHEON_UI_PASSWORD=secret\n')
    for url in ['/api/media', f'/api/media/{identity}/file']:
        assert client.get(url).status_code == 401
    assert client.post('/api/media/upload?filename=sample.pdf', content=PDF).status_code == 401
    assert client.post('/api/media/generate', json={'prompt': 'temple'}).status_code == 401
    assert client.post('/api/media/transcribe', json={'id': identity}).status_code == 401


def test_apollo_native_image_is_real_artifact_and_checkpoints_side_effect(tmp_path):
    media = service(tmp_path)
    class Agent:
        name = 'apollo'
        config = {}
        def run(self, task, context=None):
            return TaskResult('apollo', '<media_call>{"prompt":"a temple"}</media_call>')
    hermes = Hermes({'apollo': Agent()}, SimpleNamespace())
    hermes.task_store = media.services.tasks
    calls = []
    def generate(prompt, size):
        calls.append(prompt)
        return {'id': 'a' * 32, 'name': 'image.png'}
    hermes.image_generator = generate
    task = Task('Generate an image of a temple', mode='role:apollo')
    result = hermes.dispatch(task)
    assert calls == ['a temple']
    assert '/api/media/' in result['content']
    assert result['steps'][0].metadata['media'][0]['id'] == 'a' * 32
    checkpoint = hermes.task_store.get(task.task_id)['data']['checkpoint']
    assert checkpoint['effects']['1'][0]['kind'] == 'image_generation'
