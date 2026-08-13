from __future__ import annotations

import pytest

from pantheon.core.pantheon import Pantheon
from pantheon.diagnostics import ProviderProbeError, probe_role_provider


class FakeClient:
    provider_name = "openai"
    api_key = "sk-test-secret-1234"
    default_model = "gpt-5.5"

    def __init__(self, response: str = "ok", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def _uses_official_openai_endpoint(self) -> bool:
        return True

    def complete(self, messages, model, system="", temperature=0.3, **kwargs):
        self.calls.append({"messages": messages, "model": model, "kwargs": kwargs})
        if self.error:
            raise self.error
        return self.response


class FakePantheon:
    def __init__(self, client: FakeClient) -> None:
        self.router = type(
            "Router",
            (),
            {"llm_client": client, "hermes_model": "gpt-5.5"},
        )()
        self.roles = {
            "athena": type("Role", (), {"llm": client, "model": "gpt-5.4-mini"})(),
        }

    def get_role(self, name: str):
        return self.roles.get(name)


def test_probe_role_provider_uses_minimal_request() -> None:
    client = FakeClient()
    result = probe_role_provider("hermes", pantheon=FakePantheon(client))

    assert result["ok"] is True
    assert result["provider"] == "openai"
    assert result["model"] == "gpt-5.5"
    assert client.calls[0]["kwargs"] == {"max_output_tokens": 8, "timeout": 20.0}


def test_probe_role_provider_rejects_unknown_role() -> None:
    with pytest.raises(ProviderProbeError, match="Unknown or disabled"):
        probe_role_provider("poseidon", pantheon=FakePantheon(FakeClient()))


def test_probe_role_provider_redacts_key_from_errors() -> None:
    client = FakeClient(error=RuntimeError("rejected sk-test-secret-1234"))
    with pytest.raises(ProviderProbeError) as caught:
        probe_role_provider("athena", pantheon=FakePantheon(client))

    assert "sk-test-secret-1234" not in str(caught.value)
    assert "sk-t...1234" in str(caught.value)


def test_probe_reads_real_pantheon_router_attribute(tmp_path, monkeypatch) -> None:
    config = tmp_path / "pantheon.yaml"
    config.write_text(
        """
pantheon:
  hermes: {model: probe-model, provider: openai}
  roles: {}
llm_providers:
  openai: {api_key: probe-key}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    runtime = Pantheon(config_path=str(config))
    calls: list[dict] = []

    def fake_complete(messages, model, system="", temperature=0.3, **kwargs):
        calls.append({"messages": messages, "model": model, "kwargs": kwargs})
        return "ok"

    monkeypatch.setattr(runtime.router.llm_client, "complete", fake_complete)
    result = probe_role_provider("hermes", pantheon=runtime)

    assert result["model"] == "probe-model"
    assert calls[0]["model"] == "probe-model"


def test_probe_labels_deepseek_compatible_endpoint() -> None:
    client = FakeClient()
    client.base_url = "https://api.deepseek.com"

    result = probe_role_provider("hermes", pantheon=FakePantheon(client))

    assert result["provider"] == "deepseek"
