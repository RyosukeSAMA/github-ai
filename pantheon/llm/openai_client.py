"""OpenAI / OpenAI-compatible client."""

from __future__ import annotations

from typing import Any

from pantheon.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """Calls OpenAI APIs. Uses Chat Completions for compatible endpoints."""

    default_model = "gpt-5.5"
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

    def _uses_official_openai_endpoint(self) -> bool:
        if not self.base_url:
            return True
        return "api.openai.com" in self.base_url

    def _uses_responses_api(self, model: str) -> bool:
        return self._uses_official_openai_endpoint() and (model or self.default_model).startswith("gpt-5")

    @staticmethod
    def _flatten_response_text(resp: Any) -> str:
        output_text = getattr(resp, "output_text", None)
        if output_text:
            return str(output_text).strip()

        parts: list[str] = []
        for item in getattr(resp, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts).strip()

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

        target_model = model or self.default_model
        if self._uses_responses_api(target_model):
            response_kwargs = dict(kwargs)
            response_kwargs.pop("max_tokens", None)
            response_kwargs.pop("temperature", None)
            resp = client.responses.create(
                model=target_model,
                input=list(messages),
                instructions=system or None,
                **response_kwargs,
            )
            return self._flatten_response_text(resp)

        resp = client.chat.completions.create(
            model=target_model,
            messages=full_messages,
            temperature=temperature,
            **kwargs,
        )
        return (resp.choices[0].message.content or "").strip()
