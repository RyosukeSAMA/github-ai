import functools
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parents[1]


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def contrast(foreground, background):
    def luminance(color):
        value = color.strip().lstrip("#")
        if len(value) == 3:
            value = "".join(char * 2 for char in value)
        channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    values = sorted((luminance(foreground), luminance(background)))
    return (values[1] + 0.05) / (values[0] + 0.05)


def check_palette(page):
    tokens = page.evaluate("""() => {
        const style = getComputedStyle(document.querySelector('.app'));
        return Object.fromEntries(['surface','panel','ink','muted','accent','accent-soft',
          'on-accent','green','gold','red'].map(key => [key, style.getPropertyValue('--'+key).trim()]));
    }""")
    pairs = [
        ("ink", "surface"),
        ("muted", "panel"),
        ("muted", "accent-soft"),
        ("accent", "surface"),
        ("on-accent", "accent"),
        ("green", "surface"),
        ("gold", "surface"),
        ("red", "surface"),
    ]
    ratios = {f"{fg}/{bg}": round(contrast(tokens[fg], tokens[bg]), 2) for fg, bg in pairs}
    assert all(ratio >= 4.5 for ratio in ratios.values()), ratios
    return ratios


for name in ("index.html", "prototype.js"):
    assert not re.search(r"[\u3400-\u9fff]", (root / "desktop" / name).read_text()), name

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
        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator(".app").get_attribute("data-theme") == "light"
        assert (
            page.locator(".main").evaluate("el => getComputedStyle(el).backgroundColor")
            == "rgb(255, 255, 255)"
        )
        light_contrast = check_palette(page)
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
        expect(page.locator("#review-state")).to_contain_text("Changes requested")
        page.locator("#review-accept").click()
        expect(page.locator("#review-state")).to_contain_text("No files written")
        page.locator('[data-view="library"]').click()
        expect(page.locator(".artifact-tile")).to_have_count(3)
        page.locator('[data-kind="research"]').click()
        expect(page.locator(".artifact-tile")).to_have_count(1)
        page.locator(".artifact-tile").click()
        expect(page.locator("#breadcrumb-task")).to_have_text("Compare data stores")
        page.locator("#prompt").fill("Draft for the research task only")
        page.locator('[data-mode="multi"]').click()
        page.locator("#model-open").click()
        expect(page.locator('[name="model-mode"][value="single"]')).to_be_checked()
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Launch preparation", exact=True).click()
        expect(page.locator("#prompt")).to_have_value("")
        expect(page.locator('[data-mode="auto"]')).to_have_class("selected")
        page.get_by_role("button", name="Compare data stores", exact=True).click()
        expect(page.locator("#prompt")).to_have_value("Draft for the research task only")
        expect(page.locator('[data-mode="multi"]')).to_have_class("selected")
        page.locator('[data-view="tasks"]').click()
        rows = page.locator(".mission-row")
        rows.nth(1).get_by_role("button", name="Run demo", exact=True).click()
        rows.nth(2).get_by_role("button", name="Run demo", exact=True).click()
        expect(page.locator("#metric-running")).to_have_text("2")
        page.evaluate("document.querySelector('#toast').hidden = true")
        page.screenshot(path=str(root / "desktop/preview-tasks.png"))
        rows.nth(1).get_by_role("button", name="Stop demo", exact=True).click()
        expect(page.locator("#metric-running")).to_have_text("1")
        expect(rows.nth(1)).to_contain_text("Stopped")
        expect(rows.nth(2).get_by_role("button", name="Stop demo", exact=True)).to_be_visible()
        rows.nth(2).get_by_role("button", name="Stop demo", exact=True).click()
        page.locator('[data-view="capabilities"]').click()
        expect(page.locator(".capability-grid>button")).to_have_count(6)
        page.locator('[data-capability="desktop"]').click()
        expect(page.locator("#info-dialog")).to_contain_text("not implemented yet")
        page.keyboard.press("Escape")
        page.locator("#focus-preview").click()
        expect(page.locator(".app")).to_have_attribute("data-layout", "focus")
        expect(page.locator('[data-view="capabilities"]')).to_be_hidden()
        page.locator("#layout-toggle").click()
        expect(page.locator(".app")).to_have_attribute("data-layout", "professional")
        page.get_by_role("button", name="Launch preparation", exact=True).click()
        page.locator("#approval-open").click()
        page.locator("#deny-approval").click()
        expect(page.locator("#activity-list")).to_contain_text("Demo approval: denied")
        page.locator("#files-tab").click()
        expect(page.locator("#file-content")).to_contain_text("Launch checklist")
        page.locator("#terminal-toggle").click()
        page.locator("#terminal-simulate").click()
        expect(page.locator("#terminal-output")).to_contain_text("No shell command was run")
        page.locator("#terminal-close").click()
        page.locator("#new-task").click()
        page.locator("#new-prompt").fill("Write delivery notes")
        page.get_by_role("button", name="Create demo task", exact=True).click()
        expect(page.locator("#task-list")).to_contain_text("Write delivery notes")
        page.locator("#run-demo").click()
        expect(page.locator("#run-demo")).to_contain_text("Stop demo")
        page.locator("#run-demo").click()
        expect(page.locator("#task-state")).to_contain_text("Stopped")
        page.keyboard.press("Control+k")
        page.locator("#command-search").fill("assign role")
        page.locator("#command-list button").click()
        expect(page.locator("#models-dialog")).to_be_visible()
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Launch preparation", exact=True).click()
        page.locator("#result-tab").click()
        page.evaluate("document.querySelector('#toast').hidden = true")
        page.locator("#theme-toggle").click()
        dark_contrast = check_palette(page)
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
                        "English UI and accessibility labels",
                        "white-first default and readable palette contrasts",
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
                    "language": "en",
                    "light_contrast_ratios": light_contrast,
                    "dark_contrast_ratios": dark_contrast,
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
