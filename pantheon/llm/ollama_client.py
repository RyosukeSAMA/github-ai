"""Ollama (local LLM) client. Uses the OpenAI-compatible /v1 endpoint."""

from __future__ import annotations

from typing import Any, Dict, List

from pantheon.llm.openai_client import OpenAIClient


class OllamaClient(OpenAIClient):
    """Ollama exposes an OpenAI-compatible API. We reuse the OpenAI client."""

    default_model = "llama3.1"
    provider_name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", api_key: str = "") -> None:
        # Ollama typically doesn't need an API key.
        super().__init__(api_key=api_key or "ollama", base_url=f"{base_url.rstrip('/')}/v1")
