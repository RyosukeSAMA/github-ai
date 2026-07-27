from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from pantheon.core.base import Task, TaskResult
from pantheon.core.extensions import MCPManager, PluginStore, SkillStore
from pantheon.core.hermes import Hermes
from pantheon.core.router import Router
from pantheon.web import create_app


def test_skill_and_plugin_lifecycle_and_role_context(tmp_path) -> None:
    skill_store = SkillStore(
        tmp_path / "skills.json",
        builtin_path=tmp_path / "builtins",
    )
    plugin_store = PluginStore(tmp_path / "plugins.json")

    skill = skill_store.save(
        name="Review rules",
        description="Code review defaults",
        instructions="Review for regressions before suggesting edits.",
        roles=["hephaestus"],
    )
    plugin = plugin_store.save(
        name="Project pack",
        description="Project conventions",
        instructions="Keep existing APIs backward compatible.",
        roles=["global"],
    )

    skill_context, skill_matches = skill_store.context_block("review", "hephaestus")
    plugin_context, plugin_matches = plugin_store.context_block("review", "athena")

    assert skill["id"] in {item["id"] for item in skill_matches}
    assert "Review for regressions" in skill_context
    assert (tmp_path / "skills" / skill["id"] / "SKILL.md").exists()
    assert plugin["id"] in {item["id"] for item in plugin_matches}
    assert "backward compatible" in plugin_context

    assert skill_store.set_enabled(skill["id"], False)["enabled"] is False
    assert skill_store.delete(skill["id"]) is True
    assert plugin_store.delete(plugin["id"]) is True


def test_hermes_executes_explicit_mcp_tool_call() -> None:
    class FakeRole:
        def run(self, task, context=None):
            if "MCP tool result" not in task.content:
                return TaskResult(role="hephaestus", content=(
                    '<tool_call>{"server_id":"demo","tool":"echo",'
                    '"arguments":{"text":"hello"}}</tool_call>'
                ))
            return TaskResult(role="hephaestus", content="The tool returned hello.")

    hermes = Hermes(
        roles={"hephaestus": FakeRole()},
        router=Router(llm_client=None),
    )
    hermes.mcp_tool_executor = lambda call: {"text": call["arguments"]["text"]}

    result = hermes.dispatch(Task(
        content="Echo hello",
        mode="role:hephaestus",
    ))

    assert result["content"] == "The tool returned hello."
    assert result["steps"][0].metadata["mcp_calls"][0]["tool"] == "echo"


def test_hermes_emits_mcp_call_lifecycle_with_role_context() -> None:
    class FakeRole:
        def run(self, task, context=None):
            if "MCP tool result" not in task.content:
                return TaskResult(
                    role="athena",
                    content=(
                        '<tool_call>{"server_id":"docs","tool":"search",'
                        '"arguments":{"query":"MCP"}}</tool_call>'
                    ),
                )
            return TaskResult(role="athena", content="Research complete.")

    events: list[tuple[str, dict]] = []
    executor_context: list[tuple[str, bool]] = []
    hermes = Hermes(
        roles={"athena": FakeRole()},
        router=Router(llm_client=None),
    )

    def executor(call, *, role_name="", on_event=None):
        executor_context.append((role_name, callable(on_event)))
        return {"text": call["arguments"]["query"]}

    hermes.mcp_tool_executor = executor
    result = hermes.dispatch(
        Task(content="Research MCP", mode="role:athena"),
        on_event=lambda event, data: events.append((event, data)),
    )

    assert result["content"] == "Research complete."
    assert executor_context == [("athena", True)]
    lifecycle = [event for event, _data in events if event.startswith("mcp_call_")]
    assert lifecycle == ["mcp_call_start", "mcp_call_done"]
    start = next(data for event, data in events if event == "mcp_call_start")
    assert start["role"] == "athena"
    assert start["tool"] == "search"
    assert start["call_id"]


def test_mcp_environment_and_tool_access_are_explicit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PANTHEON_SHOULD_NOT_LEAK", "secret")
    secrets = {"LOCAL_DOCS_TOKEN": "token-value"}
    manager = MCPManager(
        tmp_path / "mcp_servers.json",
        env_lookup=lambda name: secrets.get(name, ""),
    )
    server = manager.save({
        "name": "Docs",
        "transport": "stdio",
        "command": sys.executable,
        "env": {"DOCS_TOKEN": "LOCAL_DOCS_TOKEN"},
        "enabled": True,
        "allow_agent_calls": True,
        "roles": ["athena", "hephaestus"],
        "last_test": {"ok": True},
        "tools": [
            {
                "name": "search",
                "description": "Search documentation",
                "input_schema": {"type": "object"},
                "annotations": {"read_only": True},
                "risk": "read",
            },
            {
                "name": "publish",
                "description": "Publish a page",
                "input_schema": {"type": "object"},
                "annotations": {"destructive": False},
                "risk": "write",
            },
        ],
    })

    child_env = manager._env_for(server)
    assert child_env["DOCS_TOKEN"] == "token-value"
    assert "PANTHEON_SHOULD_NOT_LEAK" not in child_env

    manager.set_tool_policy(
        server["id"],
        "publish",
        enabled=True,
        roles=["hephaestus"],
        approval="ask",
    )
    athena_context, athena_tools = manager.agent_context("research", "athena")
    hephaestus_context, hephaestus_tools = manager.agent_context("build", "hephaestus")

    assert "search" in athena_context
    assert "publish" not in athena_context
    assert {item["tool"] for item in athena_tools} == {"search"}
    assert "search" in hephaestus_context
    assert "publish" in hephaestus_context
    assert {item["tool"] for item in hephaestus_tools} == {"search", "publish"}
    policy = manager.agent_tool_policy(server["id"], "publish", "hephaestus")
    assert policy["approval"] == "ask"


def test_mcp_stdio_server_can_be_inspected_and_called(tmp_path) -> None:
    server_script = tmp_path / "mcp_server.py"
    server_script.write_text(
        """
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Pantheon test")

@mcp.tool()
def echo(text: str) -> str:
    return text

if __name__ == "__main__":
    mcp.run(transport="stdio")
""".strip()
        + "\n",
        encoding="utf-8",
    )
    manager = MCPManager(tmp_path / "mcp_servers.json")
    server = manager.save({
        "name": "Test server",
        "transport": "stdio",
        "command": sys.executable,
        "args": [str(server_script)],
        "enabled": True,
    })

    inspected = manager.inspect(server["id"])
    assert inspected["ok"] is True
    assert any(tool["name"] == "echo" for tool in inspected["tools"])

    called = manager.call_tool(server["id"], "echo", {"text": "hello"})
    assert called["text"] == "hello"


def test_mcp_http_server_uses_configured_header_client(tmp_path, monkeypatch) -> None:
    import mcp
    from mcp.client import streamable_http

    captured = {}

    class FakeClientSession:
        def __init__(self, _read_stream, _write_stream) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _traceback) -> None:
            return None

        async def initialize(self):
            return {}

    @asynccontextmanager
    async def fake_streamable_http_client(url, *, http_client, terminate_on_close=True):
        captured["url"] = url
        captured["authorization"] = http_client.headers.get("Authorization")
        captured["docs_key"] = http_client.headers.get("X-Docs-Key")
        captured["client"] = http_client
        yield object(), object(), lambda: None

    monkeypatch.setattr(mcp, "ClientSession", FakeClientSession)
    monkeypatch.setattr(
        streamable_http,
        "streamable_http_client",
        fake_streamable_http_client,
    )
    secrets = {"GITHUB_TOKEN": "github-secret", "DOCS_TOKEN": "docs-secret"}
    manager = MCPManager(
        tmp_path / "mcp_servers.json",
        env_lookup=lambda name: secrets.get(name, ""),
    )
    server = manager.save({
        "name": "Remote tools",
        "transport": "streamable_http",
        "url": "https://example.com/mcp",
        "bearer_token_env_var": "GITHUB_TOKEN",
        "headers_env": {"X-Docs-Key": "DOCS_TOKEN"},
        "enabled": True,
    })

    async def operation(_session, _initialized):
        return "connected"

    result = manager._run_sync(lambda: manager._with_session(server, operation))

    assert result == "connected"
    assert captured["url"] == "https://example.com/mcp"
    assert captured["authorization"] == "Bearer github-secret"
    assert captured["docs_key"] == "docs-secret"
    assert captured["client"].is_closed is True


def test_mcp_api_saves_credentials_by_environment_reference(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    created = client.post(
        "/api/mcp/servers",
        json={
            "name": "Private docs",
            "transport": "stdio",
            "command": sys.executable,
            "credential_env_var": "PRIVATE_DOCS_TOKEN",
            "credential_value": "local-secret-value",
            "roles": ["athena"],
        },
    )

    assert created.status_code == 200
    item = created.json()["item"]
    assert item["env"] == {"PRIVATE_DOCS_TOKEN": "PRIVATE_DOCS_TOKEN"}
    assert "credential_value" not in item
    assert "local-secret-value" not in (
        tmp_path / ".pantheon" / "mcp_servers.json"
    ).read_text(encoding="utf-8")
    assert "PRIVATE_DOCS_TOKEN=local-secret-value" in (
        tmp_path / ".env"
    ).read_text(encoding="utf-8")
    listed = client.get("/api/mcp/servers").json()["items"][0]
    assert listed["credentials_ready"] is True
    assert listed["credential_env_vars"] == ["PRIVATE_DOCS_TOKEN"]


def test_webhook_requires_token_and_skill_api_is_real(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    created = client.post(
        "/api/skills",
        json={
            "name": "Concise replies",
            "description": "Keep output focused",
            "instructions": "Prefer concise explanations.",
            "roles": ["global"],
        },
    )
    assert created.status_code == 200
    created_item = next(
        item for item in created.json()["items"]
        if item["name"] == "Concise replies"
    )
    assert created_item["source"] == "local"
    assert (
        tmp_path / ".pantheon" / "skills" / created_item["id"] / "SKILL.md"
    ).exists()

    configured = client.post(
        "/api/channels/webhook/config",
        json={"enabled": True, "token": "test-webhook-token"},
    )
    assert configured.status_code == 200
    assert configured.json()["token"] == "test-webhook-token"

    unauthorized = client.post("/api/channels/webhook", json={"task": "hello"})
    assert unauthorized.status_code == 401

    status = client.get("/api/channels")
    assert status.status_code == 200
    assert status.json()["items"][0]["token"] == ""
    assert status.json()["items"][0]["token_configured"] is True


def test_builtin_skills_match_only_relevant_role(tmp_path) -> None:
    builtins = Path(__file__).resolve().parents[1] / "pantheon" / "skills"
    store = SkillStore(tmp_path / "skills", builtin_path=builtins)

    context, matches = store.context_block("请修复这个 bug 并跑测试", "hephaestus")
    unrelated_context, unrelated_matches = store.context_block(
        "请修复这个 bug",
        "athena",
    )

    assert matches[0]["id"] == "fix-and-verify"
    assert "Implement the smallest change" in context
    assert all(item["id"] != "fix-and-verify" for item in unrelated_matches)
    assert "Fix and Verify" not in unrelated_context
    assert "build-web-preview" in {
        item["id"] for item in store.catalog_for_roles()["apollo"]
    }


def test_legacy_skill_json_is_migrated_without_deleting_source(tmp_path) -> None:
    legacy_path = tmp_path / "skills.json"
    legacy_path.write_text(
        '[{"id":"legacy-review","name":"Legacy review",'
        '"instructions":"Check compatibility.","roles":["athena"]}]',
        encoding="utf-8",
    )

    store = SkillStore(
        legacy_path,
        builtin_path=tmp_path / "builtins",
    )

    migrated = store.get("legacy-review")
    assert migrated is not None
    assert migrated["source"] == "local"
    assert (tmp_path / "skills" / "legacy-review" / "SKILL.md").exists()
    assert legacy_path.exists()
