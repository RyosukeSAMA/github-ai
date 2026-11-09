"""Actual, offline browser checks against a bounded, approved file snapshot."""
from __future__ import annotations

import base64
import json
import mimetypes
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

ORIGIN = 'https://pantheon-check.invalid'


def check_site(manifest: dict, directory: Path) -> dict:
    started = time.time()
    checks, screenshots, errors, blocked = [], [], [], []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {'checks': [{'label': 'Browser checks', 'status': 'unverified',
                            'detail': 'Browser checker is unavailable. Install Pantheon with the checks extra and a supported browser.'}],
                'screenshots': [], 'started': started, 'finished': time.time()}
    files = manifest['files']
    entry = manifest['contract']['entrypoint']
    def record(label, passed, detail, viewport):
        checks.append({'label': label, 'status': 'passed' if passed else 'failed',
                       'detail': str(detail)[:600], 'viewport': viewport})
    with sync_playwright() as driver:
        browser = None
        # Installed Chrome/Edge and an existing Playwright Chromium are supported; never download implicitly.
        for channel in ('chrome', 'msedge', None):
            try:
                browser = driver.chromium.launch(headless=True, **({'channel': channel} if channel else {}),
                    args=['--force-webrtc-ip-handling-policy=disable_non_proxied_udp'])
                break
            except Exception:
                continue
        if browser is None:
            return {'checks': [{'label': 'Browser checks', 'status': 'unverified',
                                'detail': 'No supported browser could start. Install Chrome, Edge or Playwright Chromium and retry.'}],
                    'screenshots': [], 'started': started, 'finished': time.time()}
        try:
            for name, width, height in [('desktop', 1440, 900), ('mobile', 390, 844)]:
                context = browser.new_context(viewport={'width': width, 'height': height},
                    service_workers='block', accept_downloads=False, permissions=[])
                def route(request_route):
                    request = request_route.request
                    url = urlsplit(request.url)
                    key = unquote(url.path).lstrip('/')
                    if url.scheme == 'https' and url.netloc == 'pantheon-check.invalid' and request.method == 'GET' and key in files:
                        mime = mimetypes.guess_type(key)[0] or 'application/octet-stream'
                        if key.endswith(('.js', '.mjs')):
                            mime = 'application/javascript'
                        request_route.fulfill(status=200, body=base64.b64decode(files[key]), content_type=mime,
                            headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
                    else:
                        if len(blocked) < 20:
                            blocked.append({'path': url.path[:160], 'reason': 'Outside approved snapshot or unsupported request'})
                        request_route.abort()
                context.add_init_script('try { localStorage.clear(); sessionStorage.clear(); } catch (_) {}')
                context.route('**/*', route)
                context.route_web_socket('**/*', lambda socket: socket.close())
                page = context.new_page()
                context.on('page', lambda popup: popup.close() if popup != page else None)
                page.set_default_timeout(1800)
                page.on('pageerror', lambda error: errors.append(str(error)[:400]) if len(errors) < 20 else None)
                page.on('dialog', lambda dialog: dialog.dismiss())
                url = ORIGIN + '/' + entry
                try:
                    response = page.goto(url, wait_until='load', timeout=10000)
                    page.wait_for_timeout(180)
                    record('Page opens', bool(response and response.status == 200 and page.locator('body').count()), 'Opened the approved entry file.', name)
                    overflow = page.evaluate('Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0) - innerWidth')
                    record('Fits viewport', overflow <= 1, f'Horizontal overflow: {max(0, overflow)} px at {width} px.', name)
                    for item in manifest['contract']['interactions']:
                        try:
                            page.goto(url, wait_until='load', timeout=10000)
                            if item.get('click'):
                                page.locator(item['click']).click(timeout=1800, no_wait_after=True)
                            target = page.locator(item['expect'])
                            target.wait_for(state='visible', timeout=1800)
                            if item.get('text'):
                                from playwright.sync_api import expect
                                expect(target).to_contain_text(item['text'], timeout=1800)
                            record(item['label'], True, 'Observed the requested visible result'+(' and text.' if item.get('text') else '.'), name)
                        except Exception as exc:
                            record(item['label'], False, str(exc).split('Call log:')[0], name)
                    image = name + '.png'
                    page.screenshot(path=str(directory / image), animations='disabled', timeout=5000)
                    screenshots.append(image)
                except Exception as exc:
                    record('Page opens', False, str(exc).split('Call log:')[0], name)
                finally:
                    context.close()
            checks.append({'label': 'Uncaught page errors', 'status': 'failed' if errors else 'passed',
                           'detail': '\n'.join(errors) if errors else 'No uncaught page errors observed during this check.'})
            # Dependencies or API calls outside the snapshot cannot be silently treated as verified.
            if blocked:
                checks.append({'label': 'External / undeclared dependencies', 'status': 'unverified',
                               'detail': f'{len(blocked)} requests blocked. Only declared snapshot files were served.'})
            return {'checks': checks, 'screenshots': screenshots, 'blocked': blocked,
                    'started': started, 'finished': time.time(), 'browser': browser.version,
                    'scope': 'Offline snapshot in a fresh browser context; no live services or external integrations verified.'}
        finally:
            browser.close()


def main(directory: str):
    root = Path(directory).resolve()
    manifest = json.loads((root / 'input.json').read_text())
    try:
        result = check_site(manifest, root)
    except Exception:
        result = {'checks': [{'label': 'Browser checks', 'status': 'unverified', 'detail': 'Checker did not finish. Review the environment and retry.'}], 'screenshots': []}
    (root / 'output.json').write_text(json.dumps(result))


if __name__ == '__main__':
    import sys
    main(sys.argv[1])
