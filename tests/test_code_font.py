"""代码块的字体走令牌 --mono：换风格改这一个令牌，代码块和图元的等宽字一起跟着变。"""
import pytest

from tests.diagram_helpers import open_built_deck

pytestmark = pytest.mark.smoke

CODE_SLIDE = '<section class="slide"><h2>代码</h2><div class="code">print("hi")</div></section>'


def test_code_block_font_follows_mono_token(tmp_path):
    playwright, browser, page, errors = open_built_deck(tmp_path, {"01_code.html": CODE_SLIDE}, 1)
    try:
        page.evaluate("document.documentElement.style.setProperty('--mono', 'Courier')")
        font_family = page.evaluate("getComputedStyle(document.querySelector('.slide.active .code')).fontFamily")
    finally:
        browser.close()
        playwright.stop()
    assert font_family == "Courier" and errors == []
