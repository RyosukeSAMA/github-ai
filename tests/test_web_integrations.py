from __future__ import annotations

from fastapi.testclient import TestClient

from pantheon.web import create_app


def test_integrations_api_reports_extension_map(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    resp = client.get("/api/integrations")

    assert resp.status_code == 200
    data = resp.json()
    assert set(data["sections"]) == {"mcp", "plugins", "skills", "channels"}
    assert data["summary"]["mcp"]["total"] == len(data["sections"]["mcp"])
    assert data["summary"]["plugins"]["ready"] >= 1
    assert any(item["id"] == "workspace" for item in data["sections"]["mcp"])
    assert any(item["id"] == "web-ui" for item in data["sections"]["channels"])
    assert data["paths"]["config_path"].endswith("config/pantheon.yaml")
    assert data["paths"]["env_path"].endswith(".env")
    assert str(tmp_path) in data["paths"]["plugins_path"]
    assert str(tmp_path) in data["paths"]["skills_path"]
