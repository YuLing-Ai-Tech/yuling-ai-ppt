"""拖动后存回源文件（Q-017 D2 形态 B）的整条链：构建 → 放映里拖 → 保存位置 → apply_positions 写回 → 重新构建 → 位置还在。"""
import json
import shutil
import subprocess
import sys

import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import FIXTURES, REPO, open_deck
from tests.test_diagram_drag import cell_size, mouse_drag

pytestmark = pytest.mark.smoke

NO_PICKER = "delete window.showSaveFilePicker;"  # 模拟没有"另存为"接口的浏览器（Safari、Firefox）
FAKE_PICKER = """window.savedPositions = null;
window.showSaveFilePicker = async options => ({ createWritable: async () => ({
  write: async text => { window.savedPositions = { name: options.suggestedName, text }; }, close: async () => {} }) });"""
CANCELLED_PICKER = """window.showSaveFilePicker = async () => { throw new DOMException("用户取消", "AbortError"); };"""
BROKEN_PICKER = """window.showSaveFilePicker = async () => { throw new DOMException("被安全策略拦下", "SecurityError"); };"""  # 不是用户取消


def build(deck_dir, out_path):
    result = subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(deck_dir), "--engine-root", ".", "--out", str(out_path)],
                            cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return out_path


def drag_web_down_one_row(page):
    page.keyboard.press("t")
    _, cell_h = cell_size(page)
    mouse_drag(page, "web", 0, cell_h)


def test_download_fallback_round_trips_into_the_source_file(tmp_path):
    deck_dir = tmp_path / "deck"
    shutil.copytree(FIXTURES / "图元冒烟", deck_dir)
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, build(deck_dir, tmp_path / "a.html"), 2)
        page.add_init_script(NO_PICKER)
        page.reload()
        drag_web_down_one_row(page)
        save_visible = page.evaluate("getComputedStyle(document.getElementById('drag-save')).visibility")
        with page.expect_download() as download_info:
            page.click("#drag-save")
        download = download_info.value
        positions_path = tmp_path / download.suggested_filename
        download.save_as(positions_path)
        browser.close()
    assert save_visible == "visible" and download.suggested_filename == "图元冒烟-位置.json" and errors == []
    assert json.loads(positions_path.read_text(encoding="utf-8"))["moves"] == [
        {"page": 2, "source": "02_嵌套图.html", "diagram": 0, "id": "web", "at": "0.5 5.5 6 1.8", "was": "0.5 4.5 6 1.8"}]
    applied = subprocess.run([sys.executable, "tools/apply_positions.py", "--deck", str(deck_dir), str(positions_path)],
                             cwd=REPO, capture_output=True, text=True)
    assert applied.returncode == 0 and "写回 1 处" in applied.stdout
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, build(deck_dir, tmp_path / "b.html"), 2)
        rebuilt_at = page.evaluate("document.querySelector('.slide.active [data-id=\"web\"]').dataset.at")
        problems = page.evaluate("window.diagramProblems")
        browser.close()
    assert rebuilt_at == "0.5 5.5 6 1.8" and problems == [] and errors == []


def test_chrome_picker_gets_the_file_and_ctrl_s_saves_only_in_drag_mode(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, build(FIXTURES / "图元冒烟", tmp_path / "a.html"), 2)
        page.add_init_script(FAKE_PICKER)
        page.reload()
        drag_web_down_one_row(page)
        page.keyboard.press("ControlOrMeta+s")
        page.wait_for_function("window.savedPositions !== null")
        saved = page.evaluate("window.savedPositions")
        page.keyboard.press("t")  # 关掉拖动模式后 Ctrl/Cmd+S 不再存
        page.evaluate("window.savedPositions = null")
        page.keyboard.press("ControlOrMeta+s")
        page.wait_for_timeout(200)
        after_off = page.evaluate("window.savedPositions")
        browser.close()
    assert saved["name"] == "图元冒烟-位置.json" and json.loads(saved["text"])["format"] == "yuling-positions-1"
    assert json.loads(saved["text"])["moves"][0]["at"] == "0.5 5.5 6 1.8"
    assert after_off is None and errors == []


def test_picker_failure_other_than_cancel_falls_back_to_download(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, build(FIXTURES / "图元冒烟", tmp_path / "a.html"), 2)
        page.add_init_script(BROKEN_PICKER)
        page.reload()
        drag_web_down_one_row(page)
        with page.expect_download(timeout=5000) as download_info:
            page.click("#drag-save")
        name = download_info.value.suggested_filename
        browser.close()
    assert name == "图元冒烟-位置.json" and errors == []


def test_cancelled_picker_neither_downloads_nor_errors(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, build(FIXTURES / "图元冒烟", tmp_path / "a.html"), 2)
        page.add_init_script(CANCELLED_PICKER)
        page.reload()
        downloads = []
        page.on("download", lambda download: downloads.append(download))
        drag_web_down_one_row(page)
        page.click("#drag-save")
        page.wait_for_timeout(1000)
        browser.close()
    assert downloads == [] and errors == []
