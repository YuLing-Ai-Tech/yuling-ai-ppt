"""图元写法检查：拼错的 data-start / data-end / data-tone、路径写错、同方向重复连线，预览报页码和 id；路径缺 data-nodes 时 R 键不抛错。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_slides, open_deck, preview, slide_with

pytestmark = pytest.mark.smoke

TWO_NODES = '<div class="node" data-id="a" data-at="1 1 4 2"{tone}></div><div class="node" data-id="b" data-at="10 1 4 2"></div>'


def problem_lines(tmp_path, diagram_body):
    built = build_slides(tmp_path, {"01.html": slide_with(diagram_body)})
    assert built.returncode == 0, built.stderr
    previewed = preview(tmp_path / "out.html", tmp_path / "shots")
    return previewed.returncode, [line for line in previewed.stdout.splitlines() if line.startswith("连线检查：第")]


def test_unknown_tone_end_and_start_are_reported_with_page_and_id(tmp_path):
    body = TWO_NODES.format(tone=' data-tone="9"') + '<i class="edge" data-from="a" data-to="b" data-start="arow" data-end="dto"></i>'
    exit_code, lines = problem_lines(tmp_path, body)
    assert exit_code == 1
    assert lines == [
        "连线检查：第 1 页 a：色调 9 未知（可用 1～8）",
        "连线检查：第 1 页 a→b：data-start arow 未知（可用 arrow、dot、diamond、none）",
        "连线检查：第 1 页 a→b：data-end dto 未知（可用 arrow、dot、diamond、none）",
    ]


def test_known_tones_and_end_shapes_are_not_reported(tmp_path):
    body = TWO_NODES.format(tone=' data-tone="8"') + '<i class="edge" data-from="a" data-to="b" data-start="diamond" data-end="none"></i>'
    exit_code, lines = problem_lines(tmp_path, body)
    assert (exit_code, lines) == (0, [])


def test_route_with_unknown_node_or_without_nodes_is_reported(tmp_path):
    body = TWO_NODES.format(tone="") + '<i class="route" data-nodes="a ghost"></i><i class="route"></i>'
    exit_code, lines = problem_lines(tmp_path, body)
    assert exit_code == 1
    assert lines == ["连线检查：第 1 页 路径 1：节点 ghost 不存在", "连线检查：第 1 页 路径 2：缺 data-nodes"]


def test_route_key_skips_route_without_nodes_and_throws_nothing(tmp_path):
    body = TWO_NODES.format(tone="") + '<i class="route"></i><i class="route" data-nodes="a b"></i>'
    assert build_slides(tmp_path, {"01.html": slide_with(body)}).returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "out.html", 1)
        page.keyboard.press("r")
        kept_ids = page.evaluate("[...document.querySelectorAll('.slide.active .dg .is-kept[data-id]')].map(e => e.dataset.id).sort()")
        browser.close()
    assert errors == [] and kept_ids == ["a", "b"]



def test_two_edges_between_same_pair_in_same_direction_are_reported(tmp_path):
    body = TWO_NODES.format(tone="") + '<i class="edge" data-from="a" data-to="b"></i><i class="edge" data-from="a" data-to="b:b"></i>'
    exit_code, lines = problem_lines(tmp_path, body)
    assert exit_code == 1
    assert lines == ["连线检查：第 1 页 a→b：同方向的连线有 2 条，检查和聚焦按「起点→终点」认线，请合并成一条"]


def test_opposite_directions_between_same_pair_are_allowed(tmp_path):
    body = TWO_NODES.format(tone="") + '<i class="edge" data-from="a" data-to="b"></i><i class="edge" data-from="b" data-to="a"></i>'
    exit_code, lines = problem_lines(tmp_path, body)
    assert (exit_code, lines) == (0, [])
