"""Anthropic Claude client."""

from __future__ import annotations

from typing import Any

from pantheon.llm.base import BaseLLMClient


class AnthropicClient(BaseLLMClient):
    """Calls Anthropic's Messages API."""

    default_model = "claude-sonnet-4-6"
    provider_name = "anthropic"

    def __init__(self, api_key: str = "", base_url: str | None = None) -> None:
        super().__init__(api_key=api_key, base_url=base_url)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise ImportError(
                    "anthropic package is required: pip install anthropic"
                ) from e
            kwargs: dict[str, Any] = {}
            is_kie_gateway = "api.kie.ai" in (self.base_url or "").lower()
            if self.api_key:
                if is_kie_gateway:
                    token = self.api_key.strip()
                    if token.lower().startswith("bearer "):
                        token = token[7:].strip()
                    kwargs["auth_token"] = token
                else:
                    kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        # Anthropic requires max_tokens; default if not given.
        kwargs.setdefault("max_tokens", max_tokens)

        resp = client.messages.create(
            model=model or self.default_model,
            system=system or "You are a helpful assistant.",
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        # Concatenate all text blocks
        parts = [b.text for b in resp.content if hasattr(b, "text")]
        return "".join(parts).strip()
