"""Tests for Pantheon facade + config loading."""

import os
import tempfile

import pytest
import yaml

from pantheon.core.pantheon import Pantheon


@pytest.fixture
def temp_config(tmp_path):
    """Write a minimal pantheon.yaml in a temp dir."""
    cfg = {
        "pantheon": {
            "hermes": {"model": "mock-model", "provider": "openai"},
            "roles": {
                "hephaestus": {"model": "mock-model", "provider": "openai", "enabled": True},
                "athena": {"model": "mock-model", "provider": "openai", "enabled": True},
                "apollo": {"model": "mock-model", "provider": "openai", "enabled": True},
                "chronos": {"enabled": True},
            },
        },
        "llm_providers": {
            "openai": {"api_key": "sk-fake", "enabled": True},
            "anthropic": {"api_key": "", "enabled": False},
            "ollama": {"base_url": "http://localhost:11434", "enabled": False},
        },
    }
    cfg_path = tmp_path / "pantheon.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    return str(cfg_path)


def test_pantheon_loads_config(temp_config):
    p = Pantheon(config_path=temp_config)
    assert p.config is not None
    assert "hermes" in p.config["pantheon"]


def test_pantheon_lists_roles(temp_config):
    p = Pantheon(config_path=temp_config)
    roles = p.list_roles()
    assert "hephaestus" in roles
    assert "athena" in roles
    assert "apollo" in roles
    assert "chronos" in roles


def test_pantheon_get_role(temp_config):
    p = Pantheon(config_path=temp_config)
    h = p.get_role("hephaestus")
    assert h is not None
    assert h.name == "hephaestus"


def test_pantheon_get_unknown_role_returns_none(temp_config):
    p = Pantheon(config_path=temp_config)
    assert p.get_role("ghost") is None


def test_pantheon_missing_config_uses_packaged_defaults(tmp_path, monkeypatch):
    # Make sure no .env or other config is found
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PANTHEON_CONFIG", raising=False)
    p = Pantheon()
    assert "athena" in p.list_roles()


def test_pantheon_env_var_expansion(temp_config, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    cfg = {
        "pantheon": {
            "hermes": {"model": "m", "provider": "openai"},
            "roles": {
                "hephaestus": {"model": "m", "provider": "openai", "enabled": True},
                "athena": {"model": "m", "provider": "openai", "enabled": True},
                "apollo": {"model": "m", "provider": "openai", "enabled": True},
                "chronos": {"enabled": True},
            },
        },
        "llm_providers": {
            "openai": {"api_key": "${OPENAI_API_KEY}", "enabled": True},
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(cfg, f)
        path = f.name
    try:
        p = Pantheon(config_path=path)
        # The expanded API key should be in the openai client's key
        openai_client = p.llm_clients["openai"]
        assert openai_client.api_key == "sk-from-env"
    finally:
        os.unlink(path)


def test_pantheon_ask_returns_dict(temp_config):
    """Smoke test: ask() returns the expected shape."""
    from tests.conftest import MockLLMClient

    p = Pantheon(config_path=temp_config)
    # Patch the LLM clients with mocks
    mock = MockLLMClient()
    mock.add_response('{"type": "single", "role": "hephaestus", "reasoning": "code"}')
    mock.add_response("def foo(): pass")
    p.llm_clients["openai"] = mock
    # Rebuild roles with the mock client
    from pantheon.roles import register_default_roles
    p.roles = {}
    for name, cls in register_default_roles().items():
        p.roles[name] = cls(
            llm_client=mock,
            model="mock",
            temperature=0.5,
        )
    from pantheon.core.hermes import Hermes
    from pantheon.core.router import Router
    p.router = Router(llm_client=mock, hermes_model="mock")
    p.hermes = Hermes(roles=p.roles, router=p.router)

    events = []
    result = p.ask("write foo", on_event=lambda event, data: events.append((event, data)))
    assert "mode" in result
    assert "content" in result
    assert "steps" in result
    assert [event for event, _ in events] == [
        "plan_start",
        "plan_ready",
        "step_start",
        "step_done",
    ]


def test_sdk_chronos_persists_jobs_visible_to_web(temp_config, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from pantheon.web.app import create_app

    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    p = Pantheon(config_path=temp_config)
    result = p.ask('in 10 minutes remind me to check the build', mode='role:chronos')
    assert result['steps'][0].metadata['scheduled']
    job_id = result['steps'][0].metadata['job']['id']
    client = TestClient(create_app(config_path=temp_config))
    jobs = client.get('/api/chronos/jobs').json()['jobs']
    assert jobs[0]['id'] == job_id
    assert p.services.scheduler.get_job(job_id) is not None


def test_sdk_uses_shared_memory_and_plugin_context(temp_config, tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    p = Pantheon(config_path=temp_config)
    saved = p.services.process_input('remember that this project uses PostgreSQL')
    assert len(saved['saved']) == 1
    context, matches = p.hermes.memory_context_provider('project PostgreSQL', 'hephaestus')
    assert 'PostgreSQL' in context
    assert matches[0]['id'] == saved['saved'][0]['id']
    p.services.plugins.save(name='Review rules', description='project review', instructions='Check migrations', roles=['hephaestus'])
    context, _ = p.hermes.plugin_context_provider('review', 'hephaestus')
    assert 'Check migrations' in context


def test_sdk_mcp_enforces_approval_before_execution(temp_config, tmp_path, monkeypatch):
    from pantheon.core.extensions import MCPError

    monkeypatch.setenv('PANTHEON_WORKSPACE', str(tmp_path))
    p = Pantheon(config_path=temp_config)
    manager = p.services.mcp
    server = manager.save({'name': 'test writer', 'command': 'mock-command', 'allow_agent_calls': True,
                           'roles': ['hephaestus'], 'last_test': {'ok': True}, 'tools': [{'name': 'write_file', 'risk': 'write'}]})
    called = []
    monkeypatch.setattr(manager, 'call_tool', lambda *args: called.append(args) or {'content': 'saved'})
    call = {'server_id': server['id'], 'tool': 'write_file', 'arguments': {'path': 'demo.py'}}
    with pytest.raises(MCPError, match='needs approval'):
        p.hermes.mcp_tool_executor(call, role_name='hephaestus')
    assert not called
    p.services.approval_handler = lambda payload: False
    with pytest.raises(MCPError, match='denied'):
        p.hermes.mcp_tool_executor(call, role_name='hephaestus')
    p.services.approval_handler = lambda payload: payload['arguments']['path'] == 'demo.py'
    assert p.hermes.mcp_tool_executor(call, role_name='hephaestus')['content'] == 'saved'
    assert len(called) == 1
