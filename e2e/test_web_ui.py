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


def test_update_banner_dismissal(page: Page, live_server_url: str) -> None:
    page.route('**/api/update', lambda route: route.fulfill(json={
        'current_version': '0.2.3', 'latest_version': 'v99.0.0', 'update_available': True,
        'release_url': 'https://github.com/RyosukeSAMA/github-ai/releases/tag/v99.0.0',
    }))
    page.goto(live_server_url)
    expect(page.locator('#update-banner')).to_be_visible()
    page.locator('#update-banner-dismiss').click()
    page.reload()
    expect(page.locator('#update-banner')).to_be_hidden()


def test_chat_archive_delete_and_stale_tab(page: Page, live_server_url: str) -> None:
    current = page.request.get(f'{live_server_url}/api/conversations').json()
    chat = {'id': 'e2e-cleanup', 'title': 'Cleanup test', 'mode': 'auto', 'overrides': {},
            'createdAt': 1, 'updatedAt': 1, 'messages': []}
    saved = page.request.put(f'{live_server_url}/api/conversations', data={
        'schema_version': 1, 'expected_revision': current['revision'], 'sessions': current['sessions'] + [chat],
    }).json()
    page.goto(live_server_url)
    row = page.locator('.conversation-row').filter(has=page.locator('[data-session="e2e-cleanup"]'))
    expect(row).to_be_visible()
    row.get_by_role('button', name='Archive conversation', exact=True).click()
    expect(page.locator('[data-session="e2e-cleanup"]')).to_have_count(0)
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="info"]').click()
    page.locator('#info-conversation-archive').click()
    expect(page.locator('[data-session="e2e-cleanup"]')).to_be_visible()
    page.on('dialog', lambda dialog: dialog.accept())
    row.get_by_role('button', name='Delete Cleanup test', exact=True).click()
    expect(page.locator('[data-session="e2e-cleanup"]')).to_have_count(0)
    latest = page.request.get(f'{live_server_url}/api/conversations').json()
    resurrect = page.request.put(f'{live_server_url}/api/conversations', data={
        'schema_version': 1, 'expected_revision': latest['revision'], 'sessions': saved['sessions'],
    }).json()
    assert not any(item['id'] == 'e2e-cleanup' for item in resurrect['sessions'])


def test_conflicting_transcripts_are_preserved_and_save_errors_visible(page: Page, live_server_url: str) -> None:
    local = {'id': 'conflict-chat', 'title': 'Local branch', 'mode': 'auto', 'overrides': {},
             'createdAt': 1, 'updatedAt': 3, 'messages': [{'role': 'user', 'text': 'Local edit'}]}
    remote = {**local, 'title': 'Remote branch', 'updatedAt': 2,
              'messages': [{'role': 'user', 'text': 'Remote edit'}]}
    page.add_init_script(f"localStorage.setItem('pantheon:chat-sessions', {json.dumps(json.dumps([local]))});")

    def conversations(route):
        if route.request.method == 'PUT':
            route.fulfill(status=400, json={'detail': 'Conversations exceed 10 MB'})
        else:
            route.fulfill(json={'schema_version': 1, 'revision': 'test-revision', 'sessions': [remote]})

    page.route('**/api/conversations', conversations)
    page.goto(live_server_url)
    expect(page.locator('#chat-list .chat-row')).to_have_count(2)
    expect(page.locator('#chat-list')).to_contain_text('Conflict copy: Remote branch')
    expect(page.locator('.conversation-save-notice')).to_contain_text('Conversations exceed 10 MB')
    assert 'Local edit' in page.locator('#chat').inner_text()


def test_task_history_can_stop_a_running_task(page: Page, live_server_url: str) -> None:
    stopped = []
    def history(route):
        route.fulfill(status=200, content_type='application/json', body=json.dumps({'tasks': [
            {'id': 'task-demo', 'status': 'running', 'cancel': bool(stopped), 'data': {'task': 'Research a topic'}}
        ]}))
    def stop(route):
        stopped.append(True)
        route.fulfill(status=200, content_type='application/json', body='{"stop_requested": true}')
    page.route('**/api/tasks', history)
    page.route('**/api/tasks/task-demo/stop', stop)
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="info"]').click()
    expect(page.locator('#info-tasks-list')).to_contain_text('Research a topic')
    page.locator('#info-tasks-list button').click()
    expect(page.locator('#info-tasks-list button')).to_have_text('Stop requested')
    expect(page.locator('#info-tasks-list button')).to_be_disabled()


def test_model_catalog_updates_on_focus_without_overwriting_setup_draft(page: Page, live_server_url: str):
    changed = False
    def status(route):
        response = route.fetch()
        payload = response.json()
        if changed:
            provider = next(p for p in payload['providers'] if p['id'] == 'openai')
            provider['models'].append({'id': 'gpt-future-release', 'label': 'Future release', 'source': 'available', 'available': True})
        route.fulfill(response=response, json=payload)
    page.route('**/api/setup/status', status)
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('#setup-provider').select_option('openai')
    page.locator('#setup-model').select_option('gpt-6.1-sol')
    page.locator('#setup-api-key').fill('unsaved-test-key')
    page.locator('#setup-base-url').fill('https://draft.example/v1')
    changed = True
    page.evaluate('window.dispatchEvent(new Event("focus"))')
    expect(page.locator('#setup-model option[value="gpt-future-release"]')).to_have_count(1)
    expect(page.locator('#setup-model')).to_have_value('gpt-6.1-sol')
    expect(page.locator('#setup-api-key')).to_have_value('unsaved-test-key')
    expect(page.locator('#setup-base-url')).to_have_value('https://draft.example/v1')
