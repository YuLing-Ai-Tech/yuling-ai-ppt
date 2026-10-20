"""逐页截图检查课件：等动画落定后截图，并报告 JS 报错、压到导航栏 / 超出舞台的元素、图元连线检查的问题。

用法：python3 preview_slides.py <课件.html> <截图目录> [每页等待毫秒，默认 3800]
有 JS 报错、溢出或连线检查问题时退出码为 1。截图文件名 p01.png、p02.png ……
"""

import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

OVERFLOW_CHECK = """() => {
  const slide = document.querySelector('.slide.active');
  const stage = document.getElementById('stage').getBoundingClientRect();
  const scale = stage.width / 1920;
  const limitBottom = stage.top + (1080 - 110) * scale;
  const bad = [];
  slide.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || getComputedStyle(el).position === 'absolute') return;
    if (r.bottom > limitBottom + 2 || r.right > stage.right + 2) bad.push((el.className || el.tagName) + ' ' + Math.round((r.bottom - limitBottom) / scale) + 'px');
  });
  return bad.slice(0, 3);
}"""


async def preview(deck_path, shot_dir, settle_ms):
    shot_dir.mkdir(parents=True, exist_ok=True)
    overflow_pages = []
    async with async_playwright() as playwright:
        chrome_path = os.environ.get("PPT_CHROME_PATH")
        launch_options = {"headless": True, "executable_path": chrome_path} if chrome_path else {"headless": True, "channel": "chrome"}
        browser = await playwright.chromium.launch(**launch_options)
        page = await browser.new_page(viewport={"width": 1600, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(deck_path.resolve().as_uri())
        await page.wait_for_timeout(settle_ms)
        total = await page.evaluate("document.querySelectorAll('.slide').length")
        # 图元在启动时渲染并检查全部页（components/diagram/render.js），结果一次读出
        diagram_problems = await page.evaluate("window.diagramProblems || []")
        for problem in diagram_problems:
            print(f"连线检查：第 {problem['page']} 页 {problem['id']}：{problem['problem']}")
        for index in range(1, total + 1):
            if index > 1:
                # 直接跳页（runtime/deck.js 的 show）：跳页时本页 data-step 全部揭示；按 → 会先逐步揭示，页码对不上
                await page.evaluate(f"show({index - 1})")
                await page.wait_for_timeout(settle_ms)
            await page.screenshot(path=str(shot_dir / f"p{index:02d}.png"))
            overflow = await page.evaluate(OVERFLOW_CHECK)
            if overflow:
                overflow_pages.append(index)
                print(f"第 {index} 页可能溢出：{overflow}")
        print(f"共 {total} 页；JS 报错：{errors or '无'}；溢出页：{overflow_pages or '无'}；连线检查：{len(diagram_problems) or '无'}")
        await browser.close()
    return not errors and not overflow_pages and not diagram_problems


if __name__ == "__main__":
    passed = asyncio.run(preview(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 3800))
    sys.exit(0 if passed else 1)
