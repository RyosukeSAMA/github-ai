"""Release checks, durable conversations, and provider usage accounting."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pantheon.core.usage import UsageStore
from pantheon.llm.anthropic_client import AnthropicClient
from pantheon.llm.openai_client import OpenAIClient
from pantheon.web import create_app
from pantheon.web.conversations import ConversationStore
from pantheon.web.updates import UpdateChecker


def _session(session_id: str = "chat-1") -> dict:
    return {"id": session_id, "title": "Hello", "mode": "auto", "overrides": {},
            "messages": [{"role": "user", "text": "Hello"}],
            "createdAt": 1000, "updatedAt": 1000}


def test_conversations_persist_and_reject_stale_writes(tmp_path) -> None:
    store = ConversationStore(tmp_path / "conversations.json")
    assert store.get()["sessions"] == []
    first = store.replace([_session()], "")
    assert first is not None
    assert store.replace([_session("chat-2")], "") is None
    assert ConversationStore(store.path).get()["sessions"] == [_session()]
    second = store.replace([_session(), _session("chat-2")], first["revision"])
    assert second is not None
    assert store.path.with_suffix(".json.bak").exists()
    store.path.write_text("broken", encoding="utf-8")
    assert store.get()["sessions"] == [_session()]
    with pytest.raises(ValueError, match="duplicate"):
        store.replace([_session(), _session()], first["revision"])
    assert store.get()["sessions"] == [_session()]


def test_conversation_and_usage_api(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PANTHEON_WORKSPACE", raising=False)
    monkeypatch.delenv("PANTHEON_UI_PASSWORD", raising=False)
    client = TestClient(create_app())
    empty = client.get("/api/conversations").json()
    assert empty["revision"] == ""
    saved = client.put("/api/conversations", json={"schema_version": 1, "expected_revision": "", "sessions": [_session()]})
    assert saved.status_code == 200
    assert client.get("/api/conversations").json()["sessions"] == [_session()]
    assert client.put("/api/conversations", json={"schema_version": 1, "expected_revision": "", "sessions": []}).status_code == 409
    assert client.put("/api/conversations", json={"schema_version": 1, "expected_revision": saved.json()["revision"], "sessions": [{**_session(), "messages": [{"role": "user", "text": 5}]}]}).status_code == 400
    usage = client.get("/api/usage")
    assert usage.status_code == 200
    assert usage.json()["totals"]["calls"] == 0


def test_usage_store_counts_reported_tokens_and_unknown_calls(tmp_path) -> None:
    store = UsageStore(tmp_path / "usage.sqlite")
    response = SimpleNamespace(usage=SimpleNamespace(
        input_tokens=100, output_tokens=30,
        input_tokens_details=SimpleNamespace(cached_tokens=20)))
    store.record("openai", "gpt-6-sol", response, responses_api=True)
    store.record("deepseek", "deepseek-v4-pro", SimpleNamespace(usage=None))
    report = UsageStore(store.path).summary()
    assert report["totals"] == {"calls": 2, "input_tokens": 100,
                                "output_tokens": 30, "cached_input_tokens": 20,
                                "metered_calls": 1}


def test_model_clients_record_usage_after_success(tmp_path) -> None:
    store = UsageStore(tmp_path / "usage.sqlite")
    openai_response = SimpleNamespace(output_text="done", usage=SimpleNamespace(
        input_tokens=12, output_tokens=4))
    openai_sdk = MagicMock()
    openai_sdk.responses.create.return_value = openai_response
    with patch("openai.OpenAI", return_value=openai_sdk):
        client = OpenAIClient(api_key="test")
        client.usage_recorder = store.record
        assert client.complete([{"role": "user", "content": "hi"}], "gpt-6-sol") == "done"

    anthropic_response = SimpleNamespace(content=[SimpleNamespace(text="hello")],
                                         usage=SimpleNamespace(input_tokens=9, output_tokens=3))
    anthropic_sdk = MagicMock()
    anthropic_sdk.messages.create.return_value = anthropic_response
    with patch("anthropic.Anthropic", return_value=anthropic_sdk):
        client = AnthropicClient(api_key="test")
        client.usage_recorder = store.record
        assert client.complete([{"role": "user", "content": "hi"}], "claude-sonnet-4-6") == "hello"

    summary = store.summary()
    assert summary["totals"]["calls"] == 2
    assert summary["totals"]["input_tokens"] == 21
    assert summary["totals"]["output_tokens"] == 7


@pytest.mark.asyncio
async def test_update_checker_uses_latest_release_and_cache(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"tag_name": "v0.2.3", "html_url": "https://github.com/RyosukeSAMA/github-ai/releases/tag/v0.2.3"}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers):
            calls.append(url)
            return FakeResponse()

    monkeypatch.setattr("pantheon.web.updates.httpx.AsyncClient", FakeClient)
    checker = UpdateChecker("0.2.2")
    assert (await checker.check())["update_available"] is True
    assert (await checker.check())["latest_version"] == "v0.2.3"
    assert len(calls) == 1
    assert (await checker.check(force=True))["update_available"] is True
    assert len(calls) == 2
