"""OpenAI / OpenAI-compatible client."""

from __future__ import annotations

from typing import Any

from pantheon.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """Calls OpenAI's Chat Completions API. Works for OpenAI-compatible endpoints too."""

    default_model = "gpt-4o"
    provider_name = "openai"

    def __init__(self, api_key: str = "", base_url: str | None = None) -> None:
        super().__init__(api_key=api_key, base_url=base_url)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError(
                    "openai package is required: pip install openai"
                ) from e
            kwargs: dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        system: str = "",
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        full_messages = list(messages)
        if system:
            full_messages = [{"role": "system", "content": system}] + full_messages

        resp = client.chat.completions.create(
            model=model or self.default_model,
            messages=full_messages,
            temperature=temperature,
            **kwargs,
        )
        return (resp.choices[0].message.content or "").strip()
