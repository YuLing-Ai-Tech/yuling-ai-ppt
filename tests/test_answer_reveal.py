"""点击揭示答案：没揭示时遮罩可见、答案隐藏；点遮罩揭示到这一步；按 → 照常逐步揭示；回归截图（全部揭示）里没有遮罩。"""
import subprocess
import sys

import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import FIXTURES, REPO, open_deck

pytestmark = pytest.mark.smoke

STATE = """() => ['q1', 'q2', 'q3'].map(id => { const answer = document.getElementById(id);
  return [getComputedStyle(answer).visibility, getComputedStyle(answer, '::before').visibility,
    getComputedStyle(answer, '::before').content]; })"""


def build_answer_deck(tmp_path):
    built = subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(FIXTURES / "揭示答案"), "--engine-root", ".",
                            "--out", str(tmp_path / "answer.html")], cwd=REPO, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr


def open_deck_on_cover(playwright, tmp_path):
    build_answer_deck(tmp_path)
    return open_deck(playwright, tmp_path / "answer.html", 1)


def open_question_page(playwright, tmp_path):
    browser, page, errors = open_deck_on_cover(playwright, tmp_path)
    page.keyboard.press("ArrowRight")  # 顺序翻进来：第 0 步，三个答案都没揭示
    # 切页过渡里 .slide 的 visibility 要过一会才变 visible，答案继承它；不等的话读到的是过渡起点（约一半次数偶发红）
    page.wait_for_function("getComputedStyle(document.querySelector('.slide.active')).visibility === 'visible'")
    return browser, page, errors


def test_mask_shows_until_revealed_and_click_reveals_up_to_that_answer(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_question_page(playwright, tmp_path)
        before = page.evaluate(STATE)
        box = page.locator("#q2").bounding_box()  # 答案本身是 visibility:hidden，page.click 会等它可见；按真人点击的坐标点遮罩
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        after_click = page.evaluate(STATE)
        page.keyboard.press("ArrowRight")
        after_arrow = page.evaluate(STATE)
        hash_after = page.evaluate("location.hash")
        browser.close()
    assert errors == []
    assert before == [["hidden", "visible", '"?"'], ["hidden", "visible", '""'], ["hidden", "visible", '"?"']]
    # 点第 2 个：第 1、2 个揭示（遮罩消失），第 3 个还遮着
    assert [state[0] for state in after_click] == ["visible", "visible", "hidden"]
    assert [state[2] for state in after_click] == ["none", "none", '"?"']
    assert [state[0] for state in after_arrow] == ["visible", "visible", "visible"] and hash_after == "#2"


def test_jumping_to_the_page_shows_all_answers_without_masks(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_question_page(playwright, tmp_path)
        page.keyboard.press("End")
        page.keyboard.press("Home")
        page.evaluate("show(1)")
        state = page.evaluate(STATE)
        browser.close()
    assert errors == []
    assert [entry[0] for entry in state] == ["visible"] * 3 and [entry[2] for entry in state] == ["none"] * 3


def test_masks_on_other_pages_do_not_swallow_clicks(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_deck_on_cover(playwright, tmp_path)
        box = page.locator("#q2").bounding_box()  # 第 2 页的答案坐标，当前停在第 1 页（封面）
        hit_answer = page.evaluate("([x, y]) => !!document.elementFromPoint(x, y).closest('.answer')",
                                   [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
        browser.close()
    assert errors == []
    assert hit_answer is False


def test_clicking_a_revealed_answer_does_nothing_and_going_back_restores_the_mask(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_question_page(playwright, tmp_path)
        page.keyboard.press("ArrowRight")  # 揭示第 1 个
        page.locator("#q1").click()  # 已揭示的答案：点了不报错、状态不变
        after_click_revealed = page.evaluate(STATE)
        page.keyboard.press("ArrowLeft")  # 回退一步：第 1 个重新遮上
        after_back = page.evaluate(STATE)
        browser.close()
    assert errors == []
    assert [state[2] for state in after_click_revealed] == ["none", '""', '"?"']
    assert [state[2] for state in after_back] == ['"?"', '""', '"?"']
