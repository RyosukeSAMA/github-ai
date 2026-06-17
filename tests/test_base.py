"""Tests for base classes (Task, Plan, Role)."""

import pytest

from pantheon.core.base import Plan, PlanStep, Role, Task, TaskResult, time_ms


def test_task_validates_mode():
    t = Task(content="hi", mode="auto")
    assert t.mode == "auto"

    t2 = Task(content="hi", mode="role:hephaestus")
    assert t2.mode == "role:hephaestus"

    t3 = Task(content="hi", mode="multi")
    assert t3.mode == "multi"

    with pytest.raises(ValueError):
        Task(content="hi", mode="invalid-mode")


def test_task_generates_id():
    t1 = Task(content="hi")
    t2 = Task(content="hi")
    # IDs should be unique (8-char UUID prefix)
    assert t1.task_id != t2.task_id
    assert len(t1.task_id) == 8


def test_plan_single():
    p = Plan.single("hephaestus", reasoning="code task")
    assert p.is_single_role is True
    assert p.single_role == "hephaestus"


def test_plan_multi():
    steps = [
        PlanStep(role="athena", task="research", description="step 1"),
        PlanStep(role="hephaestus", task="write code", description="step 2"),
    ]
    p = Plan.multi(steps, reasoning="complex")
    assert p.is_single_role is False
    assert len(p.steps) == 2
    assert p.steps[0].role == "athena"


def test_role_requires_name():
    class BadRole(Role):
        # Missing name
        description = "x"

        def run(self, task, context=None):
            return TaskResult(role="bad", content="")

    with pytest.raises(ValueError, match="must define `name`"):
        BadRole(llm_client=None)


def test_task_result_defaults():
    r = TaskResult(role="foo", content="bar")
    assert r.success is True
    assert r.error is None
    assert r.duration_ms >= 0


def test_time_ms_returns_int():
    t = time_ms()
    assert isinstance(t, int)
    assert t > 0


def test_role_default_system_prompt():
    class MyRole(Role):
        name = "myrole"
        description = "does things"

        def run(self, task, context=None):
            return TaskResult(role="myrole", content="")

    r = MyRole(llm_client=None)
    assert "myrole" in r.system_prompt
    assert "does things" in r.system_prompt


def test_role_format_context_empty():
    class MyRole(Role):
        name = "x"
        description = "x"

        def run(self, task, context=None):
            return TaskResult(role="x", content="")

    r = MyRole(llm_client=None)
    assert r._format_context(None) == ""
    assert r._format_context([]) == ""


def test_role_format_context_with_steps():
    class MyRole(Role):
        name = "x"
        description = "x"

        def run(self, task, context=None):
            return TaskResult(role="x", content="")

    r = MyRole(llm_client=None)
    ctx = [
        {"step": "first", "role": "athena", "result": "found X"},
        {"step": "second", "role": "hephaestus", "result": "built Y"},
    ]
    out = r._format_context(ctx)
    assert "first" in out
    assert "athena" in out
    assert "hephaestus" in out
