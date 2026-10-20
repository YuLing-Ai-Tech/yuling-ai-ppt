"""循环图冒烟：节点排在环上（正上、正右、正下、正左），中心节点在正中，相邻节点首尾相连、连线检查 0 问题。"""
import subprocess
import sys

import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import FIXTURES, REPO, open_deck, preview

pytestmark = pytest.mark.smoke

NODE_CENTERS = """() => Object.fromEntries([...document.querySelectorAll('.slide.active .dg .node')].map(node => [node.dataset.id,
  [Math.round(node.offsetLeft + node.offsetWidth / 2), Math.round(node.offsetTop + node.offsetHeight / 2)]]))"""


def test_cycle_nodes_go_round_clockwise_and_link_head_to_tail(tmp_path):
    built = subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(FIXTURES / "循环图"), "--engine-root", ".",
                            "--out", str(tmp_path / "cycle.html")], cwd=REPO, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "cycle.html", 1)
        centers = page.evaluate(NODE_CENTERS)
        edges = page.evaluate("[...new Set([...document.querySelectorAll('.slide.active .dg .wire')].map(w => w.dataset.edge))]")
        problems = page.evaluate("window.diagramProblems")
        browser.close()
    assert problems == [] and errors == []
    (evap_x, evap_y), (cond_x, cond_y), (rain_x, rain_y), (flow_x, flow_y) = (centers[k] for k in ("evap", "cond", "rain", "flow"))
    sun_x, sun_y = centers["sun"]
    assert evap_x == rain_x == sun_x and cond_y == flow_y == sun_y
    assert evap_y < sun_y < rain_y and flow_x < sun_x < cond_x
    assert edges == ["evap→cond", "cond→rain", "rain→flow", "flow→evap"]


def test_cycle_with_missing_id_or_too_many_nodes_is_reported_with_page_and_id(tmp_path):
    built = subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(FIXTURES / "循环图-坏"), "--engine-root", ".",
                            "--out", str(tmp_path / "bad.html")], cwd=REPO, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    previewed = preview(tmp_path / "bad.html", tmp_path / "shots")
    assert previewed.returncode == 1
    assert "连线检查：第 1 页 #2：data-at 要写 4 个数：循环图：节点缺 data-id" in previewed.stdout
    assert "连线检查：第 2 页 n1：data-at 要写 4 个数：循环图：环上有 13 个节点，最多 12 个" in previewed.stdout
    assert "连线检查：第 1 页 one：data-at 要写 4 个数：循环图：同图有节点缺 data-id，整图未排" in previewed.stdout
    assert "连线检查：第 2 页 mid：data-at 要写 4 个数：循环图：环上有 13 个节点，最多 12 个，整图未排" in previewed.stdout
    assert "（空）" not in previewed.stdout
    assert "undefined" not in previewed.stdout
