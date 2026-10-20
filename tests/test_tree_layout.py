"""树布局冒烟：构建 tests/fixtures/树布局，在浏览器里读节点位置、连线起点和连线检查结果。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import FIXTURES, open_deck, preview, REPO

pytestmark = pytest.mark.smoke

# 读 render.js 写的 left/top（不受登场动画的 transform 影响），取中心，四舍五入到像素
BOX_CENTERS = """() => Object.fromEntries([...document.querySelectorAll('.slide.active .dg .node')].map(node => [node.dataset.id,
  { x: Math.round(node.offsetLeft + node.offsetWidth / 2), y: Math.round(node.offsetTop + node.offsetHeight / 2), at: node.dataset.at }]))"""
WIRE_STARTS = """() => [...document.querySelectorAll('.slide.active .dg .wire')].map(wire =>
  [wire.dataset.edge, wire.getAttribute('d').split(' ').slice(1, 3).map(Number).map(Math.round).join(',')])"""


def build_tree_fixture(name, out_path):
    import subprocess
    import sys
    return subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(FIXTURES / name), "--engine-root", ".",
                           "--out", str(out_path)], cwd=REPO, capture_output=True, text=True)


def open_tree_page(playwright, tmp_path, page_hash):
    assert build_tree_fixture("树布局", tmp_path / "deck.html").returncode == 0
    return open_deck(playwright, tmp_path / "deck.html", page_hash)


def test_down_tree_centres_parent_and_children_share_one_trunk(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_tree_page(playwright, tmp_path, 1)
        centers = page.evaluate(BOX_CENTERS)
        starts = dict(page.evaluate(WIRE_STARTS))
        problems = page.evaluate("window.diagramProblems")
        browser.close()
    assert problems == [] and errors == []
    assert centers["ceo"]["y"] < centers["teach"]["y"] < centers["g7"]["y"]
    assert centers["teach"]["y"] == centers["moral"]["y"] == centers["logis"]["y"]
    assert centers["teach"]["x"] == (centers["g7"]["x"] + centers["g8"]["x"]) // 2
    # 同一父节点出去的线起点相同（总线），不是按 24px 错开
    assert starts["ceo→teach"] == starts["ceo→moral"] == starts["ceo→logis"]
    assert starts["teach→g7"] == starts["teach→g8"]
    assert sorted(starts) == ["ceo→logis", "ceo→moral", "ceo→teach", "teach→g7", "teach→g8"]


def test_right_tree_keeps_author_position_and_mind_map_spreads_both_sides(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_tree_page(playwright, tmp_path, 2)
        right = page.evaluate(BOX_CENTERS)
        page.evaluate("show(2)")
        mind = page.evaluate(BOX_CENTERS)
        problems = page.evaluate("window.diagramProblems")
        browser.close()
    assert problems == [] and errors == []
    assert right["wall"]["at"] == "18 0.5 5 1.2"
    assert right["cell"]["x"] < right["struct"]["x"] < right["membrane"]["x"]
    # 3 个孩子：前 2 个右边、第 3 个左边；右边的孩子再往右展开
    assert mind["scene"]["x"] > mind["topic"]["x"] and mind["feel"]["x"] > mind["topic"]["x"]
    assert mind["words"]["x"] < mind["topic"]["x"]
    assert mind["grass"]["x"] > mind["scene"]["x"]


def test_broken_tree_is_reported_with_page_and_id(tmp_path):
    assert build_tree_fixture("树布局-坏", tmp_path / "bad.html").returncode == 0
    previewed = preview(tmp_path / "bad.html", tmp_path / "shots")
    assert previewed.returncode == 1
    assert "连线检查：第 1 页 lost：data-at 要写 4 个数：树布局：父节点 nope 不存在" in previewed.stdout
    assert "连线检查：第 2 页 top：data-at 要写 4 个数：树布局：未知 data-tree 值 rihgt（只能写 down、right、mind）" in previewed.stdout
    assert "连线检查：第 2 页 kid：data-at 要写 4 个数：树布局：未知 data-tree 值 rihgt（只能写 down、right、mind）" in previewed.stdout
