"""数据图边界冒烟：多组柱图的图例不压数值标签、柱很多时动画仍在 6 秒内做完、坐标算不出有限数时不画并报页码。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import open_deck
from tests.test_charts import build_charts

pytestmark = pytest.mark.smoke

BOXES_OVERLAP = """(() => {
  const legend = document.querySelector('.slide.active .chart-legend').getBBox();
  return [...document.querySelectorAll('.slide.active .chart .value-label')].map(label => {
    const box = label.getBBox();
    return legend.x < box.x + box.width && box.x < legend.x + legend.width && legend.y < box.y + box.height && box.y < legend.y + legend.height;
  });
})()"""
LAST_ANIMATION_END_MS = """Math.max(...[...document.querySelectorAll('.slide.active .chart')].flatMap(figure => figure.getAnimations({ subtree: true }))
  .map(animation => animation.effect.getComputedTiming().endTime))"""


@pytest.fixture
def edge_page(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, build_charts(tmp_path, "数据图-边界"), 1)
        yield page, errors
        browser.close()


def test_legend_does_not_cover_value_labels_when_max_equals_top_tick(edge_page):
    page, errors = edge_page
    assert page.evaluate("document.querySelectorAll('.slide.active .chart .value-label').length") == 6
    assert page.evaluate(BOXES_OVERLAP) == [False] * 6 and errors == []


def test_many_bars_still_finish_within_six_seconds(edge_page):
    page, errors = edge_page
    page.evaluate("show(1)")
    assert page.evaluate("document.querySelectorAll('.slide.active .chart .bar').length") == 80
    assert page.evaluate(LAST_ANIMATION_END_MS) <= 6000 and errors == []


def test_non_finite_coordinates_are_not_drawn_and_are_reported(edge_page):
    page, errors = edge_page
    page.evaluate("show(2)")
    assert page.evaluate("document.querySelectorAll('.slide.active .chart svg *').length") == 0
    problems = page.evaluate("window.diagramProblems")
    assert [(problem["page"], problem["id"]) for problem in problems] == [(3, "数据图 line")]
