import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parents[1]


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        url = f"http://127.0.0.1:{server.server_port}/desktop/index.html"
        page.goto(url, wait_until="networkidle")
        assert page.locator(".brand img").evaluate("(el)=>el.naturalWidth") > 0
        page.screenshot(path=str(root / "desktop/preview-light.png"))
        page.locator("#model-open").click()
        page.locator('[name="model-mode"][value="mixed"]').check()
        assert page.locator("#model-rows select").count() == 4
        assert page.locator("#model-rows select").nth(1).input_value() == "OpenAI"
        page.locator("#save-models").click()
        page.locator("#approval-open").click()
        page.locator("#deny-approval").click()
        expect(page.locator("#activity-list")).to_contain_text("示例审批：已拒绝")
        page.locator("#files-tab").click()
        expect(page.locator("#file-content")).to_contain_text("上线前检查清单")
        page.locator("#terminal-toggle").click()
        page.locator("#terminal-simulate").click()
        expect(page.locator("#terminal-output")).to_contain_text("没有运行 shell 命令")
        page.locator("#terminal-close").click()
        page.locator("#new-task").click()
        page.locator("#new-prompt").fill("生成项目交付说明")
        page.get_by_role("button", name="创建示例任务", exact=True).click()
        expect(page.locator("#task-list")).to_contain_text("生成项目交付说明")
        page.locator("#run-demo").click()
        expect(page.locator("#run-demo")).to_contain_text("停止示例")
        page.locator("#run-demo").click()
        expect(page.locator("#task-state")).to_contain_text("已停止")
        page.keyboard.press("Control+k")
        page.locator("#command-search").fill("分配角色")
        page.locator("#command-list button").click()
        expect(page.locator("#models-dialog")).to_be_visible()
        page.keyboard.press("Escape")
        page.get_by_role("button", name="发布准备", exact=True).click()
        page.locator("#result-tab").click()
        page.evaluate("document.querySelector('#toast').hidden = true")
        page.locator("#theme-toggle").click()
        page.screenshot(path=str(root / "desktop/preview-dark.png"))
        for width in (1440, 1024, 760):
            page.set_viewport_size({"width": width, "height": 950})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
        assert not errors, errors
        assert all("/api/" not in url for url in requests), requests
        browser.close()
        (root / "desktop/verification.json").write_text(
            json.dumps(
                {
                    "prototype_only": True,
                    "checks": [
                        "light/dark render",
                        "local branding",
                        "single/mixed model selection",
                        "approval refusal",
                        "result/files/activity tabs",
                        "terminal simulation",
                        "new task and stop",
                        "keyboard command menu",
                        "1440/1024/760 layout",
                    ],
                    "page_errors": errors,
                    "api_requests": 0,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print("DESKTOP_PROTOTYPE_PASS", len(requests), "static requests; zero API requests")
finally:
    server.shutdown()
    server.server_close()
