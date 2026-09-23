from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import Page, expect


def test_core_navigation_and_conversation_state(page: Page, live_server_url: str) -> None:
    page.goto(live_server_url)

    expect(page.locator(".brand-text h1")).to_have_text("Pantheon")
    expect(page.locator("#chat-list .chat-row")).to_have_count(1)
    expect(page.locator("#provider-name")).not_to_have_text("connecting…")

    page.locator('[data-mode="multi"]').click()
    expect(page.locator("#topbar-mode-name")).to_have_text("Multi-role")
    expect(page.locator("#mode-display")).to_contain_text("Multi-role")

    page.locator("#new-chat-btn").click()
    expect(page.locator("#chat-list .chat-row")).to_have_count(2)
    expect(page.locator("#chat-list .chat-row.active .chat-row-title")).to_have_text("New chat")
    expect(page.locator("#topbar-mode-name")).to_have_text("Auto")

    page.locator("#toggle-workspace").click()
    expect(page.locator("#workspace")).to_be_visible()
    expect(page.locator("#settings-panel")).to_be_hidden()

    page.locator("#toggle-settings").click()
    expect(page.locator("#settings-panel")).to_be_visible()
    expect(page.locator("#workspace")).to_be_hidden()


def test_openai_setup_lists_gpt6_astra(
    page: Page,
    live_server_url: str,
) -> None:
    page.goto(live_server_url)
    page.locator("#toggle-settings").click()

    expect(page.locator('#setup-provider option[value="openai"]')).to_have_count(1)
    expect(page.locator('#setup-model option[value="gpt-6-astra"]')).to_have_text(
        "GPT-6 Astra"
    )


def test_prompt_enhancement_rewrites_draft_without_sending(
    page: Page,
    live_server_url: str,
) -> None:
    page.route(
        "**/api/prompt/enhance",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "prompt": "Build a responsive profile page with semantic HTML.",
            }),
        ),
    )
    page.goto(live_server_url)
    original = "make profile page"
    page.locator("#input").fill(original)

    page.locator("#enhance-prompt-btn").click()

    expect(page.locator("#input")).to_have_value(
        "Build a responsive profile page with semantic HTML."
    )
    expect(page.locator("#enhance-prompt-btn")).to_have_attribute(
        "aria-label", "Undo prompt enhancement"
    )
    expect(page.locator("#welcome")).to_be_visible()

    page.locator("#enhance-prompt-btn").click()
    expect(page.locator("#input")).to_have_value(original)
    expect(page.locator("#enhance-prompt-btn")).to_have_attribute(
        "aria-label", "Enhance prompt with the configured Hermes model"
    )


def test_workspace_file_opens_in_preview(
    page: Page,
    live_server_url: str,
    e2e_workspace: Path,
) -> None:
    (e2e_workspace / "demo.html").write_text(
        "<!doctype html><html><body><h1>Pantheon E2E</h1></body></html>",
        encoding="utf-8",
    )
    page.goto(live_server_url)
    page.locator("#toggle-workspace").click()
    page.locator('[data-ws-tab="files"]').click()

    file_row = page.locator('#ws-files [data-path="demo.html"]')
    expect(file_row).to_be_visible()
    file_row.click()

    expect(page.locator('[data-ws-tab="preview"]')).to_have_class(
        re.compile(r"(?:^|\s)active(?:\s|$)")
    )
    expect(page.locator("#ws-preview-status")).to_contain_text("demo.html")
    expect(page.frame_locator("#ws-preview-frame").locator("h1")).to_have_text("Pantheon E2E")


def test_structured_agent_handoffs_render_in_activity(
    page: Page,
    live_server_url: str,
) -> None:
    events = [
        ("start", {"task": "Research and review X", "mode": "multi"}),
        (
            "plan",
            {
                "plan": "Research first, then review the result.",
                "mode": "multi",
                "steps": [
                    {
                        "index": 0,
                        "total": 2,
                        "role": "athena",
                        "kind": "work",
                        "task": "Research X",
                        "depends_on": [],
                        "deliverable": "A sourced brief",
                        "acceptance_criteria": ["Includes reliable evidence"],
                        "skills": [],
                    },
                    {
                        "index": 1,
                        "total": 2,
                        "role": "hephaestus",
                        "kind": "review",
                        "task": "Review the brief",
                        "depends_on": [1],
                        "deliverable": "A pass or concrete corrections",
                        "acceptance_criteria": ["Checks the original request"],
                        "skills": [],
                    },
                ],
            },
        ),
        (
            "step_start",
            {"index": 0, "total": 2, "role": "athena", "task": "Research X"},
        ),
        (
            "step_done",
            {
                "index": 0,
                "total": 2,
                "role": "athena",
                "content": "Research complete.",
                "duration_ms": 20,
                "success": True,
            },
        ),
        (
            "agent_message",
            {
                "message_id": "result-1",
                "type": "result",
                "from_role": "athena",
                "to_role": "hermes",
                "summary": "A sourced brief",
                "step_index": 1,
            },
        ),
        (
            "agent_message",
            {
                "message_id": "review-1",
                "type": "review_request",
                "from_role": "athena",
                "to_role": "hephaestus",
                "summary": "A sourced brief",
                "step_index": 2,
                "target_step_index": 1,
                "deliverable": "A pass or concrete corrections",
                "acceptance_criteria": ["Checks the original request"],
            },
        ),
        (
            "step_start",
            {
                "index": 1,
                "total": 2,
                "role": "hephaestus",
                "task": "Review the brief",
            },
        ),
        (
            "step_done",
            {
                "index": 1,
                "total": 2,
                "role": "hephaestus",
                "content": "Review passed.",
                "duration_ms": 15,
                "success": True,
            },
        ),
        (
            "agent_message",
            {
                "message_id": "result-2",
                "type": "result",
                "from_role": "hephaestus",
                "to_role": "athena",
                "summary": "A pass or concrete corrections",
                "step_index": 2,
            },
        ),
        ("summary_start", {"role": "hermes", "task": "Synthesize final answer"}),
        ("summary_done", {"role": "hermes", "content": "Final answer."}),
        ("done", {"mode": "multi", "content": "Final answer."}),
    ]
    body = "".join(
        f"event: {event}\ndata: {json.dumps(data)}\n\n"
        for event, data in events
    )
    page.route(
        "**/api/ask/stream",
        lambda route: route.fulfill(
            status=200,
            content_type="text/event-stream",
            body=body,
        ),
    )

    page.goto(live_server_url)
    page.locator('[data-mode="multi"]').click()
    page.locator("#toggle-workspace").click()
    page.locator("#input").fill("Research and review X")
    page.locator("#send-btn").click()

    expect(page.locator("#ws-plan .ws-plan-kind")).to_have_text(["Work", "Review"])
    expect(page.locator("#ws-plan .ws-plan-deps")).to_have_text("after #1")
    messages = page.locator("#ws-steps .ws-agent-message")
    expect(messages).to_have_count(3)
    expect(messages.nth(1)).to_contain_text("Athena → Hephaestus")
    expect(messages.nth(1)).to_contain_text("review request")
    expect(messages.nth(1)).to_contain_text("A pass or concrete corrections")
