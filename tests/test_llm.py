"""Tests for LLM clients (using mocks for the SDK calls)."""

from unittest.mock import MagicMock, patch

import pytest

from pantheon.llm import get_llm_client
from pantheon.llm.anthropic_client import AnthropicClient
from pantheon.llm.base import BaseLLMClient
from pantheon.llm.ollama_client import OllamaClient
from pantheon.llm.openai_client import OpenAIClient


def test_factory_creates_openai():
    c = get_llm_client("openai", api_key="sk-test")
    assert isinstance(c, OpenAIClient)
    assert c.api_key == "sk-test"


def test_factory_creates_anthropic():
    c = get_llm_client("anthropic", api_key="sk-ant-test")
    assert isinstance(c, AnthropicClient)
    assert c.api_key == "sk-ant-test"


def test_factory_creates_ollama():
    c = get_llm_client("ollama")
    assert isinstance(c, OllamaClient)
    assert "11434" in c.base_url


def test_factory_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_client("nonexistent")


def test_openai_complete():
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "hello from gpt"

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("openai.OpenAI", return_value=fake_client):
        c = OpenAIClient(api_key="sk-test")
        result = c.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o",
        )
    assert result == "hello from gpt"
    fake_client.chat.completions.create.assert_called_once()
    fake_client.responses.create.assert_not_called()


def test_openai_latest_models_use_responses_api():
    fake_response = MagicMock()
    fake_response.output_text = "hello from responses"

    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_response

    with patch("openai.OpenAI", return_value=fake_client):
        c = OpenAIClient(api_key="sk-test")
        result = c.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-5.5",
            system="be brief",
            temperature=0.2,
        )
    assert result == "hello from responses"
    fake_client.responses.create.assert_called_once()
    call_kwargs = fake_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-5.5"
    assert call_kwargs["instructions"] == "be brief"
    fake_client.chat.completions.create.assert_not_called()


def test_anthropic_complete():
    # Mock the response with content blocks
    fake_block = MagicMock()
    fake_block.text = "hello from claude"
    fake_response = MagicMock()
    fake_response.content = [fake_block]

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    with patch("anthropic.Anthropic", return_value=fake_client):
        c = AnthropicClient(api_key="sk-ant-test")
        result = c.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-sonnet-4-20250514",
            system="be brief",
        )
    assert result == "hello from claude"
    # Verify system prompt was passed
    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "be brief"


def test_openai_uses_default_model_when_empty():
    c = OpenAIClient(api_key="sk-test")
    assert c.default_model == "gpt-5.5"


def test_anthropic_uses_default_model_when_empty():
    c = AnthropicClient(api_key="sk-ant-test")
    assert c.default_model.startswith("claude")


def test_base_client_is_abstract():
    with pytest.raises(TypeError):
        BaseLLMClient()
