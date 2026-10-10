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
                    {"id": "gpt-6-astra"},
                    {"id": "gpt-6-sol"},
                    {"id": "gpt-6-luna"},
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

    assert [item["id"] for item in models] == [
        "gpt-6-astra",
        "gpt-6-sol",
        "gpt-6-luna",
        "gpt-6",
        "gpt-5.6",
        "o4-mini",
    ]


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
                    {"id": "claude-opus-5-5", "display_name": "Claude Opus 5.5"},
                ]
            },
        )

    models = await discover_provider_models(
        "anthropic",
        "https://api.anthropic.com",
        "sk-ant-test",
        transport=httpx.MockTransport(handler),
    )

    assert models == [{"id": "claude-opus-5-5", "label": "Claude Opus 5.5"}]


@pytest.mark.asyncio
async def test_deepseek_discovery_accepts_latest_flash_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.deepseek.com/models")
        return httpx.Response(200, json={"data": [{"id": "deepseek-flash"}]})

    models = await discover_provider_models(
        "deepseek",
        "https://api.deepseek.com",
        "sk-test",
        transport=httpx.MockTransport(handler),
    )

    assert models == [{"id": "deepseek-flash", "label": "deepseek-flash"}]


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


@pytest.mark.asyncio
async def test_anthropic_paginates_and_excludes_retired_models():
    requests = []
    async def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json={'data': [
                {'id': 'claude-opus-5-5'}, {'id': 'claude-old-3', 'lifecycle': 'retired'}
            ], 'has_more': True, 'last_id': 'page-one'})
        assert request.url.params['after_id'] == 'page-one'
        return httpx.Response(200, json={'data': [
            {'id': 'claude-opus-5-5'}, {'id': 'claude-sonnet-5-5'}, {'id': 'claude-haiku-5-5'}
        ], 'has_more': False})
    models = await discover_provider_models('anthropic', 'https://api.anthropic.com', 'test', transport=httpx.MockTransport(handler))
    assert [item['id'] for item in models] == ['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5']
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_discovery_does_not_accept_partial_catalog_after_pagination_error():
    from pantheon.web.model_catalog import ModelDiscoveryError
    async def handler(request):
        return httpx.Response(200, json={'data': [{'id': 'claude-sonnet-5-5'}], 'has_more': True, 'last_id': 'same'})
    with pytest.raises(ModelDiscoveryError, match='cursor'):
        await discover_provider_models('anthropic', 'https://api.anthropic.com', 'test', transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_openai_includes_new_model_and_excludes_shutdown_model():
    async def handler(request):
        return httpx.Response(200, json={'data': [
            {'id': 'gpt-6.1-sol'}, {'id': 'gpt-old', 'shutdown_date': '2000-01-01'},
            {'id': 'gpt-image-2.5-sunburst'}
        ]})
    models = await discover_provider_models('openai', 'https://api.openai.com/v1', 'test', transport=httpx.MockTransport(handler))
    assert [item['id'] for item in models] == ['gpt-6.1-sol']


@pytest.mark.asyncio
@pytest.mark.parametrize('provider,document,expected', [
    ('openai', '# Models\n## Featured models\n- [GPT-6.1 Sol](/api/docs/models/gpt-6.1-sol.md)\n## Browse our full catalog\n- [old](/api/docs/models/gpt-old.md)', 'gpt-6.1-sol'),
    ('anthropic', '| Claude API ID | `claude-haiku-5-5` |\n[guide](claude-on-vertex-ai)', 'claude-haiku-5-5'),
])
async def test_public_document_parser_ignores_navigation_and_uses_no_credentials(provider, document, expected):
    from pantheon.web.model_catalog import discover_documented_models
    async def handler(request):
        assert 'authorization' not in request.headers and 'x-api-key' not in request.headers
        return httpx.Response(200, text=document)
    models = await discover_documented_models(provider, transport=httpx.MockTransport(handler))
    assert [item['id'] for item in models] == [expected]


@pytest.mark.asyncio
async def test_public_document_format_change_is_reported_instead_of_returning_empty_catalog():
    from pantheon.web.model_catalog import ModelDiscoveryError, discover_documented_models
    async def handler(request):
        return httpx.Response(200, text='# Completely different document')
    with pytest.raises(ModelDiscoveryError, match='format changed'):
        await discover_documented_models('openai', transport=httpx.MockTransport(handler))
