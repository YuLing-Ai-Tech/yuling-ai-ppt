"""图元聚焦：点选、层数、压暗与隐藏、高亮路径、页面地图、修饰键。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_fixture, node, open_built_deck, open_deck, slide_with

pytestmark = pytest.mark.smoke


KEPT_IDS = "[...document.querySelectorAll('.slide.active .dg .is-kept[data-id]')].map(e => e.dataset.id).sort()"
NOT_FOCUSING = "document.querySelector('.dg.is-focusing') === null"
USER_OPACITY = "getComputedStyle(document.querySelector('.slide.active [data-id=\"user\"]')).opacity"
USER_VISIBILITY = "getComputedStyle(document.querySelector('.slide.active [data-id=\"user\"]')).visibility"


def test_click_node_focuses_neighbours_and_escape_restores(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.clock.install()
        assert page.evaluate(NOT_FOCUSING)
        page.click('.slide.active [data-id="api"]')
        assert page.evaluate(KEPT_IDS) == ["api", "db", "priv", "pub", "region", "vpc", "web"]
        page.wait_for_function(f"{USER_OPACITY} === '0.08'")
        page.keyboard.press("Escape")
        restored = page.evaluate(NOT_FOCUSING)
        browser.close()
    assert restored and errors == []


def test_click_again_or_blank_restores(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.click('.slide.active [data-id="api"]')
        focused = not page.evaluate(NOT_FOCUSING)
        page.click('.slide.active [data-id="api"]')
        again_restored = page.evaluate(NOT_FOCUSING)
        page.click('.slide.active [data-id="api"]')
        page.mouse.click(2, 2)
        blank_restored = page.evaluate(NOT_FOCUSING)
        browser.close()
    assert focused and again_restored and blank_restored and errors == []


def test_click_container_keeps_all_its_children(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.click('.slide.active [data-id="priv"] .tab')
        kept_ids = page.evaluate(KEPT_IDS)
        browser.close()
    assert "api" in kept_ids and "db" in kept_ids and "priv" in kept_ids and errors == []


def test_number_keys_switch_between_one_and_two_hops(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.click('.slide.active [data-id="user"]')
        one_hop = page.evaluate(KEPT_IDS)
        page.keyboard.press("2")
        two_hops = page.evaluate(KEPT_IDS)
        page.keyboard.press("1")
        back_to_one = page.evaluate(KEPT_IDS)
        browser.close()
    assert "web" not in one_hop and "web" in two_hops and back_to_one == one_hop and errors == []


def test_d_key_switches_between_dim_and_hide(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.click('.slide.active [data-id="api"]')
        dim_visibility = page.evaluate(USER_VISIBILITY)
        page.keyboard.press("d")
        hide_visibility = page.evaluate(USER_VISIBILITY)
        page.keyboard.press("d")
        dim_again = page.evaluate(USER_VISIBILITY)
        browser.close()
    assert [dim_visibility, hide_visibility, dim_again] == ["visible", "hidden", "visible"] and errors == []


def test_route_key_highlights_declared_path(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.keyboard.press("r")
        kept_ids = page.evaluate(KEPT_IDS)
        kept_edges = page.evaluate("[...new Set([...document.querySelectorAll('.slide.active .dg .is-kept[data-edge]')]"
                                   ".map(e => e.dataset.edge))].sort()")
        page.keyboard.press("r")
        cleared = page.evaluate(NOT_FOCUSING)
        browser.close()
    assert kept_ids == ["api", "lb", "priv", "pub", "region", "user", "vpc", "web"]
    assert kept_edges == ["lb→web", "user→lb", "web→api"]
    assert cleared and errors == []


def test_focus_is_cleared_when_page_changes(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.click('.slide.active [data-id="api"]')
        focused = not page.evaluate(NOT_FOCUSING)
        page.keyboard.press("Home")
        cleared = focused and page.evaluate(NOT_FOCUSING)
        browser.close()
    assert cleared and errors == []


def press_with_modifier(page, key, modifier):
    page.evaluate("([key, modifier]) => document.dispatchEvent(new KeyboardEvent('keydown', { key, [modifier]: true, bubbles: true }))",
                  [key, modifier])


def test_clicking_page_map_thumbnail_leaves_no_stale_focus(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
        page.keyboard.press("m")
        # 真鼠标点不到克隆页（.map-mini 是 pointer-events: none），所以用脚本点击直达克隆页里的节点
        page.evaluate("document.querySelector('.map-mini .dg-part[data-id=\"api\"]').click()")
        stale_marks = page.evaluate("document.querySelectorAll('.is-focusing, .is-kept').length")
        browser.close()
    assert stale_marks == 0 and errors == []


def test_opening_page_map_while_focused_copies_no_focus_marks_into_thumbnails(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.click('.slide.active [data-id="api"]')
        assert page.evaluate(KEPT_IDS) != []
        page.keyboard.press("m")
        mini_marks = page.evaluate("document.querySelectorAll('.map-mini .is-focusing, .map-mini .is-kept').length")
        browser.close()
    assert mini_marks == 0 and errors == []


def test_modifier_keys_do_not_trigger_focus_handlers(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.click('.slide.active [data-id="api"]')
        kept_before = page.evaluate(KEPT_IDS)
        press_with_modifier(page, "r", "ctrlKey")
        press_with_modifier(page, "d", "metaKey")
        press_with_modifier(page, "2", "altKey")
        press_with_modifier(page, "Escape", "ctrlKey")
        kept_after = page.evaluate(KEPT_IDS)
        hide_on = page.evaluate("document.body.classList.contains('focus-hide')")
        browser.close()
    assert kept_before and kept_after == kept_before and not hide_on and errors == []


def test_route_key_without_route_keeps_click_focus(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 3)
        page.click('.slide.active [data-id="hub"]')
        kept_before = page.evaluate(KEPT_IDS)
        page.keyboard.press("r")
        kept_after = page.evaluate(KEPT_IDS)
        browser.close()
    assert kept_before and kept_after == kept_before and errors == []


def test_route_key_cycles_through_every_route_then_restores(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.evaluate("document.querySelector('.slide.active .dg').insertAdjacentHTML('beforeend', "
                      "'<i class=\"route\" data-nodes=\"web api db\"></i>')")
        page.keyboard.press("r")
        first = page.evaluate(KEPT_IDS)
        page.keyboard.press("r")
        second = page.evaluate(KEPT_IDS)
        page.keyboard.press("r")
        cleared = page.evaluate(NOT_FOCUSING)
        browser.close()
    assert "user" in first and "user" not in second and "db" in second and cleared and errors == []


def test_same_id_in_two_diagrams_on_one_page_moves_focus_to_the_clicked_diagram(tmp_path):
    two_diagrams = slide_with(node("a"), node("a"))
    playwright, browser, page, errors = open_built_deck(tmp_path, {"01.html": two_diagrams}, 1)
    focused_diagram = "[...document.querySelectorAll('.slide.active .dg')].map(dg => dg.classList.contains('is-focusing'))"
    click_node_in_diagram = "index => document.querySelectorAll('.slide.active .dg')[index].querySelector('[data-id=\"a\"]').click()"
    page.evaluate(click_node_in_diagram, 0)
    after_first = page.evaluate(focused_diagram)
    page.evaluate(click_node_in_diagram, 1)
    after_second = page.evaluate(focused_diagram)
    browser.close()
    playwright.stop()
    assert after_first == [True, False] and after_second == [False, True] and errors == []
