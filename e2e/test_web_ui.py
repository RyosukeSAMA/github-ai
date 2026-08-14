from __future__ import annotations

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
