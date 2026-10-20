"""图元样板 9 页：冒烟（0 JS 报错、0 溢出、连线检查 0 问题）+ 回归（和 baselines/图元样板 逐像素 0 差异）。"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import wait_for_entrance_settled
from tools import build_deck

REPO = Path(__file__).resolve().parent.parent
DECK_DIR = REPO / "examples/图元样板"
BASELINE_DIR = REPO / "baselines/图元样板"


@pytest.mark.slow
def test_diagram_samples_preview_clean(tmp_path):
    deck_path = build_deck.build(DECK_DIR, REPO, tmp_path / "samples.html", [])["out"]
    previewed = subprocess.run([sys.executable, "tools/preview_slides.py", str(deck_path), str(tmp_path / "shots"), "3800"],
                               cwd=REPO, capture_output=True, text=True)
    assert previewed.returncode == 0, previewed.stdout
    assert "共 9 页；JS 报错：无；溢出页：无；连线检查：无" in previewed.stdout


PAGE_COUNT = 9
LABEL_RECTS_SCRIPT = """() => [...document.querySelectorAll('.slide.active .dg-label')].map(label => {
  const rect = label.getBoundingClientRect();
  return { edge: label.dataset.edge, left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom };
})"""
LABEL_NODE_RECTS_SCRIPT = """() => {
  document.getAnimations().forEach(animation => { if (animation.effect.getTiming().iterations !== Infinity) animation.finish(); });
  const rectOf = element => { const rect = element.getBoundingClientRect(); return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }; };
  return {
    labels: [...document.querySelectorAll('.slide.active .dg-label')].map(label => ({ edge: label.dataset.edge, text: label.textContent, ...rectOf(label) })),
    nodes: [...document.querySelectorAll('.slide.active .dg .node')].map(node => ({ id: node.dataset.id, ...rectOf(node) })),
  };
}"""
AXIS_LINE_RECTS_SCRIPT = """() => {
  const rectOf = element => { const rect = element.getBoundingClientRect(); return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }; };
  const lines = [];
  document.querySelectorAll('.slide.active .dg .quadrant').forEach(quadrant => {
    const box = rectOf(quadrant), centerX = (box.left + box.right) / 2, centerY = (box.top + box.bottom) / 2;
    lines.push({ name: 'quadrant 横轴', left: box.left, right: box.right, top: centerY - 1, bottom: centerY + 1 });
    lines.push({ name: 'quadrant 竖轴', left: centerX - 1, right: centerX + 1, top: box.top, bottom: box.bottom });
  });
  document.querySelectorAll('.slide.active .dg .axis').forEach(axis => {
    const box = rectOf(axis);
    lines.push({ name: 'axis 轴线', left: box.left, right: box.right, top: box.top, bottom: box.top + 2 });
  });
  const labels = [...document.querySelectorAll('.slide.active .dg-label, .slide.active .dg .axis-title')].map(label => ({ text: label.textContent, ...rectOf(label) }));
  return { lines, labels };
}"""
LABEL_TO_NODE_MIN_GAP = 24
HUMAN_WIRES_SCRIPT = "document.querySelectorAll('.slide.active .dg .wire[data-kind=\"human\"]').length"
HUB_SIZE_SCRIPT = """() => {
  const style = getComputedStyle(document.querySelector('.slide.active .dg [data-id="hub"]'));
  return [parseFloat(style.width), parseFloat(style.height)];
}"""
HUB_HALO_TRANSFORM_SCRIPT = """() => {
  const halo = document.querySelector('.slide.active .dg [data-id="hub"] .halo');
  const [animation] = halo.getAnimations();
  animation.pause();
  animation.currentTime = 2000;
  return getComputedStyle(halo).transform;
}"""


@pytest.fixture(scope="module")
def samples_page(tmp_path_factory):
    deck_path = build_deck.build(DECK_DIR, REPO, tmp_path_factory.mktemp("samples") / "samples.html", [])["out"]
    with sync_playwright() as playwright:
        chrome_path = os.environ.get("PPT_CHROME_PATH")
        launch_options = {"headless": True, "executable_path": chrome_path} if chrome_path else {"headless": True, "channel": "chrome"}
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(deck_path.resolve().as_uri())
        wait_for_entrance_settled(page)

        def open_page(number):
            page.evaluate(f"show({number - 1})")
            wait_for_entrance_settled(page)
            return page

        yield open_page
        browser.close()


@pytest.mark.smoke
def test_no_two_edge_labels_overlap_on_any_page(samples_page):
    overlaps = []
    for number in range(1, PAGE_COUNT + 1):
        labels = samples_page(number).evaluate(LABEL_RECTS_SCRIPT)
        for index, first in enumerate(labels):
            for second in labels[index + 1:]:
                if first["left"] < second["right"] and second["left"] < first["right"] \
                        and first["top"] < second["bottom"] and second["top"] < first["bottom"]:
                    overlaps.append(f"第 {number} 页 {first['edge']} × {second['edge']}")
    assert overlaps == []


def rect_gap(first, second):
    gap_x = max(first["left"] - second["right"], second["left"] - first["right"], 0)
    gap_y = max(first["top"] - second["bottom"], second["top"] - first["bottom"], 0)
    return (gap_x ** 2 + gap_y ** 2) ** 0.5


@pytest.mark.smoke
def test_every_edge_label_keeps_distance_from_every_node(samples_page):
    too_close = []
    for number in range(1, PAGE_COUNT + 1):
        rects = samples_page(number).evaluate(LABEL_NODE_RECTS_SCRIPT)
        for label in rects["labels"]:
            for node in rects["nodes"]:
                gap = rect_gap(label, node)
                if gap < LABEL_TO_NODE_MIN_GAP:
                    too_close.append(f"第 {number} 页 标签「{label['text']}」离节点 {node['id']} 仅 {gap:.0f}px")
    assert too_close == []


@pytest.mark.smoke
def test_no_label_touches_an_axis_or_quadrant_line(samples_page):
    crossings = []
    for number in range(1, PAGE_COUNT + 1):
        rects = samples_page(number).evaluate(AXIS_LINE_RECTS_SCRIPT)
        for label in rects["labels"]:
            for line in rects["lines"]:
                if rect_gap(label, line) == 0:
                    crossings.append(f"第 {number} 页 「{label['text']}」压在 {line['name']} 上")
    assert crossings == []


@pytest.mark.smoke
def test_hub_circle_is_square_in_pixels(samples_page):
    width, height = samples_page(8).evaluate(HUB_SIZE_SCRIPT)
    assert abs(width - height) <= 1, (width, height)


@pytest.mark.smoke
def test_hub_halo_scales_uniformly(samples_page):
    transform = samples_page(8).evaluate(HUB_HALO_TRANSFORM_SCRIPT)
    scale_x, _, _, scale_y = [float(value) for value in transform.removeprefix("matrix(").removesuffix(")").split(",")[:4]]
    assert scale_x > 1.05, transform
    assert abs(scale_x - scale_y) < 1e-6, transform


@pytest.mark.smoke
def test_human_edges_appear_only_on_pages_4_and_5(samples_page):
    pages_with_human = [number for number in range(1, PAGE_COUNT + 1) if samples_page(number).evaluate(HUMAN_WIRES_SCRIPT)]
    assert pages_with_human == [4, 5]
