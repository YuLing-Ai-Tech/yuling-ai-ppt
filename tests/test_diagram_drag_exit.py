"""拖动模式的退出（Q-019 第 12 问）：翻页自动关、Esc 关；Esc 优先级 地图 > 拖动模式 > 聚焦。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_fixture, open_deck

pytestmark = pytest.mark.smoke

DRAG_ON = "document.body.classList.contains('drag-on')"
FOCUSING = "document.querySelector('.dg.is-focusing') !== null"
MAP_OPEN = "document.body.classList.contains('map-open')"
SWIPE = """() => { const target = document.querySelector('.slide.active');
  const touch = x => new Touch({ identifier: 1, target, clientX: x, clientY: 500 });
  target.dispatchEvent(new TouchEvent('touchstart', { bubbles: true, touches: [touch(900)], changedTouches: [touch(900)] }));
  target.dispatchEvent(new TouchEvent('touchend', { bubbles: true, touches: [], changedTouches: [touch(1200)] })); }"""


@pytest.fixture
def diagram_page(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.evaluate("document.getAnimations().forEach(a => { if (a.effect.getTiming().iterations !== Infinity) a.finish(); })")
        yield page, errors
        browser.close()


def click_node(page, node_id):
    page.locator(f'.slide.active [data-id="{node_id}"]').click()


def test_turning_page_closes_drag_mode_and_swipe_works_again(diagram_page):
    page, errors = diagram_page
    page.keyboard.press("t")
    assert page.evaluate(DRAG_ON)
    page.keyboard.press("End")
    assert page.evaluate(DRAG_ON) is False
    before = page.evaluate("location.hash")
    page.evaluate(SWIPE)
    assert page.evaluate("location.hash") != before and errors == []


def test_turning_page_mid_drag_keeps_and_records_the_move(diagram_page):
    page, errors = diagram_page
    box = page.locator('.slide.active [data-id="web"]').bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.keyboard.press("t")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + 60, steps=4)
    assert page.evaluate("document.querySelectorAll('.is-dragging').length") == 1
    page.keyboard.press("End")
    assert page.evaluate("document.querySelectorAll('.is-dragging').length") == 0  # 翻页当场结束这次拖动，不等松手
    assert page.evaluate(DRAG_ON) is False
    page.mouse.up()
    assert page.evaluate("document.body.classList.contains('drag-has-moves')") and errors == []


def test_escape_closes_drag_mode_and_keeps_focus_then_next_escape_clears_focus(diagram_page):
    page, errors = diagram_page
    click_node(page, "api")
    assert page.evaluate(FOCUSING)
    page.keyboard.press("t")
    page.keyboard.press("Escape")
    assert page.evaluate(DRAG_ON) is False and page.evaluate(FOCUSING)
    page.keyboard.press("Escape")
    assert page.evaluate(FOCUSING) is False and errors == []


def test_escape_with_map_open_closes_map_only(diagram_page):
    page, errors = diagram_page
    page.keyboard.press("t")
    page.keyboard.press("m")
    assert page.evaluate(MAP_OPEN)
    page.keyboard.press("Escape")
    assert page.evaluate(MAP_OPEN) is False and page.evaluate(DRAG_ON) and errors == []
    page.keyboard.press("Escape")
    assert page.evaluate(DRAG_ON) is False and errors == []


def test_escape_with_drag_off_still_clears_focus(diagram_page):
    page, errors = diagram_page
    click_node(page, "api")
    page.keyboard.press("Escape")
    assert page.evaluate(FOCUSING) is False and errors == []
