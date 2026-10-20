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


def test_getting_started_can_reopen_and_prepare_without_sending(page: Page, live_server_url: str) -> None:
    requests = []
    page.on('request', lambda request: requests.append(request.url))
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('#guide-reopen').click()
    expect(page.locator('#onboarding-card')).to_be_visible()
    page.locator('[data-guide-action="confirm_workspace"]').click()
    expect(page.locator('#onboarding-steps li').first).to_have_class('done')
    expect(page.locator('#setup-status-title')).to_contain_text('configured')
    page.locator('#guide-first-task').click()
    expect(page.locator('#settings-panel')).to_be_hidden()
    expect(page.locator('#input')).to_have_value(re.compile('Explain which Pantheon agent'))
    assert not any('/api/setup/test' in url or '/api/ask' in url for url in requests)
    page.locator('#toggle-settings').click()
    page.locator('[data-guide-action="skip"]').click()
    expect(page.locator('#onboarding-card')).to_be_hidden()


def test_task_checkpoint_resume_uses_stream_and_retains_current_overrides(page: Page, live_server_url: str) -> None:
    requests = []
    task = {'id': 'checkpoint-task', 'status': 'partial_failure', 'data': {'task': 'Complete the saved plan',
            'mode': 'multi', 'recoverable': True, 'archive_available': True}, 'updated': 1}
    page.route('**/api/tasks', lambda route: route.fulfill(json={'tasks': [task]}))
    def resume(route):
        requests.append(route.request.post_data_json)
        events = [('phase', {'stage': 'executing', 'task_id': 'resume-task', 'role': 'athena'}),
                  ('step_start', {'index': 0, 'role': 'athena', 'total': 1}),
                  ('step_done', {'index': 0, 'role': 'athena', 'content': 'Retained research', 'reused': True, 'success': True}),
                  ('done', {'status': 'completed', 'success': True})]
        body = ''.join(f'event: {event}\ndata: {json.dumps(data)}\n\n' for event, data in events)
        route.fulfill(content_type='text/event-stream', body=body)
    page.route('**/api/ask/stream', resume)
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="info"]').click()
    expect(page.locator('#info-tasks-list')).to_contain_text('Resume failed steps')
    page.get_by_role('button', name='Resume failed steps').click()
    expect(page.locator('#chat')).to_contain_text('Retained research')
    assert requests[0]['resume_task_id'] == 'checkpoint-task'
    assert 'overrides' not in requests[0]


def test_parallel_results_finish_out_of_order_in_their_own_blocks(page: Page, live_server_url: str) -> None:
    events = [('step_start', {'index': 0, 'total': 2, 'role': 'athena', 'task': 'Research'}),
              ('step_start', {'index': 1, 'total': 2, 'role': 'apollo', 'task': 'Draft'}),
              ('step_chunk', {'index': 1, 'role': 'apollo', 'text': 'Apollo independent draft'}),
              ('step_done', {'index': 1, 'role': 'apollo', 'content': 'Apollo independent draft', 'success': True}),
              ('step_chunk', {'index': 0, 'role': 'athena', 'text': 'Athena independent research'}),
              ('step_done', {'index': 0, 'role': 'athena', 'content': 'Athena independent research', 'success': True}),
              ('done', {'status': 'completed', 'success': True})]
    body = ''.join(f'event: {event}\ndata: {json.dumps(data)}\n\n' for event, data in events)
    page.route('**/api/ask/stream', lambda route: route.fulfill(content_type='text/event-stream', body=body))
    page.goto(live_server_url)
    page.locator('#input').fill('Research and draft independent sections')
    page.locator('#send-btn').click()
    athena = page.locator('#chat [data-role="athena"] [data-step-body]')
    apollo = page.locator('#chat [data-role="apollo"] [data-step-body]')
    expect(athena).to_contain_text('Athena independent research')
    expect(athena).not_to_contain_text('Apollo independent draft')
    expect(apollo).to_contain_text('Apollo independent draft')
    expect(apollo).not_to_contain_text('Athena independent research')


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


def test_save_connections_keeps_role_defaults_and_chat_choices(page: Page, live_server_url: str) -> None:
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    before = page.request.get(f'{live_server_url}/api/setup/status').json()['role_statuses']
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    expect(page.locator('#provider-connections .provider-connection-card')).to_have_count(4)
    expect(page.locator('#setup-apply-roles')).to_have_count(0)
    for provider, key in [('anthropic', 'fake-e2e-anthropic'), ('openai', 'fake-e2e-openai'), ('deepseek', 'fake-e2e-deepseek')]:
        page.locator(f'[data-edit-provider="{provider}"]').click()
        page.locator('#setup-api-key').fill(key)
        page.locator('#setup-save').click()
        expect(page.locator('#setup-check-result')).to_contain_text('Provider connection saved')
        expect(page.locator('#setup-api-key')).to_have_value('')
    after = page.request.get(f'{live_server_url}/api/setup/status').json()['role_statuses']
    assert [(i['role'],i['provider'],i['model']) for i in after] == [(i['role'],i['provider'],i['model']) for i in before]
    assert not errors


def test_single_or_mixed_models_and_default_scope_keep_existing_chats(page: Page, live_server_url: str) -> None:
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="models"]').click()
    page.locator('#models-shared-provider').select_option('deepseek')
    page.locator('#models-shared-model').select_option('deepseek-flash')
    page.locator('#models-apply-all').click()
    expect(page.locator('.settings-role[data-role="hermes"] .sr-provider')).to_have_value('deepseek')
    hephaestus = page.locator('.settings-role[data-role="hephaestus"]')
    hephaestus.locator('.sr-provider').select_option('anthropic')
    athena = page.locator('.settings-role[data-role="athena"]')
    athena.locator('.sr-provider').select_option('openai')
    expect(page.locator('#models-status-title')).to_contain_text('3 providers')
    saved = page.evaluate("JSON.parse(localStorage.getItem('pantheon:chat-sessions'))")
    original = saved[0]['overrides']
    assert original['hephaestus']['provider'] == 'anthropic'
    assert original['athena']['provider'] == 'openai'
    page.locator('#models-scope').select_option('defaults')
    page.locator('#models-shared-provider').select_option('deepseek')
    page.locator('#models-shared-model').select_option('deepseek-flash')
    page.locator('#models-apply-all').click()
    page.locator('#models-save-defaults').click()
    expect(page.locator('#models-feedback')).to_contain_text('New chat defaults saved')
    page.locator('#models-scope').select_option('chat')
    expect(hephaestus.locator('.sr-provider')).to_have_value('anthropic')
    expect(athena.locator('.sr-provider')).to_have_value('openai')
    page.locator('#new-chat-btn').click()
    expect(hephaestus.locator('.sr-provider')).to_have_value('deepseek')
    expect(athena.locator('.sr-provider')).to_have_value('deepseek')
    page.reload()
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="models"]').click()
    expect(hephaestus.locator('.sr-provider')).to_have_value('deepseek')
    stored = page.evaluate("JSON.parse(localStorage.getItem('pantheon:chat-sessions'))")
    assert next(i for i in stored if i['id'] == saved[0]['id'])['overrides'] == original


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
            {'id': 'task-demo', 'status': 'running', 'cancel': bool(stopped), 'data': {'task': 'Research a topic'}},
            {'id': 'completed-demo', 'status': 'completed', 'data': {'task': 'Finished research'}}
        ]}))
    def stop(route):
        stopped.append(True)
        route.fulfill(status=200, content_type='application/json', body='{"stop_requested": true}')
    page.route('**/api/tasks', history)
    page.route('**/api/tasks/completed-demo', lambda route: route.fulfill(json={
        'id': 'completed-demo', 'status': 'completed', 'data': {'result': '<script>untrusted source</script> Stored answer'},
    }))
    page.route('**/api/tasks/task-demo/stop', stop)
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="info"]').click()
    expect(page.locator('#info-tasks-list')).to_contain_text('Research a topic')
    page.locator('[data-stop-task="task-demo"]').click()
    expect(page.locator('[data-stop-task="task-demo"]')).to_have_text('Stop requested')
    expect(page.locator('[data-stop-task="task-demo"]')).to_be_disabled()
    page.locator('[data-task-result="completed-demo"]').click()
    expect(page.locator('#info-task-result')).to_have_text('<script>untrusted source</script> Stored answer')
    expect(page.locator('#info-task-result script')).to_have_count(0)


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
    # Focus can leave another catalog request in flight. Drain route callbacks
    # before Playwright disposes this test's request context.
    page.unroute_all(behavior='wait')


def test_late_initial_status_preserves_a_connection_being_edited(page: Page, live_server_url: str):
    pending = []
    page.route('**/api/setup/status', lambda route: pending.append(route))
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('#setup-provider').select_option('openai')
    page.locator('#setup-api-key').fill('unsaved-draft-key')
    page.locator('#setup-base-url').fill('https://draft-openai.example/v1')
    payload = page.request.get(f'{live_server_url}/api/setup/status').json()
    for route in pending:
        route.fulfill(json=payload)
    expect(page.locator('#setup-provider')).to_have_value('openai')
    expect(page.locator('#setup-model option[value="gpt-6.1-sol"]')).to_have_count(1)
    expect(page.locator('#setup-api-key')).to_have_value('unsaved-draft-key')
    expect(page.locator('#setup-base-url')).to_have_value('https://draft-openai.example/v1')
    page.unroute_all(behavior='wait')


def test_media_upload_and_transcript_prepare_without_sending(page: Page, live_server_url: str):
    requests = []
    media_id = 'a' * 32
    page.route('**/api/media/upload?*', lambda route: route.fulfill(json={'id': media_id, 'name': 'sample.pdf', 'type': 'application/pdf', 'size': 16}))
    page.route('**/api/media/transcribe', lambda route: route.fulfill(json={'text': 'Review this transcript', 'artifact': {'id': 'b' * 32}}))
    def ask(route):
        requests.append(route.request.post_data_json)
        route.fulfill(content_type='text/event-stream', body='event: done\ndata: {"success":true,"content":"Read the PDF"}\n\n')
    page.route('**/api/ask/stream', ask)
    page.goto(live_server_url)
    page.locator('#attachment-input').set_input_files({'name': 'sample.pdf', 'mimeType': 'application/pdf', 'buffer': b'%PDF-1.7\nfixture'})
    expect(page.locator('#composer-attachments')).to_contain_text('vision model reads on Send')
    assert not requests
    page.locator('#input').fill('Summarize the PDF')
    page.locator('#send-btn').click()
    expect(page.locator('#send-btn')).not_to_be_disabled()
    assert requests[0]['attachments'] == [media_id]
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="media"]').click()
    expect(page.locator('#media-settings-form')).to_be_visible()
    page.locator('#media-audio-file').set_input_files({'name': 'voice.wav', 'mimeType': 'audio/wav', 'buffer': b'RIFF0000WAVE'})
    page.locator('#media-audio-form button').click()
    expect(page.locator('#media-transcript')).to_have_value('Review this transcript')
    page.locator('#media-use-transcript').click()
    expect(page.locator('#input')).to_have_value('Review this transcript')
    assert len(requests) == 1


def test_chat_platform_configuration_and_empty_allowlists(page: Page, live_server_url: str):
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="integrations"]').click()
    page.locator('[data-integration-section="channels"]').click()
    telegram = page.locator('[data-chat-channel="telegram"]')
    telegram.locator('xpath=..').locator('summary').click()
    telegram.locator('[data-channel-enabled]').check()
    telegram.locator('button[type="submit"]').click()
    expect(telegram.locator('[data-channel-status]')).to_contain_text('allowlists')
    telegram.locator('[data-channel-users]').fill('11')
    telegram.locator('[data-channel-destinations]').fill('22')
    telegram.locator('[data-channel-secret="bot_token"]').fill('123:test-token')
    telegram.locator('[data-channel-secret="secret_token"]').fill('callback-test')
    telegram.locator('button[type="submit"]').click()
    expect(page.locator('#integration-list')).to_contain_text('configured')
    assert page.request.get(live_server_url + '/api/channels').json()['items'][1]['users'] == ['11']
    assert 'test-token' not in page.locator('#integration-list').inner_text()
    assert page.locator('[data-chat-channel="slack"]').count() == 1
    assert page.locator('[data-chat-channel="discord"]').count() == 1


def test_followup_context_and_reply_provenance_survive_model_switch_and_reload(page: Page, live_server_url: str):
    requests = []

    def ask(route):
        requests.append(route.request.post_data_json)
        events = [('step_start', {'index': 0, 'role': 'hephaestus'}),
                  ('step_done', {'index': 0, 'role': 'hephaestus', 'task_id': 'original-task',
                                 'provider': 'deepseek', 'model': 'deepseek-flash',
                                 'content': 'INTERMEDIATE_DO_NOT_REPEAT', 'success': True}),
                  ('summary_start', {'role': 'hermes'}),
                  ('summary_done', {'role': 'hermes', 'provider': 'openai', 'model': 'summary-model',
                                    'content': 'def ORCHID_917(a, b): return a + b'}),
                  ('done', {'status': 'completed', 'success': True})]
        route.fulfill(content_type='text/event-stream', body=''.join(
            f'event: {event}\ndata: {json.dumps(data)}\n\n' for event, data in events))

    page.route('**/api/ask/stream', ask)
    page.goto(live_server_url, wait_until="networkidle")
    page.locator("#new-chat-btn").click()
    page.locator('#input').fill('Write function ORCHID_917 to add integers')
    page.locator('#send-btn').click()
    answer = page.locator('#chat [data-role="hephaestus"]').first
    expect(answer).to_have_attribute('data-status', 'done')
    expect(page.locator('#send-btn')).to_contain_text('Send')
    assert requests[0]['history'] == []
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="models"]').click()
    role = page.locator('.settings-role[data-role="hephaestus"]')
    role.locator('.sr-provider').select_option('openai')
    role.locator('.sr-model').select_option('gpt-6.1-sol')
    page.reload()
    expect(answer.locator('.msg-model')).to_have_attribute('title', 'deepseek-flash')
    expect(answer).to_have_attribute('data-provider', 'deepseek')
    expect(answer).to_have_attribute('data-task-id', 'original-task')
    page.locator('#input').fill('Change the previous function to subtract')
    page.locator('#send-btn').click()
    expect(page.locator('#chat [data-role="hephaestus"]')).to_have_count(2)
    expect(page.locator('#send-btn')).to_contain_text('Send')
    assert requests[1]['history'] == [
        {'role': 'user', 'content': 'Write function ORCHID_917 to add integers'},
        {'role': 'assistant', 'content': 'def ORCHID_917(a, b): return a + b'},
    ]
    page.locator('#new-chat-btn').click()
    page.locator('#input').fill('A separate chat')
    page.locator('#send-btn').click()
    expect(page.locator('#send-btn')).to_contain_text('Send')
    assert requests[2]['history'] == []


def test_enhancement_sends_current_chat_hermes_choice(page: Page, live_server_url: str):
    requests = []

    def enhance(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={'prompt': 'Improved draft', 'provider': 'openai', 'model': 'private-hermes'})

    page.route('**/api/prompt/enhance', enhance)
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="models"]').click()
    role = page.locator('.settings-role[data-role="hermes"]')
    role.locator('.sr-provider').select_option('openai')
    role.locator('.sr-custom summary').click()
    role.locator('.sr-custom-model').fill('private-hermes')
    role.locator('.sr-use-custom').click()
    page.locator('#toggle-settings').click()
    page.locator('#input').fill('Original draft')
    page.locator('#enhance-prompt-btn').click()
    expect(page.locator('#input')).to_have_value('Improved draft')
    assert requests[0]['overrides']['hermes'] == {'provider': 'openai', 'model': 'private-hermes'}
    expect(page.locator('#composer-status')).to_contain_text('openai / private-hermes')


def test_custom_ids_available_for_role_and_bulk_assignment(page: Page, live_server_url: str):
    result = page.request.post(live_server_url + '/api/connections/save', data={
        'provider': 'openai', 'model': 'private-saved-model',
        'base_url': 'https://gateway.example/v1', 'api_key': 'fake-key',
    })
    assert result.ok
    page.goto(live_server_url)
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="models"]').click()
    role = page.locator('.settings-role[data-role="hephaestus"]')
    role.locator('.sr-provider').select_option('openai')
    role.locator('.sr-model').select_option('private-saved-model')
    expect(role.locator('.sr-model')).to_have_value('private-saved-model')
    page.locator('#models-shared-provider').select_option('openai')
    page.locator('#models-shared-custom-model').locator('..').locator('..').locator('summary').click()
    page.locator('#models-shared-custom-model').fill('private-bulk-model')
    page.locator('#models-apply-all').click()
    for name in ('hermes', 'hephaestus', 'athena', 'apollo'):
        expect(page.locator(f'.settings-role[data-role="{name}"] .sr-model')).to_have_value('private-bulk-model')
    page.reload()
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="models"]').click()
    expect(role.locator('.sr-model')).to_have_value('private-bulk-model')


def test_legacy_model_unknown_and_long_history_remains_bounded(page: Page, live_server_url: str):
    messages = [{'role': 'user' if index % 2 == 0 else 'hephaestus', 'text': f'Old message {index}'}
                for index in range(20)]
    messages[-1]['text'] = 'HEAD ' + ('😀中文' * 6000) + ' TAIL'
    chat = {'id': 'legacy-audit-chat', 'title': 'Legacy audit', 'mode': 'auto',
            'overrides': {}, 'createdAt': 1, 'updatedAt': 1, 'messages': messages}
    state = page.request.get(live_server_url + '/api/conversations').json()
    assert page.request.put(live_server_url + '/api/conversations', data={
        'schema_version': 1, 'expected_revision': state['revision'], 'sessions': [chat],
    }).ok
    page.add_init_script(f"localStorage.setItem('pantheon:chat-sessions', JSON.stringify([{json.dumps(chat, ensure_ascii=True)}]));")
    requests = []

    def ask(route):
        requests.append(route.request.post_data_json)
        route.fulfill(content_type='text/event-stream', body='event: done\ndata: {"status":"completed"}\n\n')

    page.route('**/api/ask/stream', ask)
    page.goto(live_server_url)
    old = page.locator('#chat [data-role="hephaestus"]').last
    expect(old.locator('.msg-model')).to_have_text('Model not recorded')
    expect(page.locator('#info-conversation-status')).to_contain_text('conversations saved')
    expect(page.locator('#chat-list .chat-row-title').filter(has_text='Conflict copy:')).to_have_count(0)
    page.locator('#input').fill('Continue the previous answer')
    page.locator('#send-btn').click()
    expect(page.locator('#send-btn')).to_contain_text('Send')
    history = requests[0]['history']
    assert len(history) <= 16
    assert sum(len(item['content']) for item in history) <= 24000
    assert all(len(item['content']) <= 12000 for item in history)
    assert 'HEAD' in history[-1]['content'] and 'TAIL' in history[-1]['content']
    assert '[Excerpt:' in history[-1]['content']
    assert not any(0xD800 <= ord(char) <= 0xDFFF for char in history[-1]['content'])
