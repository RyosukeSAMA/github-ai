"""Tests for individual roles (Hephaestus, Athena, Apollo, Chronos)."""


from pantheon.core.base import Task
from pantheon.roles import (
    Apollo,
    Athena,
    Chronos,
    Hephaestus,
    register_default_roles,
)
from tests.conftest import MockLLMClient


def test_register_default_roles_returns_all_four():
    roles = register_default_roles()
    assert "hephaestus" in roles
    assert "athena" in roles
    assert "apollo" in roles
    assert "chronos" in roles


def test_hephaestus_runs_with_mock():
    mock = MockLLMClient()
    mock.add_response("```python\nprint('hello')\n```")
    h = Hephaestus(llm_client=mock)
    result = h.run(Task(content="print hello"))
    assert result.role == "hephaestus"
    assert "print" in result.content
    assert result.success is True
    assert len(mock.calls) == 1
    assert "Hephaestus" in mock.calls[0]["system"]


def test_athena_runs_with_mock():
    mock = MockLLMClient()
    mock.add_response("Sources: arxiv.org/...")
    a = Athena(llm_client=mock)
    result = a.run(Task(content="Compare transformers vs RNNs"))
    assert result.role == "athena"
    assert "arxiv" in result.content
    assert "research analyst" in mock.calls[0]["system"].lower()


def test_apollo_runs_with_mock():
    mock = MockLLMClient()
    mock.add_response("A neon temple in the rain, cyberpunk style...")
    ap = Apollo(llm_client=mock)
    result = ap.run(Task(content="Write a Midjourney prompt"))
    assert result.role == "apollo"
    assert "neon temple" in result.content
    assert result.success is True


def test_chronos_runs_without_llm():
    """Chronos doesn't need an LLM client."""
    c = Chronos(llm_client=None)
    assert c.model == ""
    assert c.llm_client is None
    result = c.run(Task(content="Every day at 9 AM, ping Athena"))
    assert result.role == "chronos"
    assert "Chronos" in result.content
    assert "Received" in result.content
    assert result.success is True


def test_role_handles_llm_error():
    """If the LLM call raises, the role returns a failed TaskResult."""

    class BrokenClient(MockLLMClient):
        def complete(self, *args, **kwargs):
            raise RuntimeError("network down")

    h = Hephaestus(llm_client=BrokenClient())
    result = h.run(Task(content="anything"))
    assert result.success is False
    assert "network down" in result.content or "network down" in result.error
    assert result.error is not None


def test_role_passes_context_to_llm():
    mock = MockLLMClient()
    mock.add_response("answer with context")
    h = Hephaestus(llm_client=mock)
    ctx = [{"step": "research", "role": "athena", "result": "LLMs are transformers"}]
    h.run(Task(content="use this info"), context=ctx)
    user_msg = mock.calls[0]["messages"][0]["content"]
    assert "research" in user_msg
    assert "athena" in user_msg
    assert "transformers" in user_msg


def test_role_temperature_default():
    h = Hephaestus(llm_client=MockLLMClient())
    assert h.temperature == 0.1

    a = Athena(llm_client=MockLLMClient())
    assert a.temperature == 0.3

    ap = Apollo(llm_client=MockLLMClient())
    assert ap.temperature == 0.7


def test_role_can_override_temperature():
    h = Hephaestus(llm_client=MockLLMClient(), temperature=0.5)
    assert h.temperature == 0.5
