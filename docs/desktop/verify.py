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
        page.locator("#model-open").click()
        expect(page.locator('[name="model-mode"][value="mixed"]')).to_be_checked()
        assert page.locator("#model-rows select").nth(1).input_value() == "OpenAI"
        page.keyboard.press("Escape")
        page.locator("#review-tab").click()
        page.locator("#review-reject").click()
        expect(page.locator("#review-state")).to_contain_text("已退回")
        page.locator("#review-accept").click()
        expect(page.locator("#review-state")).to_contain_text("未写入项目")
        page.locator('[data-view="library"]').click()
        expect(page.locator(".artifact-tile")).to_have_count(3)
        page.locator('[data-kind="research"]').click()
        expect(page.locator(".artifact-tile")).to_have_count(1)
        page.locator(".artifact-tile").click()
        expect(page.locator("#breadcrumb-task")).to_have_text("比较数据存储方案")
        page.locator("#prompt").fill("只属于研究任务的草稿")
        page.locator('[data-mode="multi"]').click()
        page.locator("#model-open").click()
        expect(page.locator('[name="model-mode"][value="single"]')).to_be_checked()
        page.keyboard.press("Escape")
        page.get_by_role("button", name="发布准备", exact=True).click()
        expect(page.locator("#prompt")).to_have_value("")
        expect(page.locator('[data-mode="auto"]')).to_have_class("selected")
        page.get_by_role("button", name="比较数据存储方案", exact=True).click()
        expect(page.locator("#prompt")).to_have_value("只属于研究任务的草稿")
        expect(page.locator('[data-mode="multi"]')).to_have_class("selected")
        page.locator('[data-view="tasks"]').click()
        rows = page.locator(".mission-row")
        rows.nth(1).get_by_role("button", name="运行示例", exact=True).click()
        rows.nth(2).get_by_role("button", name="运行示例", exact=True).click()
        expect(page.locator("#metric-running")).to_have_text("2")
        page.evaluate("document.querySelector('#toast').hidden = true")
        page.screenshot(path=str(root / "desktop/preview-tasks.png"))
        rows.nth(1).get_by_role("button", name="停止示例", exact=True).click()
        expect(page.locator("#metric-running")).to_have_text("1")
        expect(rows.nth(1)).to_contain_text("已停止")
        expect(rows.nth(2).get_by_role("button", name="停止示例", exact=True)).to_be_visible()
        rows.nth(2).get_by_role("button", name="停止示例", exact=True).click()
        page.locator('[data-view="capabilities"]').click()
        expect(page.locator(".capability-grid>button")).to_have_count(6)
        page.locator('[data-capability="desktop"]').click()
        expect(page.locator("#info-dialog")).to_contain_text("尚未实现")
        page.keyboard.press("Escape")
        page.locator("#focus-preview").click()
        expect(page.locator(".app")).to_have_attribute("data-layout", "focus")
        expect(page.locator('[data-view="capabilities"]')).to_be_hidden()
        page.locator("#layout-toggle").click()
        expect(page.locator(".app")).to_have_attribute("data-layout", "professional")
        page.get_by_role("button", name="发布准备", exact=True).click()
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
            for view in ("work", "tasks", "library", "capabilities"):
                page.locator(f'[data-view="{view}"]').click()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                    width,
                    view,
                )
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
                        "single/mixed model selection and per-task isolation",
                        "two simultaneous demo tasks and independent stop",
                        "artifact filtering and source task",
                        "review accept/reject",
                        "focus/professional layouts and capability center",
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
