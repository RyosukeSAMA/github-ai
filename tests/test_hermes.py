"""Tests for Hermes (orchestrator) end-to-end dispatching."""

import pytest

from pantheon.core.base import Task
from pantheon.core.hermes import Hermes
from pantheon.core.router import Router
from tests.conftest import MockLLMClient


def _build_hermes(mock_llm, role_responses=None):
    """Build a Hermes with mock LLM and roles that just echo via the mock."""
    from pantheon.roles.apollo import Apollo
    from pantheon.roles.athena import Athena
    from pantheon.roles.hephaestus import Hephaestus

    if role_responses:
        for r in role_responses:
            mock_llm.add_response(r)

    roles = {
        "hephaestus": Hephaestus(llm_client=mock_llm),
        "athena": Athena(llm_client=mock_llm),
        "apollo": Apollo(llm_client=mock_llm),
    }
    router = Router(llm_client=mock_llm)
    return Hermes(roles=roles, router=router), roles


def test_hermes_dispatches_to_single_role():
    mock = MockLLMClient()
    mock.add_response('{"type": "single", "role": "hephaestus", "reasoning": "code"}')
    mock.add_response("def foo(): return 42")
    hermes, _ = _build_hermes(mock)
    result = hermes.dispatch(Task(content="write a function"))
    assert result["mode"] == "single"
    assert "foo" in result["content"]
    assert len(result["steps"]) == 1


def test_hermes_routes_to_explicit_role():
    mock = MockLLMClient()
    mock.add_response("here is the research")
    hermes, _ = _build_hermes(mock)
    result = hermes.dispatch(Task(content="anything", mode="role:athena"))
    assert result["mode"] == "single"
    assert "research" in result["content"]


def test_hermes_handles_unknown_explicit_role():
    mock = MockLLMClient()
    hermes, _ = _build_hermes(mock)
    result = hermes.dispatch(Task(content="anything", mode="role:ghost"))
    assert "Error" in result["content"]
    assert "ghost" in result["content"]


def test_hermes_dispatches_multi_role():
    mock = MockLLMClient()
    # First the planner call:
    mock.add_response(
        '{"type": "multi", "reasoning": "complex", '
        '"steps": ['
        '{"role": "athena", "task": "research X"},'
        '{"role": "hephaestus", "task": "implement X"}'
        ']}'
    )
    # Then two role calls:
    mock.add_response("Research findings: X is a transformer.")
    mock.add_response("Implementation: def x(): pass")
    # Then summarization:
    mock.add_response("Summary: We researched and implemented X.")

    hermes, _ = _build_hermes(mock)
    result = hermes.dispatch(Task(content="research and implement X"))
    assert result["mode"] == "multi"
    assert len(result["steps"]) == 2
    assert "Summary" in result["content"]
    assert "research" in result["content"].lower() or "implement" in result["content"].lower()


def test_hermes_passes_context_between_steps():
    """In multi-mode, step 2 should receive step 1's result as context."""
    mock = MockLLMClient()
    mock.add_response(
        '{"type": "multi", "steps": ['
        '{"role": "athena", "task": "research"},'
        '{"role": "hephaestus", "task": "implement"}'
        ']}'
    )
    mock.add_response("Finding: use async")
    mock.add_response("async def f(): pass")
    mock.add_response("Summary.")

    hermes, _ = _build_hermes(mock)
    hermes.dispatch(Task(content="build it"))

    # 3 LLM calls: planner, athena, hephaestus, summarizer = 4 calls total
    # The 3rd call is Hephaestus's, and its user message should contain
    # "async" (Athena's result)
    assert len(mock.calls) >= 3
    hephaestus_call = mock.calls[2]
    user_msg = hephaestus_call["messages"][0]["content"]
    assert "Finding" in user_msg or "async" in user_msg


def test_hermes_skips_unknown_role_in_multi_plan():
    """When the planner returns an unknown role, the Router filters it out.

    Hermes only executes known roles; unknown ones are silently dropped.
    """
    mock = MockLLMClient()
    mock.add_response(
        '{"type": "multi", "steps": ['
        '{"role": "ghost", "task": "x"},'
        '{"role": "athena", "task": "y"}'
        ']}'
    )
    mock.add_response("research done")
    mock.add_response("summary")
    hermes, _ = _build_hermes(mock)
    result = hermes.dispatch(Task(content="anything"))
    assert result["mode"] == "multi"
    # Only the known role (athena) should have been executed;
    # the unknown one was filtered out by the Router.
    executed_roles = {s.role for s in result["steps"]}
    assert "ghost" not in executed_roles
    assert "athena" in executed_roles


def test_hermes_role_descriptions():
    mock = MockLLMClient()
    hermes, roles = _build_hermes(mock)
    descs = hermes._role_descriptions()
    assert "hephaestus" in descs
    assert "athena" in descs
    assert "apollo" in descs
    # Chronos wasn't registered
    assert "chronos" not in descs
