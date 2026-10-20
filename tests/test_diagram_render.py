"""图元渲染：嵌套图、原子、形状、标签页，构建夹具后在浏览器里读几何与样式。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_fixture, open_deck, open_fixture_page

pytestmark = pytest.mark.smoke


def test_nested_diagram_renders_all_edges_without_problems(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        counts = page.evaluate("[document.querySelectorAll('.slide.active .dg .wire').length, "
                               "document.querySelectorAll('.slide.active .dg-label').length, window.diagramProblems]")
        browser.close()
    assert counts == [5, 4, []] and errors == []


BOX_GEOMETRY_SCRIPT = """() => {
  const dg = document.querySelector('.slide.active .dg');
  const style = id => getComputedStyle(dg.querySelector(`[data-id="${id}"]`));
  const px = id => ['left', 'top', 'width', 'height'].map(name => parseFloat(style(id)[name]));
  return { width: dg.clientWidth, height: dg.clientHeight, dst: px('dst'), start: px('start'), lane: px('lane') };
}"""

EDGE_PARTS_SCRIPT = """() => [...document.querySelectorAll('.slide.active .dg .wire, .slide.active .dg .dg-label')].map(part => ({
  tag: part.tagName.toLowerCase(), edge: part.dataset.edge, kind: part.dataset.kind, step: part.dataset.step || null }))"""


def test_atoms_page_renders_and_boxes_land_on_grid(tmp_path):
    playwright, browser, page, errors = open_fixture_page(tmp_path, 3)
    try:
        wire_count = page.evaluate("document.querySelectorAll('.slide.active .dg .wire').length")
        placed_count = page.evaluate("document.querySelectorAll('.slide.active .dg .dg-part').length")
        geometry = page.evaluate(BOX_GEOMETRY_SCRIPT)
        problems = page.evaluate("window.diagramProblems")
    finally:
        browser.close()
        playwright.stop()
    cell_w, cell_h = geometry["width"] / 24, geometry["height"] / 12
    # Chrome 把布局吸附到 1/64 px（约 0.011px 残差）；容许 0.05px 仍能抓出 1px 错位
    # dst 直接在图区里：data-at="11.5 5.5 1.4 1"
    expected_dst = [11.5 * cell_w, 5.5 * cell_h, 1.4 * cell_w, 1 * cell_h]
    assert all(abs(actual - expected) < 0.05 for actual, expected in zip(geometry["dst"], expected_dst))
    lane_left, lane_top = 0 * cell_w, 1 * cell_h
    expected_start = [lane_left + 1.3 * cell_w, lane_top + 0.7 * cell_h, 3 * cell_w, 1.6 * cell_h]
    assert all(abs(actual - expected) < 0.05 for actual, expected in zip(geometry["start"], expected_start))
    assert wire_count == 3 and placed_count == 17 and problems == [] and errors == []


def test_wires_and_labels_carry_edge_id_kind_and_step(tmp_path):
    playwright, browser, page, errors = open_fixture_page(tmp_path, 2)
    try:
        parts = page.evaluate(EDGE_PARTS_SCRIPT)
    finally:
        browser.close()
        playwright.stop()
    expected = {"user→lb": ("sync", "2"), "web→api": ("sync", "3"), "api→db": ("data", "3"), "db→pub": ("async", "3"),
                "lb→web": ("sync", "2")}
    assert sorted((part["tag"], part["edge"]) for part in parts) == sorted(
        [("path", edge) for edge in expected] + [("span", edge) for edge in expected if edge != "lb→web"])
    for part in parts:
        assert (part["kind"], part["step"]) == expected[part["edge"]], part
    assert errors == []


def test_tab_moves_to_bottom_when_a_wire_crosses_its_top(tmp_path):
    playwright, browser, page, errors = open_fixture_page(tmp_path, 3)
    try:
        tab_side = page.evaluate("[...document.querySelectorAll('.slide.active .dg .zone')].map(zone => "
                                 "[zone.dataset.id, zone.classList.contains('tab-bottom')])")
        untouched_side = page.evaluate("document.querySelector('.slide.active .dg .quadrant').classList.contains('tab-bottom')")
    finally:
        browser.close()
        playwright.stop()
    assert tab_side == [["cage", True]] and untouched_side is False and errors == []


ATOMS_SCRIPT = """() => {
  const slide = document.querySelector('.slide.active');
  return {
    legend: [...slide.querySelectorAll('.legend span')].map(item => item.textContent),
    ticks: [...slide.querySelectorAll('.axis .tick')].map(tick => tick.style.left),
    axisTitles: [...slide.querySelectorAll('.quadrant .axis-title')].map(title => title.textContent),
    diamond: getComputedStyle(slide.querySelector('[data-id="judge"]'), '::after').clipPath,
    curve: slide.querySelector('.dg-wires .wire[data-edge="hub→judge"]').getAttribute('d').includes(' C '),
    problems: window.diagramProblems,
  };
}"""


def test_atoms_render_legend_axis_quadrant_and_shapes(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 3)
        atoms = page.evaluate(ATOMS_SCRIPT)
        browser.close()
    assert atoms == {"legend": ["同步调用", "写库"], "ticks": ["0%", "33.3333%", "66.6667%", "100%"],
                     "axisTitles": ["难度 →", "↑ 价值"], "diamond": "polygon(50% 0px, 100% 50%, 50% 100%, 0px 50%)",
                     "curve": True, "problems": []}
    assert errors == []


LANE_AND_SHAPES_SCRIPT = """() => {
  const slide = document.querySelector('.slide.active');
  const style = (selector, pseudo) => getComputedStyle(slide.querySelector(selector), pseudo);
  return {
    laneTitleMode: style('.lane > b').writingMode,
    laneTitleWidth: parseFloat(style('.lane > b').width),
    cellWidth: parseFloat(getComputedStyle(slide.querySelector('.dg')).getPropertyValue('--cell-w')),
    pillRadius: style('[data-id="start"]').borderTopLeftRadius,
    circleRadius: style('[data-id="hub"]').borderTopLeftRadius,
    legendLine: style('.legend span[data-kind="data"] i').borderTopColor,
    dataWire: style('.dg-wires .wire[data-kind="data"]').stroke,
    captionMargin: parseFloat(style('.dg-caption').marginTop),
  };
}"""


def test_lane_shapes_legend_line_and_caption_are_styled(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 3)
        styled = page.evaluate(LANE_AND_SHAPES_SCRIPT)
        browser.close()
    assert styled["laneTitleMode"] == "vertical-rl"
    assert abs(styled["laneTitleWidth"] - styled["cellWidth"]) < 0.5
    assert styled["pillRadius"] == "999px" and styled["circleRadius"] == "50%"
    assert styled["legendLine"] == styled["dataWire"] != ""
    assert styled["captionMargin"] == 10 and errors == []
