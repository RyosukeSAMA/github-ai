"""Transport faults and in-flight edits, without making provider calls."""
import json

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(autouse=True)
def isolated_conversations(page: Page):
    # Fault tests must not seed transcripts consumed by the existing UI suite.
    state = {'schema_version': 1, 'revision': 0, 'sessions': [], 'deleted': []}
    def conversations(route):
        if route.request.method == 'PUT':
            state.update(sessions=route.request.post_data_json['sessions'], revision=state['revision'] + 1)
        route.fulfill(json=state)
    page.route('**/api/conversations', conversations)


def sse(events):
    return ''.join(f'event: {name}\ndata: {json.dumps(data)}\n\n' for name, data in events)


@pytest.mark.parametrize('saved_status', ['unavailable', 'running', 'completed', 'failed'])
def test_unexpected_eof_retains_output_and_reconciles_without_resending(page: Page, live_server_url, saved_status):
    requests = []
    events = [('start', {'task_id': 'eof-task'}),
              ('step_start', {'index': 0, 'role': 'athena'}),
              ('step_chunk', {'index': 0, 'role': 'athena', 'text': 'Partial answer retained'})]
    def stream(route):
        requests.append(route.request.post_data_json)
        route.fulfill(content_type='text/event-stream', body=sse(events))
    page.route('**/api/ask/stream', stream)
    page.route('**/api/tasks/eof-task', lambda route: route.fulfill(status=404 if saved_status == 'unavailable' else 200,
        json={'id': 'eof-task', 'status': saved_status,
              'data': {'archive_available': True, 'result': 'Saved final answer'}}))
    page.route('**/api/tasks/eof-task/archive', lambda route: route.fulfill(json={
        'content': 'Saved final answer', 'steps': [{'role': 'athena', 'content': 'Full saved research',
            'success': saved_status == 'completed', 'metadata': {'provider': 'fake', 'model': 'saved-model'}}]}))
    page.goto(live_server_url)
    page.locator('#input').fill('Simulate unexpected EOF')
    page.locator('#send-btn').click()
    expect(page.locator('#send-btn')).to_contain_text('Send')
    expect(page.locator('.msg.assistant[data-status="running"]')).to_have_count(0)
    expect(page.locator('.step-status.streaming')).to_have_count(0)
    if saved_status in {'completed', 'failed'}:
        expect(page.locator('#workspace-state')).to_have_text('Ready' if saved_status == 'completed' else 'Needs attention')
        expect(page.locator('#chat')).to_contain_text('Saved final answer')
        expect(page.locator('#chat')).to_contain_text('Full saved research')
    else:
        expect(page.locator('#workspace-state')).to_have_text('Connection interrupted')
        expect(page.locator('#chat')).to_contain_text('Partial answer retained')
        expect(page.locator('#chat .msg.error')).to_contain_text('eof-task')
        expect(page.locator('#chat .msg.error')).to_contain_text('No task was resent')
    assert len(requests) == 1
    stored = page.evaluate("JSON.parse(localStorage.getItem('pantheon:chat-sessions'))")
    assert all(message.get('status') != 'running' for session in stored for message in session.get('messages', []))


def test_model_custom_drafts_survive_refresh_focus_scope_and_provider(page: Page, live_server_url):
    page.goto(live_server_url, wait_until='networkidle')
    page.locator('#toggle-settings').click()
    page.locator('[data-tab="models"]').click()
    role = page.locator('.settings-role[data-role="hephaestus"]')
    provider = role.locator('.sr-provider').input_value()
    role.locator('.sr-custom summary').click()
    field = role.locator('.sr-custom-model')
    field.fill('private-unsaved-model')
    field.evaluate('(el) => el.setSelectionRange(4, 11)')
    with page.expect_response('**/api/setup/status'):
        page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(field).to_have_value('private-unsaved-model')
    expect(role.locator('.sr-custom')).to_have_attribute('open', '')
    expect(field).to_be_focused()
    assert field.evaluate('(el) => [el.selectionStart, el.selectionEnd]') == [4, 11]
    role.locator('.sr-provider').select_option('anthropic' if provider != 'anthropic' else 'openai')
    expect(field).to_have_value('')
    role.locator('.sr-provider').select_option(provider)
    expect(field).to_have_value('private-unsaved-model')
    page.locator('#models-scope').select_option('defaults')
    expect(field).to_have_value('')
    page.locator('#models-scope').select_option('chat')
    expect(field).to_have_value('private-unsaved-model')
    page.locator('.models-shared-controls summary').click()
    page.locator('#models-shared-custom-model').fill('shared-chat-only')
    page.locator('#new-chat-btn').click()
    expect(field).to_have_value('')
    expect(page.locator('#models-shared-custom-model')).to_have_value('')
    page.locator('#chat-list .chat-row').nth(1).locator('.chat-row-title').click()
    expect(field).to_have_value('private-unsaved-model')
    expect(page.locator('#models-shared-custom-model')).to_have_value('shared-chat-only')


@pytest.mark.parametrize('change', ['new_chat', 'switch_chat', 'edit_aba', 'hermes_model', 'mode_aba', 'newer_request'])
def test_stale_enhancement_never_rewrites_another_draft(page: Page, live_server_url, change):
    # Deliberately ignore AbortSignal so a late response still tests the identity guard.
    page.add_init_script('''
        const realFetch = window.fetch;
        window.pendingEnhancements = [];
        window.fetch = (url, options) => url === '/api/prompt/enhance'
          ? new Promise(resolve => window.pendingEnhancements.push(resolve))
          : realFetch(url, options);
        window.finishEnhancement = () => window.pendingEnhancements.shift()(new Response(
          JSON.stringify({prompt:'Late enhancement from old context'}), {status:200}));
    ''')
    page.goto(live_server_url, wait_until='networkidle')
    if change == 'switch_chat':
        page.locator('#new-chat-btn').click()
    original = 'Original draft text'
    page.locator('#input').fill(original)
    page.locator('#enhance-prompt-btn').click()
    page.wait_for_function('window.pendingEnhancements.length === 1')
    if change == 'new_chat':
        page.locator('#new-chat-btn').click()
    elif change == 'switch_chat':
        page.locator('#chat-list .chat-row').nth(1).locator('.chat-row-title').click()
    elif change == 'edit_aba':
        page.locator('#input').fill('Edited once')
        page.locator('#input').fill(original)
    elif change == 'mode_aba':
        page.locator('[data-mode="multi"]').click()
        page.locator('[data-mode="auto"]').click()
    elif change == 'newer_request':
        page.locator('#new-chat-btn').click()
        page.locator('#enhance-prompt-btn').click()
        page.wait_for_function('window.pendingEnhancements.length === 2')
    else:
        page.locator('#toggle-settings').click()
        page.locator('[data-tab="models"]').click()
        page.locator('.settings-role[data-role="hermes"] .sr-provider').select_option('anthropic')
    page.evaluate('window.finishEnhancement()')
    if change == 'newer_request':
        expect(page.locator('#enhance-prompt-btn')).to_have_attribute('aria-busy', 'true')
        expect(page.locator('#input')).to_have_value(original)
        page.evaluate('window.finishEnhancement()')
        expect(page.locator('#input')).to_have_value('Late enhancement from old context')
        return
    expect(page.locator('#enhance-prompt-btn')).to_have_attribute('aria-busy', 'false')
    expect(page.locator('#input')).to_have_value(original)
    expect(page.locator('#enhance-prompt-btn')).not_to_have_attribute('aria-label', 'Undo prompt enhancement')


def test_network_error_after_partial_response_retains_task_and_text(page: Page, live_server_url):
    events = sse([('start', {'task_id': 'network-task'}),
                  ('step_start', {'role': 'athena', 'index': 0}),
                  ('step_chunk', {'role': 'athena', 'index': 0, 'text': 'Partial network output'})])
    page.add_init_script('''
      const realFetch = window.fetch;
      window.taskAttempts = 0;
      window.fetch = (url, options) => {
        if (url !== '/api/ask/stream') return realFetch(url, options);
        window.taskAttempts++;
        return Promise.resolve(new Response(new ReadableStream({start(controller) {
          controller.enqueue(new TextEncoder().encode(EVENTS));
          window.breakTaskStream = () => controller.error(new Error('Simulated connection reset'));
        }}), {status:200}));
      };
    '''.replace('EVENTS', json.dumps(events)))
    page.route('**/api/tasks/network-task', lambda route: route.fulfill(status=404, json={'detail': 'unavailable'}))
    page.goto(live_server_url)
    page.locator('#input').fill('Simulate network reset')
    page.locator('#send-btn').click()
    expect(page.locator('#chat')).to_contain_text('Partial network output')
    page.evaluate('window.breakTaskStream()')
    expect(page.locator('#workspace-state')).to_have_text('Connection interrupted')
    expect(page.locator('#chat .msg.error')).to_contain_text('network-task')
    expect(page.locator('#chat .msg.error')).to_contain_text('No task was resent')
    expect(page.locator('#chat .msg.assistant')).to_have_attribute('data-status', 'interrupted')
    expect(page.locator('#send-btn')).to_contain_text('Send')
    assert page.evaluate('window.taskAttempts') == 1


def test_workspace_command_stream_keeps_stdout_and_exit_status(page: Page, live_server_url):
    page.route('**/api/workspace/terminal/stream', lambda route: route.fulfill(
        content_type='text/event-stream', body=sse([('stdout', {'text': 'Terminal smoke output'}),
                                                   ('exit', {'returncode': 0})])))
    page.goto(live_server_url)
    page.locator('#toggle-workspace').click()
    page.locator('[data-ws-tab="terminal"]').click()
    page.locator('#ws-command-input').fill('echo simulated')
    page.locator('#ws-run-command').click()
    expect(page.locator('#ws-output')).to_contain_text('Terminal smoke output')
    expect(page.locator('#ws-output')).to_contain_text('[exit 0]')
    expect(page.locator('#workspace-state')).to_have_text('Ready')
    expect(page.locator('#ws-command-input')).to_be_enabled()
