from __future__ import annotations

import json
import logging
from io import StringIO
from types import SimpleNamespace

from rich.console import Console

import pantheon.cli as cli
from pantheon.core.base import TaskResult


def _capture_console(monkeypatch) -> StringIO:
    stream = StringIO()
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=stream, width=80, color_system=None, force_terminal=False),
    )
    return stream


def test_council_header_uses_large_temple_on_wide_terminals(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=stream, width=120, color_system=None, force_terminal=False),
    )

    cli.console.print(
        cli._brand_header(
            "COUNCIL",
            "Hermes routes the task; specialist agents execute",
            ["model test-model", "cwd workspace"],
            hero=True,
        )
    )

    output = stream.getvalue()
    assert "__||_|__|__|__|_||__" in output
    assert "PANTHEON  COUNCIL" in output


def test_council_header_keeps_large_temple_at_standard_width(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=stream, width=80, color_system=None, force_terminal=False),
    )

    cli.console.print(
        cli._brand_header(
            "COUNCIL",
            "Hermes routes the task; specialist agents execute",
            ["model test-model", "cwd workspace"],
            hero=True,
        )
    )

    output = stream.getvalue()
    assert "__||_|__|__|__|_||__" in output
    assert "ROUTE  →  EXECUTE  →  SYNTHESIZE" in output


def test_cli_hides_dependency_request_logs_unless_verbose() -> None:
    names = ("httpx", "httpcore", "openai", "anthropic")
    previous_levels = {name: logging.getLogger(name).level for name in names}
    try:
        for name in names:
            logging.getLogger(name).setLevel(logging.INFO)

        cli._configure_cli_logging(verbose=True)
        assert all(logging.getLogger(name).level == logging.INFO for name in names)

        cli._configure_cli_logging(verbose=False)
        assert all(logging.getLogger(name).level == logging.WARNING for name in names)
    finally:
        for name, level in previous_levels.items():
            logging.getLogger(name).setLevel(level)


def test_roles_render_compact_roster(monkeypatch) -> None:
    role = SimpleNamespace(
        model="test-model",
        description="Builds software",
        config={"provider": "openai", "description": "Builds software"},
    )
    pantheon = SimpleNamespace(
        router=SimpleNamespace(hermes_model="router-model"),
        list_roles=lambda: ["hephaestus"],
        get_role=lambda name: role,
    )
    monkeypatch.setattr(cli, "Pantheon", lambda config_path=None: pantheon)
    stream = _capture_console(monkeypatch)

    cli.list_roles(config=None)

    output = stream.getvalue()
    assert "🏛" in output
    assert "PANTHEON  ROSTER" in output
    assert "Hephaestus" in output
    assert "test-model" in output
    assert "Builds software" in output


def test_ask_raw_output_remains_machine_readable(monkeypatch) -> None:
    pantheon = SimpleNamespace(
        router=SimpleNamespace(hermes_model="router-model"),
        ask=lambda task, mode, skill, on_event=None: {
            "mode": mode,
            "plan": "",
            "content": "done",
            "steps": [],
        },
    )
    monkeypatch.setattr(
        cli,
        "Pantheon",
        lambda config_path=None, verbose=False: pantheon,
    )
    stream = _capture_console(monkeypatch)
    echoed: list[str] = []
    monkeypatch.setattr(cli.typer, "echo", echoed.append)

    cli.ask(
        task="test task",
        role=None,
        multi=False,
        skill=None,
        config=None,
        raw=True,
        verbose=False,
    )

    assert stream.getvalue() == ""
    assert json.loads(echoed[0]) == {
        "mode": "auto",
        "plan": "",
        "content": "done",
        "steps": [],
    }


def test_ask_renders_session_steps_and_answer(monkeypatch) -> None:
    def fake_ask(task, mode, skill, on_event=None):
        if on_event:
            on_event(
                "plan_ready",
                {
                    "mode": "multi",
                    "steps": [{"role": "hephaestus"}, {"role": "athena"}],
                },
            )
            on_event(
                "step_start",
                {
                    "index": 0,
                    "total": 2,
                    "role": "hephaestus",
                    "description": "Implement the change",
                },
            )
            on_event(
                "step_done",
                {
                    "role": "hephaestus",
                    "success": True,
                    "duration_ms": 1250,
                },
            )
            on_event(
                "agent_message",
                {
                    "from_role": "hephaestus",
                    "to_role": "athena",
                    "summary": "Implementation ready for verification",
                },
            )
            on_event("summary_start", {"role": "hermes"})
        return {
            "mode": mode,
            "plan": "Use Hephaestus, then Athena.",
            "content": "## Recommendation\n\nShip the verified change.",
            "steps": [
                TaskResult(
                    role="hephaestus",
                    content="Implemented the change.",
                    duration_ms=1250,
                ),
                TaskResult(
                    role="athena",
                    content="Verified the behavior.",
                    duration_ms=640,
                ),
            ],
        }

    pantheon = SimpleNamespace(
        router=SimpleNamespace(hermes_model="router-model"),
        ask=fake_ask,
    )
    monkeypatch.setattr(
        cli,
        "Pantheon",
        lambda config_path=None, verbose=False: pantheon,
    )
    stream = _capture_console(monkeypatch)

    cli.ask(
        task="Build and verify the feature",
        role=None,
        multi=True,
        skill=None,
        config=None,
        raw=False,
        verbose=False,
    )

    output = stream.getvalue()
    assert "PANTHEON  COUNCIL" in output
    assert "council formed with 2 steps" in output
    assert "Implementation ready for verification" in output
    assert "Hermes plan" in output
    assert "Hephaestus" in output
    assert "Athena" in output
    assert "Recommendation" in output
    assert "2/2 steps" in output
