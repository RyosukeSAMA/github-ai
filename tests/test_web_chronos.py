from __future__ import annotations

from fastapi.testclient import TestClient

from pantheon.web import create_app


def test_chronos_job_api_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    created = client.post("/api/chronos/jobs", json={"text": "daily at 09:00 remind me to stand up"})
    assert created.status_code == 200
    data = created.json()
    job = data["job"]
    assert job["schedule_type"] == "daily"
    assert job["enabled"] is True
    assert job["prompt"] == "remind me to stand up"
    assert (tmp_path / ".pantheon" / "chronos_jobs.json").exists()

    listed = client.get("/api/chronos/jobs")
    assert listed.status_code == 200
    assert listed.json()["jobs"][0]["id"] == job["id"]

    paused = client.post(f"/api/chronos/jobs/{job['id']}/pause")
    assert paused.status_code == 200
    assert paused.json()["job"]["enabled"] is False

    resumed = client.post(f"/api/chronos/jobs/{job['id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["job"]["enabled"] is True

    deleted = client.delete(f"/api/chronos/jobs/{job['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["jobs"] == []


def test_chronos_job_api_reports_parse_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    resp = client.post("/api/chronos/jobs", json={"text": "sometime maybe do this"})

    assert resp.status_code == 400
    assert "every 10 minutes" in resp.json()["detail"]
