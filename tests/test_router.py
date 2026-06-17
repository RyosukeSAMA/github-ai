"""Tests for the Router (planner)."""


from pantheon.core.router import Router
from tests.conftest import MockLLMClient


def test_router_parses_single_plan():
    mock = MockLLMClient()
    mock.add_response('{"type": "single", "role": "hephaestus", "reasoning": "code"}')
    r = Router(llm_client=mock, hermes_model="mock")
    plan = r.plan("Write a function", {"hephaestus": {"description": "code"}})
    assert plan.is_single_role is True
    assert plan.single_role == "hephaestus"


def test_router_parses_multi_plan():
    mock = MockLLMClient()
    mock.add_response("""
{
  "type": "multi",
  "reasoning": "complex",
  "steps": [
    {"role": "athena", "task": "research X", "description": "first"},
    {"role": "hephaestus", "task": "build Y", "description": "second"}
  ]
}
""")
    r = Router(llm_client=mock, hermes_model="mock")
    plan = r.plan("Research and build", {"athena": {}, "hephaestus": {}})
    assert plan.is_single_role is False
    assert len(plan.steps) == 2
    assert plan.steps[0].role == "athena"
    assert plan.steps[1].role == "hephaestus"


def test_router_handles_invalid_json_fallback():
    mock = MockLLMClient()
    mock.add_response("not json at all, just rambling")
    r = Router(llm_client=mock)
    plan = r.plan("something", {"athena": {}, "hephaestus": {}})
    assert plan.is_single_role is True
    assert plan.single_role in ("athena", "hephaestus")  # fallback


def test_router_handles_unknown_role_in_single():
    mock = MockLLMClient()
    mock.add_response('{"type": "single", "role": "nonexistent", "reasoning": ""}')
    r = Router(llm_client=mock)
    plan = r.plan("anything", {"athena": {}, "hephaestus": {}})
    # Should fall back to a known role
    assert plan.single_role in ("athena", "hephaestus")


def test_router_handles_unknown_role_in_multi():
    mock = MockLLMClient()
    mock.add_response("""
{
  "type": "multi",
  "steps": [
    {"role": "ghost", "task": "x"},
    {"role": "athena", "task": "y"}
  ]
}
""")
    r = Router(llm_client=mock)
    plan = r.plan("anything", {"athena": {}, "hephaestus": {}})
    # Unknown role is skipped; only known ones remain
    assert len(plan.steps) == 1
    assert plan.steps[0].role == "athena"


def test_router_handles_empty_steps_fallback():
    mock = MockLLMClient()
    mock.add_response('{"type": "multi", "steps": [{"role": "ghost", "task": "x"}]}')
    r = Router(llm_client=mock)
    plan = r.plan("anything", {"athena": {}, "hephaestus": {}})
    # All steps had unknown roles → fallback to single
    assert plan.is_single_role is True


def test_router_extracts_json_from_prose():
    mock = MockLLMClient()
    mock.add_response(
        "Sure, here's the plan:\n"
        '{"type": "single", "role": "apollo", "reasoning": "creative"}\n'
        "Hope this helps!"
    )
    r = Router(llm_client=mock)
    plan = r.plan("write a poem", {"apollo": {}})
    assert plan.is_single_role is True
    assert plan.single_role == "apollo"


def test_router_handles_json_fence():
    mock = MockLLMClient()
    mock.add_response(
        '```json\n{"type": "single", "role": "apollo"}\n```'
    )
    r = Router(llm_client=mock)
    plan = r.plan("song lyrics", {"apollo": {}})
    assert plan.single_role == "apollo"


def test_router_summarize_calls_llm():
    mock = MockLLMClient()
    mock.add_response("Final answer.")
    r = Router(llm_client=mock)
    summary = r.summarize(
        "research X",
        [
            {"step": "s1", "role": "athena", "result": "r1"},
            {"step": "s2", "role": "hephaestus", "result": "r2"},
        ],
    )
    assert summary == "Final answer."
    assert len(mock.calls) == 1
    user_msg = mock.calls[0]["messages"][0]["content"]
    assert "research X" in user_msg
    assert "athena" in user_msg
    assert "r1" in user_msg


def test_router_summarize_empty_context_returns_empty():
    mock = MockLLMClient()
    r = Router(llm_client=mock)
    assert r.summarize("anything", []) == ""
    # No LLM call made
    assert len(mock.calls) == 0
