from __future__ import annotations

import yaml
from fastapi.testclient import TestClient

from pantheon.web import create_app


def _write_minimal_config(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
pantheon:
  hermes:
    model: old-model
    provider: openai
  roles:
    hephaestus:
      model: old-model
      provider: openai
    athena:
      model: old-model
      provider: openai
    apollo:
      model: old-model
      provider: openai
    chronos:
      model: none
      provider: none
llm_providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://api.openai.com/v1
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_mixed_config(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
pantheon:
  hermes:
    model: gpt-4o
    provider: openai
  roles:
    hephaestus:
      model: claude-sonnet-4-20250514
      provider: anthropic
    athena:
      model: gpt-4o
      provider: openai
    apollo:
      model: gpt-4o
      provider: openai
    chronos:
      model: none
      provider: none
llm_providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://api.openai.com/v1
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    base_url: https://api.anthropic.com
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_setup_save_writes_env_and_config_without_leaking_key(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config_path = tmp_path / "config" / "pantheon.yaml"
    _write_minimal_config(config_path)

    client = TestClient(create_app())

    resp = client.post(
        "/api/setup/save",
        json={
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "base_url": "https://api.deepseek.com",
            "api_key": "sk-test-secret-1234",
            "apply_to_roles": True,
        },
    )

    assert resp.status_code == 200
    assert "sk-test-secret-1234" not in resp.text
    data = resp.json()
    assert data["provider"] == "deepseek"
    assert data["adapter"] == "openai"
    assert data["key_configured"] is True
    assert data["masked_key"] == "sk-t••••1234"
    assert data["setup_ready"] is True
    assert data["summary_title"] == "DeepSeek · 4/4 ready"
    providers = {item["id"]: item for item in data["providers"]}
    assert providers["deepseek"]["model"] == "deepseek-v4-flash"
    assert any(model["id"] == "deepseek-v4-pro" for model in providers["deepseek"]["models"])
    assert {model["id"] for model in providers["deepseek"]["models"]} == {
        "deepseek-v4-flash",
        "deepseek-v4-pro",
    }
    assert providers["openai"]["model"] == "gpt-5.5"
    assert {item["role"] for item in data["role_statuses"]} == {
        "hermes",
        "hephaestus",
        "athena",
        "apollo",
        "chronos",
    }
    assert all(
        item["status"] == "ready"
        for item in data["role_statuses"]
        if item["counts_toward_ready"]
    )

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=sk-test-secret-1234" in env_text

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved["pantheon"]["hermes"]["provider"] == "openai"
    assert saved["pantheon"]["hermes"]["model"] == "deepseek-v4-flash"
    assert saved["llm_providers"]["openai"]["api_key"] == "${DEEPSEEK_API_KEY}"
    assert saved["llm_providers"]["openai"]["base_url"] == "https://api.deepseek.com"
    for role_name in ("hephaestus", "athena", "apollo"):
        role = saved["pantheon"]["roles"][role_name]
        assert role["provider"] == "openai"
        assert role["model"] == "deepseek-v4-flash"


def test_setup_save_requires_key_when_no_existing_secret(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _write_minimal_config(tmp_path / "config" / "pantheon.yaml")

    client = TestClient(create_app())
    resp = client.post(
        "/api/setup/save",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
        },
    )

    assert resp.status_code == 400
    assert "OPENAI_API_KEY" in resp.json()["detail"]


def test_setup_status_reports_existing_env_secret_as_masked(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _write_minimal_config(tmp_path / "config" / "pantheon.yaml")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-existing-9999\n", encoding="utf-8")

    client = TestClient(create_app())
    resp = client.get("/api/setup/status")

    assert resp.status_code == 200
    assert "sk-existing-9999" not in resp.text
    data = resp.json()
    assert data["provider"] == "openai"
    assert data["key_configured"] is True
    assert data["masked_key"] == "sk-e••••9999"
    assert data["setup_ready"] is True
    assert data["summary_title"] == "OpenAI · 4/4 ready"


def test_setup_test_api_uses_form_values_without_network(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _write_minimal_config(tmp_path / "config" / "pantheon.yaml")

    calls = {}

    class FakeClient:
        def complete(self, messages, model, system="", temperature=0.3, **kwargs):
            calls["messages"] = messages
            calls["model"] = model
            calls["system"] = system
            calls["temperature"] = temperature
            calls["kwargs"] = kwargs
            return "ok"

    def fake_get_llm_client(provider, api_key="", base_url=None):
        calls["provider"] = provider
        calls["api_key"] = api_key
        calls["base_url"] = base_url
        return FakeClient()

    monkeypatch.setattr("pantheon.web.app.get_llm_client", fake_get_llm_client)

    client = TestClient(create_app())
    resp = client.post(
        "/api/setup/test",
        json={
            "provider": "openai",
            "model": "gpt-5.5",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-secret-1234",
        },
    )

    assert resp.status_code == 200
    assert "sk-test-secret-1234" not in resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["tested"] is True
    assert data["tested_provider"] == "openai"
    assert data["tested_model"] == "gpt-5.5"
    assert calls["provider"] == "openai"
    assert calls["api_key"] == "sk-test-secret-1234"
    assert calls["base_url"] == "https://api.openai.com/v1"
    assert calls["model"] == "gpt-5.5"
    assert calls["kwargs"] == {"max_output_tokens": 8}


def test_setup_test_api_masks_provider_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _write_minimal_config(tmp_path / "config" / "pantheon.yaml")

    class FakeClient:
        def complete(self, messages, model, system="", temperature=0.3, **kwargs):
            raise RuntimeError("provider rejected sk-test-secret-1234")

    monkeypatch.setattr(
        "pantheon.web.app.get_llm_client",
        lambda provider, api_key="", base_url=None: FakeClient(),
    )

    client = TestClient(create_app())
    resp = client.post(
        "/api/setup/test",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-secret-1234",
        },
    )

    assert resp.status_code == 200
    assert "sk-test-secret-1234" not in resp.text
    data = resp.json()
    assert data["ok"] is False
    assert data["tested"] is True
    assert data["problem"] == "provider rejected sk-t••••1234"


def test_setup_status_reports_mixed_provider_matrix(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _write_mixed_config(tmp_path / "config" / "pantheon.yaml")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-openai-9999\n", encoding="utf-8")

    client = TestClient(create_app())
    status_resp = client.get("/api/setup/status")
    check_resp = client.post("/api/setup/check")

    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["setup_ready"] is False
    assert data["summary_title"] == "Mixed providers · 3/4 ready"
    roles = {item["role"]: item for item in data["role_statuses"]}
    assert roles["hermes"]["provider_label"] == "OpenAI"
    assert roles["hephaestus"]["provider_label"] == "Anthropic"
    assert roles["hephaestus"]["status"] == "missing_key"
    assert roles["chronos"]["status"] == "no_key_needed"

    assert check_resp.status_code == 200
    check_data = check_resp.json()
    assert check_data["ok"] is False
    assert "ANTHROPIC_API_KEY is not configured." in check_data["problems"]


AUTH_ENV_KEYS = (
    "PANTHEON_UI_AUTH_ENABLED",
    "PANTHEON_UI_USERNAME",
    "PANTHEON_UI_PASSWORD",
    "PANTHEON_UI_PASSWORD_HASH",
    "PANTHEON_UI_SESSION_SECRET",
)


def _clear_auth_env(monkeypatch) -> None:
    for key in AUTH_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_auth_disabled_by_default_keeps_workspace_available(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_auth_env(monkeypatch)

    client = TestClient(create_app())

    status = client.get("/api/auth/status")
    assert status.status_code == 200
    assert status.json()["enabled"] is False
    assert status.json()["authenticated"] is True

    workspace = client.get("/api/workspace")
    assert workspace.status_code == 200


def test_info_reports_local_runtime_paths(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_auth_env(monkeypatch)

    client = TestClient(create_app())
    resp = client.get("/api/info")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ui_version"] == "0.2.0"
    assert data["backend_version"] == "0.2.0"
    assert data["python_version"].startswith("3.11")
    assert data["workspace_path"] == str(tmp_path)
    assert data["config_path"] == str(tmp_path / "config" / "pantheon.yaml")
    assert data["env_path"] == str(tmp_path / ".env")


def test_security_save_enables_login_and_protects_sensitive_api(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_auth_env(monkeypatch)
    app = create_app()
    admin = TestClient(app)

    enabled = admin.post(
        "/api/security/save",
        json={"enabled": True, "username": "admin", "password": "local-pass-123"},
    )
    assert enabled.status_code == 200
    data = enabled.json()
    assert data["enabled"] is True
    assert data["authenticated"] is True
    assert data["username"] == "admin"

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "PANTHEON_UI_AUTH_ENABLED=true" in env_text
    assert "PANTHEON_UI_USERNAME=admin" in env_text
    assert "PANTHEON_UI_PASSWORD_HASH=" in env_text
    assert "pbkdf2_sha256$" in env_text
    assert "local-pass-123" not in env_text

    guest = TestClient(app)
    blocked = guest.get("/api/workspace")
    assert blocked.status_code == 401

    bad_login = guest.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    good_login = guest.post(
        "/api/auth/login",
        json={"username": "admin", "password": "local-pass-123"},
    )
    assert good_login.status_code == 200
    assert good_login.json()["authenticated"] is True

    allowed = guest.get("/api/workspace")
    assert allowed.status_code == 200


def test_security_save_can_disable_login_after_authentication(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_auth_env(monkeypatch)
    app = create_app()
    client = TestClient(app)

    assert client.post(
        "/api/security/save",
        json={"enabled": True, "username": "admin", "password": "local-pass-123"},
    ).status_code == 200

    disabled = client.post(
        "/api/security/save",
        json={"enabled": False, "username": "admin", "password": ""},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    guest = TestClient(app)
    workspace = guest.get("/api/workspace")
    assert workspace.status_code == 200
