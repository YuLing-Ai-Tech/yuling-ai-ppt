"""图元测试共用：构建夹具课件、打开课件、构建临时课件、跑预览。"""
import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests/fixtures"


def build_fixture(name, out_path):
    return subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(FIXTURES / name), "--engine-root", ".",
                           "--out", str(out_path)], cwd=REPO, capture_output=True, text=True)


def open_deck(playwright, deck_path, page_hash):
    chrome_path = os.environ.get("PPT_CHROME_PATH")
    launch_options = {"headless": True, "executable_path": chrome_path} if chrome_path else {"headless": True, "channel": "chrome"}
    browser = playwright.chromium.launch(**launch_options)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{deck_path.as_uri()}#{page_hash}")
    wait_for_entrance_settled(page)
    return browser, page, errors


ENTRANCE_SETTLED = """() => document.getAnimations().every(animation => animation.effect.getTiming().iterations === Infinity || animation.playState === 'finished')"""


def wait_for_entrance_settled(page):
    """翻页后等切入动画和过渡（有限次的）全部结束再读坐标或样式；无限循环的动画不算。"""
    page.wait_for_function(ENTRANCE_SETTLED)


def open_fixture_page(tmp_path, page_hash):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    playwright = sync_playwright().start()
    browser, page, errors = open_deck(playwright, tmp_path / "deck.html", page_hash)
    return playwright, browser, page, errors


def preview(deck_path, shot_dir):
    return subprocess.run([sys.executable, "tools/preview_slides.py", str(deck_path), str(shot_dir), "1200"], cwd=REPO,
                          capture_output=True, text=True)


def build_slides(tmp_path, slide_files):
    deck = tmp_path / "deck"
    (deck / "slides").mkdir(parents=True)
    (deck / "deck.json").write_text('{"title": "t", "output": "t.html", "style": "苹果风"}', encoding="utf-8")
    for name, body in slide_files.items():
        (deck / "slides" / name).write_text(body, encoding="utf-8")
    return subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(deck), "--engine-root", ".",
                           "--out", str(tmp_path / "out.html")], cwd=REPO, capture_output=True, text=True)


def slide_with(*diagram_bodies, dg_open='<div class="dg" data-grid="24 12">'):
    diagrams = "".join(f"{dg_open}{body}</div>" for body in diagram_bodies)
    return f'<section class="slide">{diagrams}</section>'


def node(node_id, parent=""):
    return f'<div class="node" data-id="{node_id}"{f" data-in={parent!r}" if parent else ""} data-at="1 1 4 2"></div>'


def open_built_deck(tmp_path, slide_files, page_hash):
    assert build_slides(tmp_path, slide_files).returncode == 0
    playwright = sync_playwright().start()
    browser, page, errors = open_deck(playwright, tmp_path / "out.html", page_hash)
    return playwright, browser, page, errors
