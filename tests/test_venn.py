"""韦恩图冒烟：每段区域文字的中心落在且只落在它该落的圈里；集合名落在自己的圈里、不在别的圈里；圈是正圆。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_fixture, open_deck

pytestmark = pytest.mark.smoke

FINISH_ENTRANCES = "document.getAnimations().forEach(a => { if (a.effect.getTiming().iterations !== Infinity) a.finish(); })"
VENN_GEOMETRY = """() => {
  const venn = document.querySelector('.slide.active .venn');
  const center = element => { const rect = element.getBoundingClientRect(); return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }; };
  const circles = [...venn.querySelectorAll('.set')].map(set => { const rect = set.getBoundingClientRect();
    return { ...center(set), r: rect.width / 2, ratio: rect.width / rect.height, name: center(set.querySelector('b')) }; });
  const inside = point => circles.map((circle, index) => Math.hypot(point.x - circle.x, point.y - circle.y) < circle.r ? 'abc'[index] : '').join('');
  return { box: [venn.clientWidth, venn.clientHeight], ratios: circles.map(circle => circle.ratio),
    names: circles.map(circle => inside(circle.name)),
    regions: [...venn.querySelectorAll('.region')].map(region => [region.dataset.region, inside(center(region))]) };
}"""


def test_two_and_three_set_regions_sit_in_the_right_circles(tmp_path):
    assert build_fixture("韦恩", tmp_path / "venn.html").returncode == 0
    deck_path = tmp_path / "venn.html"
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, deck_path, 1)
        page.evaluate(FINISH_ENTRANCES)
        two = page.evaluate(VENN_GEOMETRY)
        page.evaluate("show(1)")
        page.evaluate(FINISH_ENTRANCES)
        three = page.evaluate(VENN_GEOMETRY)
        browser.close()
    assert errors == []
    assert all(abs(ratio - 1) < 0.01 for ratio in two["ratios"] + three["ratios"])
    assert abs(two["box"][0] / two["box"][1] - 1.6) < 0.01 and abs(three["box"][0] / three["box"][1] - 1) < 0.01
    assert two["names"] == ["a", "b"] and three["names"] == ["a", "b", "c"]
    assert all(region == inside for region, inside in two["regions"]), two["regions"]
    assert all(region == inside for region, inside in three["regions"]), three["regions"]
    assert sorted(region for region, _ in three["regions"]) == ["a", "ab", "abc", "ac", "b", "bc", "c"]
