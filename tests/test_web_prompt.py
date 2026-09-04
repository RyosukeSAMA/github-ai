from fastapi.testclient import TestClient

import pantheon.web.app as web_app


def test_prompt_enhance_endpoint_uses_hermes_without_sending(tmp_path, monkeypatch) -> None:
    class FakeRouter:
        def __init__(self) -> None:
            self.calls = []

        def enhance_prompt(self, prompt: str, mode: str) -> str:
            self.calls.append((prompt, mode))
            return "Build a responsive profile page with semantic HTML."

    class FakeHermes:
        pass

    class FakePantheon:
        instance = None

        def __init__(self, *args, **kwargs) -> None:
            self.router = FakeRouter()
            self.hermes = FakeHermes()
            FakePantheon.instance = self

        def get_role(self, name):
            return None

    monkeypatch.setenv("PANTHEON_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(web_app, "Pantheon", FakePantheon)
    client = TestClient(web_app.create_app())

    response = client.post(
        "/api/prompt/enhance",
        json={"prompt": "make profile page", "mode": "multi"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "prompt": "Build a responsive profile page with semantic HTML.",
    }
    assert FakePantheon.instance.router.calls == [("make profile page", "multi")]


def test_prompt_enhance_endpoint_rejects_empty_prompt(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PANTHEON_WORKSPACE", str(tmp_path))
    client = TestClient(web_app.create_app())

    response = client.post("/api/prompt/enhance", json={"prompt": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "prompt is required"
