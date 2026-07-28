"""Shared test fixtures."""

import sys
from pathlib import Path

import pytest

# Make project root importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class MockLLMClient:
    """A fake LLM client that returns predetermined responses."""

    def __init__(self, default_model: str = "mock-model", provider_name: str = "mock"):
        self.default_model = default_model
        self.provider_name = provider_name
        self.calls: list = []
        self.responses: list = []  # queue of responses; cycles if exhausted
        self._index = 0

    def complete(self, messages, model="", system="", temperature=0.3, **kwargs) -> str:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "system": system,
                "temperature": temperature,
            }
        )
        if not self.responses:
            return "[mock response]"
        resp = self.responses[self._index % len(self.responses)]
        self._index += 1
        return resp

    def add_response(self, text: str) -> None:
        self.responses.append(text)


@pytest.fixture
def mock_llm():
    return MockLLMClient()


UI_AUTH_ENV_KEYS = (
    "PANTHEON_UI_AUTH_ENABLED",
    "PANTHEON_UI_USERNAME",
    "PANTHEON_UI_PASSWORD",
    "PANTHEON_UI_PASSWORD_HASH",
    "PANTHEON_UI_SESSION_SECRET",
)


@pytest.fixture(autouse=True)
def isolate_ui_auth_env(monkeypatch):
    """Keep a local .env login lock from leaking across tests."""
    for key in UI_AUTH_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
