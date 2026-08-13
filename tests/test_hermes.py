"""Tests for Hermes (orchestrator) end-to-end dispatching."""


from pathlib import Path

from pantheon.core.base import Task
from pantheon.core.extensions import SkillStore
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


def test_hermes_injects_role_scoped_memory():
    mock = MockLLMClient()
    mock.add_response("code result")
    hermes, _ = _build_hermes(mock)

    def memory_provider(content, role):
        assert content == "build it"
        if role == "hephaestus":
            return (
                "Relevant memories:\n"
                "- [user_profile/global] prefer Chinese\n"
                "- [agent/hephaestus] keep existing architecture",
                [
                    {"id": "global-1", "role": "", "content": "prefer Chinese"},
                    {"id": "he-1", "role": "hephaestus", "content": "keep existing architecture"},
                ],
            )
        return "", []

    hermes.memory_context_provider = memory_provider
    result = hermes.dispatch(Task(content="build it", mode="role:hephaestus"))

    assert result["memory_matches"] == [
        {"id": "global-1", "role": "", "content": "prefer Chinese"},
        {"id": "he-1", "role": "hephaestus", "content": "keep existing architecture"},
    ]
    user_msg = mock.calls[0]["messages"][0]["content"]
    assert "prefer Chinese" in user_msg
    assert "keep existing architecture" in user_msg


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


def test_hermes_reports_multi_role_progress_before_each_call():
    mock = MockLLMClient()
    mock.add_response(
        '{"type": "multi", "reasoning": "research then build", '
        '"steps": ['
        '{"role": "athena", "task": "research X"},'
        '{"role": "hephaestus", "task": "implement X"}'
        ']}'
    )
    mock.add_response("Research complete.")
    mock.add_response("Implementation complete.")
    mock.add_response("Final synthesis.")
    hermes, _ = _build_hermes(mock)
    events: list[tuple[str, dict]] = []

    result = hermes.dispatch(
        Task(content="research and implement X", mode="multi"),
        on_event=lambda event, data: events.append((event, data)),
    )

    names = [event for event, _ in events]
    assert names == [
        "plan_start",
        "plan_ready",
        "step_start",
        "step_done",
        "step_start",
        "step_done",
        "summary_start",
        "summary_done",
    ]
    plan = events[1][1]
    assert [step["role"] for step in plan["steps"]] == ["athena", "hephaestus"]
    assert events[2][1]["index"] == 0
    assert events[2][1]["total"] == 2
    assert events[4][1]["index"] == 1
    assert result["content"] == "Final synthesis."


def test_multi_mode_forces_council_when_router_returns_single():
    mock = MockLLMClient()
    mock.add_response('{"type": "single", "role": "hephaestus", "reasoning": "code"}')
    mock.add_response("Research framing")
    mock.add_response("Implementation detail")
    mock.add_response("Creative review")
    mock.add_response("Council summary")

    hermes, _ = _build_hermes(mock)
    result = hermes.dispatch(Task(content="build and polish this", mode="multi"))

    assert result["mode"] == "multi"
    assert len(result["steps"]) >= 2
    assert "Council summary" in result["content"]


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


def test_hermes_multi_steps_keep_original_request_and_structure_confirmations():
    mock = MockLLMClient()
    mock.add_response(
        '{"type": "multi", "steps": ['
        '{"role": "athena", "task": "analyze inputs and edge cases"},'
        '{"role": "apollo", "task": "design the interface"}'
        ']}'
    )
    mock.add_response("Analysis complete")
    mock.add_response("Design complete")
    mock.add_response("Summary")

    original = "Build a subscription calculator for a local AI product"
    hermes, _ = _build_hermes(mock)
    hermes.dispatch(Task(content=original, mode="multi"))

    for call in mock.calls[1:3]:
        prompt = call["messages"][0]["content"]
        assert f"Original user request:\n{original}" in prompt
        assert "1. <choice> - Suggestion:" in prompt
        assert "2. <choice> - Suggestion:" in prompt
        assert "3. <optional choice> - Suggestion:" in prompt
        assert "Provide 2-4 concrete numbered options" in prompt
        assert "Do not perform the dependent action" in prompt

    assert "Your assigned step:\nanalyze inputs and edge cases" in (
        mock.calls[1]["messages"][0]["content"]
    )
    assert "Your assigned step:\ndesign the interface" in (
        mock.calls[2]["messages"][0]["content"]
    )


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


def test_explicit_role_skill_routes_without_planner_and_records_match(tmp_path):
    mock = MockLLMClient()
    mock.add_response("fixed and verified")
    hermes, _ = _build_hermes(mock)
    builtins = Path(__file__).resolve().parents[1] / "pantheon" / "skills"
    store = SkillStore(tmp_path / "skills", builtin_path=builtins)
    hermes.skill_context_provider = store.context_block
    hermes.skill_catalog_provider = store.catalog_for_roles
    hermes.skill_lookup_provider = store.get

    result = hermes.dispatch(Task(
        content="修复这个 bug 并验证",
        skill="fix-and-verify",
    ))

    assert result["steps"][0].role == "hephaestus"
    assert result["skill_matches"][0]["id"] == "fix-and-verify"
    assert result["skill_matches"][0]["invocation"] == "explicit"
    assert "Fix and Verify" in mock.calls[0]["messages"][0]["content"]
