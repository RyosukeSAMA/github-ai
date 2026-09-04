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


def test_router_preserves_only_skills_allowed_for_selected_role():
    mock = MockLLMClient()
    mock.add_response(
        '{"type": "single", "role": "hephaestus", '
        '"skill": "fix-and-verify", "reasoning": "code"}'
    )
    router = Router(llm_client=mock, hermes_model="mock")
    plan = router.plan(
        "Fix this bug",
        {
            "hephaestus": {
                "description": "code",
                "skills": [{"id": "fix-and-verify", "description": "fix bugs"}],
            },
        },
        requested_skill="fix-and-verify",
    )

    assert plan.single_skill == "fix-and-verify"
    assert "$fix-and-verify" in mock.calls[0]["messages"][0]["content"]


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


def test_router_parses_structured_collaboration_fields():
    mock = MockLLMClient()
    mock.add_response("""
{
  "type": "multi",
  "reasoning": "research then review",
  "steps": [
    {
      "role": "athena",
      "kind": "work",
      "task": "research X",
      "depends_on": [],
      "deliverable": "A sourced research brief",
      "acceptance_criteria": ["Includes two sources", "Separates facts from inference"]
    },
    {
      "role": "hephaestus",
      "kind": "review",
      "task": "review the brief",
      "depends_on": [1, 1, 2, "bad"],
      "deliverable": "A pass or concrete corrections",
      "acceptance_criteria": ["Checks every requirement"]
    }
  ]
}
""")
    router = Router(llm_client=mock, hermes_model="mock")

    plan = router.plan("Research and review", {"athena": {}, "hephaestus": {}})

    assert plan.steps[0].kind == "work"
    assert plan.steps[0].depends_on == []
    assert plan.steps[0].deliverable == "A sourced research brief"
    assert plan.steps[0].acceptance_criteria == [
        "Includes two sources",
        "Separates facts from inference",
    ]
    assert plan.steps[1].kind == "review"
    assert plan.steps[1].depends_on == [1]
    assert plan.steps[1].deliverable == "A pass or concrete corrections"


def test_router_defaults_legacy_multi_steps_to_sequential_handoffs():
    mock = MockLLMClient()
    mock.add_response(
        '{"type": "multi", "steps": ['
        '{"role": "athena", "task": "research"},'
        '{"role": "hephaestus", "task": "build"}'
        "]}"
    )
    router = Router(llm_client=mock)

    plan = router.plan("Research and build", {"athena": {}, "hephaestus": {}})

    assert plan.steps[0].kind == "work"
    assert plan.steps[0].depends_on == []
    assert plan.steps[1].kind == "work"
    assert plan.steps[1].depends_on == [1]


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
    assert "2-4 numbered choices" in user_msg
    assert "practical suggestion to every choice" in user_msg
    assert "reply with that option number" in user_msg
    assert "do not end\nwith vague examples" in user_msg


def test_router_summarize_empty_context_returns_empty():
    mock = MockLLMClient()
    r = Router(llm_client=mock)
    assert r.summarize("anything", []) == ""
    # No LLM call made
    assert len(mock.calls) == 0


def test_router_enhance_prompt_preserves_draft_and_strips_wrappers():
    mock = MockLLMClient()
    mock.add_response("```text\n请比较 PostgreSQL 与 MongoDB，并给出选型建议。\n```")
    router = Router(llm_client=mock, hermes_model="hermes-model")

    enhanced = router.enhance_prompt("比较 PG 和 Mongo", mode="multi")

    assert enhanced == "请比较 PostgreSQL 与 MongoDB，并给出选型建议。"
    assert mock.calls[0]["model"] == "hermes-model"
    assert mock.calls[0]["temperature"] == 0.2
    assert "<draft>\n比较 PG 和 Mongo\n</draft>" in mock.calls[0]["messages"][0]["content"]
    assert "multiple objectives" in mock.calls[0]["messages"][0]["content"]
    assert "Do not answer the task" in mock.calls[0]["system"]


def test_router_enhance_prompt_rejects_empty_draft():
    router = Router(llm_client=MockLLMClient())

    try:
        router.enhance_prompt("   ")
    except ValueError as exc:
        assert str(exc) == "prompt is required"
    else:
        raise AssertionError("empty prompts must be rejected")
