"""在 playwright 空白页里加载前端源文件和测试文件，跑 tests/js/unit-runner.js 登记的用例，返回每条结果。"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "tests/js/unit-runner.js"


def run_js_units(source_paths, test_path):
    """source_paths、test_path 相对仓库根。返回 (用例结果列表, 页面 JS 报错列表)。"""
    page_errors = []
    with sync_playwright() as playwright:
        chrome_path = os.environ.get("PPT_CHROME_PATH")
        launch_options = {"headless": True, "executable_path": chrome_path} if chrome_path else {"headless": True, "channel": "chrome"}
        browser = playwright.chromium.launch(**launch_options)
        try:
            page = browser.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto("about:blank")
            for path in [RUNNER, *(REPO / source for source in source_paths), REPO / test_path]:
                page.add_script_tag(content=path.read_text(encoding="utf-8"))
            results = page.evaluate("runUnitTests()")
        finally:
            browser.close()
    return results, page_errors
