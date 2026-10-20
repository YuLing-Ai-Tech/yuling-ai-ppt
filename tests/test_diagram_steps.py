"""分步揭示：方向键、跳页、页面地图、自动播放、章节页。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_fixture, open_built_deck, open_deck, wait_for_entrance_settled

pytestmark = pytest.mark.smoke


SHOWN_STEPS = ("[...document.querySelectorAll('.slide.active [data-step]')].filter(e => e.classList.contains('step-shown'))"
               ".map(e => Number(e.dataset.step)).reduce((a, b) => Math.max(a, b), 0)")


def test_arrow_key_reveals_steps_before_turning_page(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
        page.keyboard.press("ArrowRight")
        assert (page.evaluate("location.hash"), page.evaluate(SHOWN_STEPS)) == ("#2", 0)
        for expected in (1, 2, 3):
            page.keyboard.press("ArrowRight")
            assert (page.evaluate("location.hash"), page.evaluate(SHOWN_STEPS)) == ("#2", expected)
        page.keyboard.press("ArrowRight")
        assert page.evaluate("location.hash") == "#3"
        page.keyboard.press("ArrowLeft")
        assert (page.evaluate("location.hash"), page.evaluate(SHOWN_STEPS)) == ("#2", 3)
        page.keyboard.press("ArrowLeft")
        assert (page.evaluate("location.hash"), page.evaluate(SHOWN_STEPS)) == ("#2", 2)
        browser.close()
    assert errors == []


def test_jumping_to_page_reveals_all_steps_and_map_copy_too(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        assert page.evaluate(SHOWN_STEPS) == 3
        browser.close()
    assert errors == []


def test_map_copy_of_unvisited_page_shows_all_steps(tmp_path):
    # 从第 1 页打开：第 2 页没进过，原页上没有 .step-shown，缩略图副本必须自己揭示全部
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
        page.keyboard.press("m")
        counts = page.evaluate("[document.querySelectorAll('.map-mini [data-step]').length, "
                               "document.querySelectorAll('.map-mini [data-step]:not(.step-shown)').length]")
        browser.close()
    assert counts[0] > 0 and counts[1] == 0 and errors == []


def test_autoplay_reveals_steps_one_interval_each_before_turning_page(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
        page.clock.install()
        page.keyboard.press("p")
        readings = []
        for _ in range(5):
            page.clock.run_for(9000)
            readings.append((page.evaluate("location.hash"), page.evaluate(SHOWN_STEPS)))
        browser.close()
    assert readings == [("#2", 0), ("#2", 1), ("#2", 2), ("#2", 3), ("#3", 0)] and errors == []


STEP_STATE = """() => [...document.querySelectorAll('.slide.active [data-step]')].map(e => {
  const style = getComputedStyle(e);
  return [e.dataset.step, e.classList.contains('step-shown'), style.visibility, style.animationName];
})"""


def stepped_slide(step_numbers, chapter=False):
    parts = "".join(f'<div data-step="{number}">s{number}</div>' for number in step_numbers)
    return f'<section class="slide{" chapter" if chapter else ""}"><h2>标题</h2>{parts}</section>'


def test_unrevealed_step_is_hidden_and_revealed_step_is_visible_by_computed_style(tmp_path):
    playwright, browser, page, errors = open_built_deck(
        tmp_path, {"01_a.html": stepped_slide([]), "02_b.html": stepped_slide([1, 2])}, 1)
    try:
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        wait_for_entrance_settled(page)  # 页面切入有 1 秒 visibility 过渡
        state = page.evaluate(STEP_STATE)
    finally:
        browser.close()
        playwright.stop()
    assert state == [["1", True, "visible", "none"], ["2", False, "hidden", "none"]] and errors == []


def test_non_contiguous_step_numbers_take_one_press_per_distinct_step(tmp_path):
    playwright, browser, page, errors = open_built_deck(
        tmp_path, {"01_a.html": stepped_slide([]), "02_b.html": stepped_slide([1, 3]), "03_c.html": stepped_slide([])}, 1)
    try:
        readings = []
        for _ in range(4):
            page.keyboard.press("ArrowRight")
            readings.append((page.evaluate("location.hash"), page.evaluate(SHOWN_STEPS)))
        page.keyboard.press("ArrowLeft")
        page.keyboard.press("ArrowLeft")
        after_back = (page.evaluate("location.hash"), page.evaluate(SHOWN_STEPS))
    finally:
        browser.close()
        playwright.stop()
    assert readings == [("#2", 0), ("#2", 1), ("#2", 3), ("#3", 0)] and after_back == ("#2", 1) and errors == []


def test_elements_sharing_a_step_number_appear_on_the_same_press(tmp_path):
    playwright, browser, page, errors = open_built_deck(
        tmp_path, {"01_a.html": stepped_slide([]), "02_b.html": stepped_slide([1, 2, 2])}, 1)
    try:
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        shown = page.evaluate("[...document.querySelectorAll('.slide.active [data-step]')].map(e => e.classList.contains('step-shown'))")
    finally:
        browser.close()
        playwright.stop()
    assert shown == [True, True, True] and errors == []


def test_arrow_right_on_last_page_leaves_revealed_steps_alone(tmp_path):
    playwright, browser, page, errors = open_built_deck(tmp_path, {"01_a.html": stepped_slide([]), "02_b.html": stepped_slide([1, 2])}, 2)
    try:
        page.evaluate("() => { window.enterCalls = 0; const original = enterSteps; enterSteps = (...args) => { window.enterCalls++; return original(...args); }; }")
        page.keyboard.press("ArrowRight")
        result = (page.evaluate("location.hash"), page.evaluate(SHOWN_STEPS), page.evaluate("window.enterCalls"))
    finally:
        browser.close()
        playwright.stop()
    assert result == ("#2", 2, 0) and errors == []


def test_chapter_page_with_steps_runs_wipe_and_starts_at_step_zero(tmp_path):
    playwright, browser, page, errors = open_built_deck(
        tmp_path, {"01_a.html": stepped_slide([]), "02_b.html": stepped_slide([1, 2], chapter=True)}, 1)
    try:
        page.keyboard.press("ArrowRight")
        wipe_running = page.evaluate("document.getElementById('wipe').classList.contains('run')")
        at_entry = page.evaluate(SHOWN_STEPS)
        page.keyboard.press("ArrowRight")
        after_press = page.evaluate(SHOWN_STEPS)
    finally:
        browser.close()
        playwright.stop()
    assert (wipe_running, at_entry, after_press) == (True, 0, 1) and errors == []
