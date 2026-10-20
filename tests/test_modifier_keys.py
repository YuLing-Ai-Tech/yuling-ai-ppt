"""放映快捷键 P、F、M 带 Cmd/Ctrl/Alt 时是浏览器或系统的快捷键（打印、查找、最小化），不应触发放映动作；不带修饰键照常。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_fixture, open_deck

pytestmark = pytest.mark.smoke

PLAY_LABEL = "document.getElementById('play').textContent"
MAP_OPEN = "document.body.classList.contains('map-open')"
COUNT_FULLSCREEN = "window.fullscreenRequests"
COUNT_FULLSCREEN_STUB = "window.fullscreenRequests = 0; document.documentElement.requestFullscreen = () => { window.fullscreenRequests += 1; return Promise.resolve(); }; 0"
MODIFIERS = ["Meta", "Control", "Alt"]


def open_cover(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    playwright = sync_playwright().start()
    browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
    page.evaluate(COUNT_FULLSCREEN_STUB)
    return playwright, browser, page, errors


@pytest.mark.parametrize("modifier", MODIFIERS)
def test_modifier_plus_p_f_m_does_nothing(tmp_path, modifier):
    playwright, browser, page, errors = open_cover(tmp_path)
    try:
        label_before = page.evaluate(PLAY_LABEL)
        for key in "pfm":
            page.keyboard.press(f"{modifier}+{key}")
        state = [page.evaluate(PLAY_LABEL), page.evaluate(MAP_OPEN), page.evaluate(COUNT_FULLSCREEN)]
    finally:
        browser.close()
        playwright.stop()
    assert errors == []
    assert state == [label_before, False, 0]


def test_plain_p_f_m_still_work(tmp_path):
    playwright, browser, page, errors = open_cover(tmp_path)
    try:
        page.keyboard.press("f")
        fullscreen_requests = page.evaluate(COUNT_FULLSCREEN)
        page.keyboard.press("m")
        map_open = page.evaluate(MAP_OPEN)
        page.keyboard.press("m")
        page.keyboard.press("p")
        label_playing = page.evaluate(PLAY_LABEL)
        page.keyboard.press("p")
    finally:
        browser.close()
        playwright.stop()
    assert errors == []
    assert (fullscreen_requests, map_open, label_playing) == (1, True, "暂停")
