"""Layout regressions use a private server and mocked model output, never paid APIs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(autouse=True)
def isolated_layout_state(page: Page):
    state = {'schema_version': 1, 'revision': '', 'sessions': []}

    def conversations(route):
        if route.request.method == 'PUT':
            state.update(sessions=route.request.post_data_json['sessions'], revision='layout')
        route.fulfill(json=state)

    page.route('**/api/conversations', conversations)
    page.route('**/api/update', lambda route: route.fulfill(json={
        'current_version': '0.4.0', 'latest_version': 'v0.4.0', 'update_available': False,
    }))
    page.emulate_media(reduced_motion='reduce')


def assert_composer_at_bottom(page: Page) -> None:
    bounds = page.evaluate("""() => {
      const main = document.querySelector('.main').getBoundingClientRect();
      const composer = document.querySelector('#composer').getBoundingClientRect();
      const chat = document.querySelector('#chat').getBoundingClientRect();
      const input = document.querySelector('.composer-inner').getBoundingClientRect();
      return {bottom: composer.bottom, mainBottom: main.bottom, height: composer.height,
        top: composer.top, chatBottom: chat.bottom, chatHeight: chat.height,
        inputBottom: input.bottom, inputRight: input.right, mainRight: main.right,
        sendRight: document.querySelector('#send-btn').getBoundingClientRect().right,
        viewport: innerHeight, width: innerWidth,
        overflow: document.documentElement.scrollWidth > innerWidth};
    }""")
    assert abs(bounds['bottom'] - bounds['mainBottom']) <= 2
    assert abs(bounds['bottom'] - bounds['viewport']) <= 2
    assert abs(bounds['top'] - bounds['chatBottom']) <= 2
    assert bounds['height'] < 180, 'An empty composer must not consume the flexible chat row'
    assert bounds['chatHeight'] > 200
    assert 0 <= bounds['viewport'] - bounds['inputBottom'] <= 65
    assert bounds['mainRight'] <= bounds['width'] + 2
    assert bounds['inputRight'] <= bounds['width']
    assert bounds['sendRight'] <= bounds['width']
    assert not bounds['overflow']


def screenshot(page: Page, name: str) -> None:
    folder = Path(__file__).resolve().parents[1] / 'dist' / 'web-temple-v2-evidence'
    folder.mkdir(parents=True, exist_ok=True)
    draft = page.locator('#input').input_value()
    page.locator('#input').fill('')
    page.mouse.move(0, 0)
    page.screenshot(path=str(folder / f'{name}.png'), animations='disabled', scale='css')
    page.locator('#input').fill(draft)


@pytest.mark.parametrize('size', [(1440, 1000), (1024, 768), (390, 844)])
def test_composer_anchors_with_hidden_visible_and_dismissed_update(page: Page, live_server_url: str, size) -> None:
    page.set_viewport_size({'width': size[0], 'height': size[1]})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(live_server_url)
    expect(page.locator('#welcome')).to_be_visible()
    expect(page.locator('#gods-list .god-row.loading')).to_have_count(0)
    expect(page.locator('#update-banner')).to_be_hidden()
    for theme in ['dark', 'light']:
        page.locator('#toggle-settings').click()
        page.locator('[data-tab="display"]').click()
        page.locator(f'[data-action="theme"][data-value="{theme}"]').click()
        page.locator('#settings-close').click()
        name = 'temple-fresco-night-v2.png' if theme == 'dark' else 'temple-fresco-day-v2.png'
        image = live_server_url + '/static/' + name
        assert name in page.locator('.main').evaluate('node => getComputedStyle(node, "::before").backgroundImage')
        decoded = page.evaluate('''async source => {
          const image = new Image(); image.src = source; await image.decode();
          return {width: image.naturalWidth, height: image.naturalHeight};
        }''', image)
        assert decoded['width'] >= 1000 and decoded['height'] >= 700
        assert_composer_at_bottom(page)
        page.locator('#input').fill('A draft to retain through layout changes')
        screenshot(page, f'welcome-{theme}-{size[0]}')
        page.evaluate("""() => {
          document.querySelector('#update-banner-text').textContent = 'A local layout test update is available.';
          document.querySelector('#update-banner').hidden = false;
        }""")
        expect(page.locator('#update-banner')).to_be_visible()
        assert_composer_at_bottom(page)
        page.locator('#update-banner-dismiss').click()
        expect(page.locator('#update-banner')).to_be_hidden()
        assert_composer_at_bottom(page)
        expect(page.locator('#input')).to_have_value('A draft to retain through layout changes')

        if size[0] == 1440:
            page.locator('.mode-chip[data-mode="multi"]').click()
            page.locator('#toggle-settings').click()
            page.locator('[data-tab="models"]').click()
            assert_composer_at_bottom(page)
            screenshot(page, f'settings-{theme}')
            page.locator('#settings-close').click()

    assert not errors


def test_chat_scroll_theme_and_new_chat_keep_input_reachable(page: Page, live_server_url: str) -> None:
    calls = []
    content = '## Temple layout verification\n\n' + '\n\n'.join(
        f'Paragraph {index}: a readable saved result without a real provider call.' for index in range(32)
    ) + '\n\n```python\nprint("local fixture")\n```'
    events = [
        ('step_start', {'index': 0, 'total': 1, 'role': 'hephaestus', 'task': 'Layout fixture'}),
        ('step_done', {'index': 0, 'role': 'hephaestus', 'content': content, 'success': True}),
        ('done', {'status': 'completed', 'success': True}),
    ]

    def answer(route):
        calls.append(route.request.post_data_json)
        body = ''.join(f'event: {name}\ndata: {json.dumps(data)}\n\n' for name, data in events)
        route.fulfill(content_type='text/event-stream', body=body)

    page.route('**/api/ask/stream', answer)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.goto(live_server_url)
    expect(page.locator('#welcome')).to_be_visible()
    idle_opacity = page.locator('.main').evaluate('node => Number(getComputedStyle(node, "::before").opacity)')
    page.locator('.example-chip').first.click()
    expect(page.locator('#input')).not_to_have_value('')
    assert not calls, 'Starting points only fill a draft'
    page.locator('#send-btn').click()
    expect(page.locator('#chat')).to_contain_text('Temple layout verification')
    expect(page.locator('#welcome')).to_have_count(0)
    expect(page.locator('#send-btn')).to_contain_text('Send')
    assert len(calls) == 1
    assert_composer_at_bottom(page)
    chat_opacity = page.locator('.main').evaluate('node => Number(getComputedStyle(node, "::before").opacity)')
    assert chat_opacity < idle_opacity
    assert page.locator('#chat').evaluate('node => node.scrollHeight > node.clientHeight')
    page.locator('#input').fill('Keep this unsent follow-up')
    screenshot(page, 'conversation-dark')

    page.locator('#toggle-settings').click()
    page.locator('[data-tab="display"]').click()
    page.locator('[data-action="theme"][data-value="light"]').click()
    page.locator('#settings-close').click()
    expect(page.locator('#input')).to_have_value('Keep this unsent follow-up')
    assert_composer_at_bottom(page)
    screenshot(page, 'conversation-light')

    page.locator('#new-chat-btn').click()
    expect(page.locator('#welcome')).to_be_visible()
    assert_composer_at_bottom(page)
    assert len(calls) == 1, 'Theme and new-chat navigation must not resend a task'
