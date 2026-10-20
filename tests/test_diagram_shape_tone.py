"""胶囊、圆形节点的 data-tone 色调（Q-022 B）：只在树布局、循环图的图区里显示；普通图（图元样板、甬舟）保持白底。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_slides, open_deck

pytestmark = pytest.mark.smoke

TREE = """<section class="slide"><div class="dg" data-grid="24 12" data-tree="down">
  <div class="node" data-id="root" data-shape="circle" data-tone="2" data-size="2 2"><b>根</b></div>
  <div class="node" data-id="kid" data-parent="root" data-shape="pill" data-tone="1"><b>枝</b></div>
  <div class="node" data-id="card" data-parent="root" data-tone="3"><b>卡</b></div></div></section>"""
CYCLE = """<section class="slide"><div class="dg" data-grid="24 12" data-cycle>
  <div class="node" data-id="a" data-shape="pill" data-tone="1"><b>甲</b></div>
  <div class="node" data-id="b" data-shape="pill" data-tone="4"><b>乙</b></div>
  <div class="node" data-id="c" data-shape="circle" data-tone="6" data-size="2 2"><b>丙</b></div></div></section>"""
PLAIN = """<section class="slide"><div class="dg" data-grid="24 12">
  <div class="node" data-id="p" data-shape="pill" data-tone="1" data-at="1 1 4 1.4"><b>胶囊</b></div>
  <div class="node" data-id="o" data-shape="circle" data-tone="2" data-at="7 1 2 2"><b>圆</b></div></div></section>"""

# 描边色、::before 底色（节点本身不能降透明度，否则文字变淡）、::before 透明度
READ_STYLES = """() => Object.fromEntries([...document.querySelectorAll('.slide.active .dg .node')].map(node => {
  const tint = getComputedStyle(node, '::before'), box = getComputedStyle(node);
  return [node.dataset.id, { border: box.borderTopColor, background: box.backgroundColor, tint: tint.backgroundColor,
    tintShown: tint.display !== 'none', tintOpacity: tint.opacity }];
}))"""
CAT_COLOR = {1: "rgb(0, 113, 227)", 2: "rgb(255, 149, 0)", 3: "rgb(52, 199, 89)", 4: "rgb(175, 82, 222)", 6: "rgb(48, 176, 199)"}


def styles_of(tmp_path, slide_html):
    assert build_slides(tmp_path, {"01_x.html": slide_html}).returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "out.html", 1)
        styles = page.evaluate(READ_STYLES)
        browser.close()
    assert errors == []
    return styles


def assert_toned(style, cat):
    assert style["border"] == CAT_COLOR[cat]
    assert style["tint"] == CAT_COLOR[cat] and style["tintShown"] and float(style["tintOpacity"]) == 0.13


def test_tree_pill_and_circle_show_their_tone(tmp_path):
    styles = styles_of(tmp_path, TREE)
    assert_toned(styles["root"], 2)
    assert_toned(styles["kid"], 1)


def test_cycle_pill_and_circle_show_their_tone(tmp_path):
    styles = styles_of(tmp_path, CYCLE)
    assert_toned(styles["a"], 1)
    assert_toned(styles["b"], 4)
    assert_toned(styles["c"], 6)


def test_plain_diagram_pill_and_circle_stay_untoned(tmp_path):
    styles = styles_of(tmp_path, PLAIN)
    for node_id in ("p", "o"):
        assert styles[node_id]["border"] != CAT_COLOR[1] and styles[node_id]["border"] != CAT_COLOR[2]
        assert styles[node_id]["tintShown"] is False


def test_tree_card_node_keeps_its_stripe_not_the_shape_tint(tmp_path):
    card = styles_of(tmp_path, TREE)["card"]
    assert card["tintShown"] and card["tintOpacity"] == "1" and card["border"] != CAT_COLOR[3]
