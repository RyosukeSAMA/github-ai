from __future__ import annotations

from fastapi.testclient import TestClient

from pantheon.web import create_app


def test_workspace_lists_reads_and_previews_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("SECRET=1", encoding="utf-8")
    (tmp_path / "index.html").write_text("<!doctype html><h1>Hello</h1>", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("print('ok')\n", encoding="utf-8")

    client = TestClient(create_app())

    listing = client.get("/api/workspace/files")
    assert listing.status_code == 200
    names = {item["name"] for item in listing.json()["items"]}
    assert "index.html" in names
    assert "src" in names
    assert ".env" not in names

    file_resp = client.get("/api/workspace/file", params={"path": "src/app.py"})
    assert file_resp.status_code == 200
    assert file_resp.json()["content"] == "print('ok')\n"

    preview = client.get("/api/workspace/preview", params={"path": "index.html"})
    assert preview.status_code == 200
    assert "Hello" in preview.text
    assert "sandbox" in preview.headers["content-security-policy"]
    assert "allow-popups" in preview.headers["content-security-policy"]


def test_workspace_rejects_path_escape(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    resp = client.get("/api/workspace/file", params={"path": "../secret.txt"})

    assert resp.status_code == 403


def test_workspace_saves_generated_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    save_resp = client.post(
        "/api/workspace/file",
        json={"path": "pantheon-artifacts/demo.py", "content": "print('ok')\n"},
    )

    assert save_resp.status_code == 200
    assert save_resp.json()["path"] == "pantheon-artifacts/demo.py"
    assert (tmp_path / "pantheon-artifacts" / "demo.py").read_text(encoding="utf-8") == "print('ok')\n"

    duplicate = client.post(
        "/api/workspace/file",
        json={"path": "pantheon-artifacts/demo.py", "content": "print('new')\n"},
    )
    assert duplicate.status_code == 409

    overwrite = client.post(
        "/api/workspace/file",
        json={"path": "pantheon-artifacts/demo.py", "content": "print('new')\n", "overwrite": True},
    )
    assert overwrite.status_code == 200
    assert (tmp_path / "pantheon-artifacts" / "demo.py").read_text(encoding="utf-8") == "print('new')\n"

    escape = client.post(
        "/api/workspace/file",
        json={"path": "../escape.py", "content": "bad"},
    )
    assert escape.status_code == 403


def test_workspace_terminal_streams_command_output(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    resp = client.post(
        "/api/workspace/terminal/stream",
        json={"command": "printf hello", "cwd": ""},
    )

    assert resp.status_code == 200
    assert "event: stdout" in resp.text
    assert "hello" in resp.text
    assert "event: exit" in resp.text
