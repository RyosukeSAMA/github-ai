"""LLM provider adapters."""

from pantheon.llm.base import BaseLLMClient
from pantheon.llm.openai_client import OpenAIClient
from pantheon.llm.anthropic_client import AnthropicClient
from pantheon.llm.ollama_client import OllamaClient


def get_llm_client(provider: str, api_key: str = "", base_url: str | None = None) -> BaseLLMClient:
    """Factory for LLM clients.

    Args:
        provider: One of "openai", "anthropic", "ollama".
        api_key: The API key (not needed for Ollama).
        base_url: Optional custom base URL.
    """
    p = provider.lower()
    if p == "openai":
        return OpenAIClient(api_key=api_key, base_url=base_url)
    if p == "anthropic":
        return AnthropicClient(api_key=api_key, base_url=base_url)
    if p == "ollama":
        return OllamaClient(base_url=base_url or "http://localhost:11434")
    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        "Supported: openai, anthropic, ollama."
    )


__all__ = [
    "BaseLLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "OllamaClient",
    "get_llm_client",
]
