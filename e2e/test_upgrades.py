import json

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(autouse=True)
def private_chats(page: Page):
    state = {'schema_version':1,'revision':'','sessions':[]}
    def conversations(route):
        if route.request.method == 'PUT':
            state.update(sessions=route.request.post_data_json['sessions'],revision='test-revision')
        route.fulfill(json=state)
    page.route('**/api/conversations', conversations)


def test_incremental_text_is_visible_before_done_and_not_duplicated(page: Page, live_server_url):
    frames = ''.join(f'event: {event}\ndata: {json.dumps(data)}\n\n' for event,data in [
        ('start',{'task_id':'incremental'}),('step_start',{'index':0,'role':'athena'}),
        ('step_chunk',{'index':0,'role':'athena','text':'Alpha '})])
    end = ''.join(f'event: {event}\ndata: {json.dumps(data)}\n\n' for event,data in [
        ('step_chunk',{'index':0,'role':'athena','text':'Beta'}),
        ('step_done',{'index':0,'role':'athena','content':'Alpha Beta','success':True}),
        ('done',{'status':'completed','success':True})])
    page.add_init_script('''
      const realFetch = window.fetch;
      window.fetch = (url,options) => url === '/api/ask/stream' ? Promise.resolve(new Response(new ReadableStream({
        start(controller) {controller.enqueue(new TextEncoder().encode(FIRST)); window.finishStream = () => {
          controller.enqueue(new TextEncoder().encode(LAST));controller.close();};}
      }))) : realFetch(url,options);
    '''.replace('FIRST',json.dumps(frames)).replace('LAST',json.dumps(end)))
    page.goto(live_server_url,wait_until='networkidle')
    page.locator('#input').fill('Stream this')
    page.locator('#send-btn').click()
    expect(page.locator('#chat [data-step-body]')).to_contain_text('Alpha')
    expect(page.locator('#send-btn')).to_contain_text('Stop')
    page.evaluate('window.finishStream()')
    expect(page.locator('#send-btn')).to_contain_text('Send')
    expect(page.locator('#chat [data-step-body]')).to_have_text('Alpha Beta')


def test_long_chat_dom_is_bounded_and_complete_history_survives(page: Page, live_server_url):
    messages = [{'role':'user' if i % 2 == 0 else 'hephaestus', 'text':f'Message {i}'} for i in range(240)]
    messages[-1]['text'] = 'HEAD '+('x'*25000)+' TAIL'
    chat = {'id':'long-upgrade','title':'Long chat','mode':'auto','overrides':{},'createdAt':1,'updatedAt':1,'messages':messages}
    state = {'schema_version':1,'revision':'','sessions':[chat]}
    def conversations(route):
        if route.request.method == 'PUT':
            state.update(sessions=route.request.post_data_json['sessions'],revision='next')
        route.fulfill(json=state)
    page.route('**/api/conversations', conversations)
    requests = []
    def ask(route):
        requests.append(route.request.post_data_json)
        route.fulfill(content_type='text/event-stream', body='event: done\ndata: {"success":true,"status":"completed"}\n\n')
    page.route('**/api/ask/stream',ask)
    page.goto(live_server_url,wait_until='networkidle')
    expect(page.locator('#chat .msg')).to_have_count(80)
    expect(page.locator('.load-full-message')).to_have_count(1)
    page.locator('.load-full-message').click()
    expect(page.locator('#chat .msg').last).to_contain_text('TAIL')
    page.locator('.load-earlier-messages').click()
    expect(page.locator('#chat .msg')).to_have_count(160)
    page.locator('#input').fill('Continue from the full transcript')
    page.locator('#send-btn').click()
    expect(page.locator('#send-btn')).to_contain_text('Send')
    assert len(requests[0]['history']) <= 16
    assert 'TAIL' in requests[0]['history'][-1]['content']
    stored = page.evaluate("JSON.parse(localStorage.getItem('pantheon:chat-sessions'))")
    original = next(item for item in stored if item['id']=='long-upgrade')
    assert original['messages'][0]['text'] == 'Message 0'
    assert original['messages'][239]['text'] == messages[239]['text']
    assert len(original['messages']) == 241


def test_connections_show_references_before_disable_and_can_restore(page: Page, live_server_url):
    assert page.request.post(live_server_url+'/api/connections/save',data={
        'provider':'deepseek','model':'test-model','api_key':'fake-key','base_url':'https://provider.example/v1'}).ok
    page.goto(live_server_url,wait_until='networkidle')
    page.locator('#toggle-settings').click()
    card = page.locator('.provider-connection-card[data-provider="deepseek"]')
    dialogs = []
    def confirm(dialog):
        dialogs.append(dialog.message)
        dialog.accept()
    page.on('dialog',confirm)
    card.get_by_role('button',name='Disable',exact=True).click()
    expect(card).to_contain_text('Disabled')
    assert 'Saved roles:' in dialogs[0] and 'media:' in dialogs[0]
    card.get_by_role('button',name='Enable',exact=True).click()
    expect(card.get_by_role('button',name='Disable',exact=True)).to_be_visible()


def test_keyboard_chat_navigation_and_composer_shortcuts(page: Page, live_server_url):
    page.goto(live_server_url,wait_until='networkidle')
    page.locator('#new-chat-btn').click()
    rows = page.locator('#chat-list .chat-row')
    rows.first.focus()
    page.keyboard.press('ArrowDown')
    expect(rows.nth(1)).to_be_focused()
    page.keyboard.press('Enter')
    expect(rows.nth(1)).to_have_class('chat-row active')
    page.keyboard.press('Control+Shift+O')
    expect(rows).to_have_count(3)
    expect(page.locator('#input')).to_be_focused()
