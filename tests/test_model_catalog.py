from __future__ import annotations

import httpx
import pytest

from pantheon.web.model_catalog import discover_provider_models


@pytest.mark.asyncio
async def test_openai_discovery_keeps_chat_models_and_filters_other_capabilities() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.openai.com/v1/models")
        assert request.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "gpt-6"},
                    {"id": "gpt-5.6"},
                    {"id": "o4-mini"},
                    {"id": "text-embedding-4-large"},
                    {"id": "gpt-image-2"},
                ]
            },
        )

    models = await discover_provider_models(
        "openai",
        "https://api.openai.com/v1",
        "sk-test",
        transport=httpx.MockTransport(handler),
    )

    assert [item["id"] for item in models] == ["gpt-6", "gpt-5.6", "o4-mini"]


@pytest.mark.asyncio
async def test_anthropic_discovery_uses_display_names() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["limit"] == "100"
        assert request.headers["x-api-key"] == "sk-ant-test"
        assert request.headers["anthropic-version"] == "2023-06-01"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "claude-sonnet-next", "display_name": "Claude Sonnet Next"},
                ]
            },
        )

    models = await discover_provider_models(
        "anthropic",
        "https://api.anthropic.com",
        "sk-ant-test",
        transport=httpx.MockTransport(handler),
    )

    assert models == [{"id": "claude-sonnet-next", "label": "Claude Sonnet Next"}]


@pytest.mark.asyncio
async def test_anthropic_compatible_gateway_uses_bearer_authentication() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.kie.ai/claude/v1/models?limit=100")
        assert request.headers["authorization"] == "Bearer sk-kie-test"
        assert request.headers["anthropic-version"] == "2023-06-01"
        return httpx.Response(
            200,
            json={"data": [{"id": "claude-opus-5", "display_name": "Claude Opus 5"}]},
        )

    models = await discover_provider_models(
        "anthropic",
        "https://api.kie.ai/claude",
        "Bearer sk-kie-test",
        transport=httpx.MockTransport(handler),
    )

    assert models == [{"id": "claude-opus-5", "label": "Claude Opus 5"}]


@pytest.mark.asyncio
async def test_ollama_discovery_uses_local_tags_endpoint() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("http://localhost:11434/api/tags")
        return httpx.Response(
            200,
            json={"models": [{"name": "qwen3:8b"}, {"name": "nomic-embed-text"}]},
        )

    models = await discover_provider_models(
        "ollama",
        "http://localhost:11434/v1",
        transport=httpx.MockTransport(handler),
    )

    assert models == [{"id": "qwen3:8b", "label": "qwen3:8b"}]
