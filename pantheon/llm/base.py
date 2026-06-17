"""Base class for LLM clients."""

from __future__ import annotations

import abc
from typing import Any


class BaseLLMClient(abc.ABC):
    """Abstract base. All providers expose the same `complete()` interface."""

    default_model: str = ""
    provider_name: str = ""

    def __init__(self, api_key: str = "", base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url

    @abc.abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        system: str = "",
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> str:
        """Call the LLM and return the assistant's text content.

        Args:
            messages: OpenAI-style messages [{"role": ..., "content": ...}, ...].
            model: The model ID to use.
            system: System prompt (separate field for Anthropic-style APIs).
            temperature: Sampling temperature.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{type(self).__name__} provider={self.provider_name} model={self.default_model}>"
