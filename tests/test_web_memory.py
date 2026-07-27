from __future__ import annotations

from fastapi.testclient import TestClient

from pantheon.web import create_app


def test_memory_api_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    initial = client.get("/api/memory")
    assert initial.status_code == 200
    assert initial.json()["stats"]["count"] == 0

    created = client.post(
        "/api/memory",
        json={
            "content": "The project prefers a clean glass UI without heavy neon.",
            "kind": "project",
            "source": "manual",
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["stats"]["count"] == 1
    item = data["item"]
    assert item["kind"] == "project"
    assert "glass UI" in item["content"]
    assert (tmp_path / ".pantheon" / "memory.sqlite").exists()

    searched = client.get("/api/memory", params={"query": "glass"})
    assert searched.status_code == 200
    assert searched.json()["items"][0]["id"] == item["id"]

    settings = client.post(
        "/api/memory/settings",
        json={"enabled": False, "auto_capture": True},
    )
    assert settings.status_code == 200
    assert settings.json()["stats"]["enabled"] is False
    assert settings.json()["settings"]["auto_capture"] is True

    deleted = client.delete(f"/api/memory/{item['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["stats"]["count"] == 0


def test_memory_suggestion_api_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    created = client.post(
        "/api/memory",
        json={
            "content": "Hephaestus 写代码时优先保持现有架构。",
            "kind": "note",
            "source": "manual",
        },
    )
    assert created.status_code == 200
    assert created.json()["item"]["role"] == "hephaestus"
    assert created.json()["item"]["kind"] == "agent"

    # A normal project fact becomes a pending suggestion before it is saved.
    from pantheon.core.memory import MemoryStore

    store = MemoryStore(tmp_path / ".pantheon" / "memory.sqlite")
    suggestion = store.suggest("当前项目叫 Pantheon，是神殿多 agent 协作系统。", kind="project")

    listed = client.get("/api/memory")
    assert listed.status_code == 200
    assert listed.json()["stats"]["pending_suggestions"] == 1
    assert listed.json()["suggestions"][0]["id"] == suggestion["id"]

    accepted = client.post(f"/api/memory/suggestions/{suggestion['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["item"]["source"] == "suggested"
    assert accepted.json()["stats"]["pending_suggestions"] == 0

    ignored_suggestion = store.suggest("UI 风格偏简洁高级。", kind="project")
    ignored = client.post(f"/api/memory/suggestions/{ignored_suggestion['id']}/ignore")
    assert ignored.status_code == 200
    assert ignored.json()["stats"]["pending_suggestions"] == 0


def test_memory_api_validates_kind_and_content(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    empty = client.post("/api/memory", json={"content": "   ", "kind": "note"})
    assert empty.status_code == 400

    bad_kind = client.post("/api/memory", json={"content": "remember me", "kind": "bad"})
    assert bad_kind.status_code == 400
