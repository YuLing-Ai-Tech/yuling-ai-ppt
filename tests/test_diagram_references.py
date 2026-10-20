"""图元引用与几何检查：构建期引用错、预览期几何错，报页码和 id。"""
import pytest

from tests.diagram_helpers import build_fixture, build_slides, node, preview, slide_with


@pytest.mark.smoke
def test_nested_diagram_previews_clean(tmp_path):
    built = build_fixture("图元冒烟", tmp_path / "deck.html")
    assert built.returncode == 0, built.stderr
    previewed = preview(tmp_path / "deck.html", tmp_path / "shots")
    assert previewed.returncode == 0, previewed.stdout
    assert "JS 报错：无；溢出页：无；连线检查：无" in previewed.stdout


def test_build_reports_broken_references_with_page_and_id(tmp_path):
    built = build_fixture("连线检查-引用错", tmp_path / "deck.html")
    assert built.returncode == 1
    assert built.stderr.splitlines()[1:] == ["第 1 页 api：data-id 重复", "第 1 页 vcp：data-in 指向的容器不存在",
                                             "第 1 页 dbx：连线端点不存在"]
    assert not (tmp_path / "deck.html").exists()


@pytest.mark.smoke
def test_preview_reports_geometry_problems_with_page_and_id(tmp_path):
    built = build_fixture("连线检查-几何错", tmp_path / "deck.html")
    assert built.returncode == 0, built.stderr
    previewed = preview(tmp_path / "deck.html", tmp_path / "shots")
    assert previewed.returncode == 1
    assert [line for line in previewed.stdout.splitlines() if line.startswith("连线检查：第")] == [
        "连线检查：第 1 页 cache：超出父容器 vpc",
        "连线检查：第 1 页 api × db：同一容器里重叠",
        "连线检查：第 1 页 web→mid 的标签：标签压在节点 mid 上",
    ]


def test_same_id_in_two_diagrams_on_one_page_is_allowed(tmp_path):
    built = build_slides(tmp_path, {"01.html": slide_with(node("a"), node("a"))})
    assert built.returncode == 0, built.stderr


def test_edge_to_id_that_exists_only_in_another_diagram_is_reported(tmp_path):
    first = node("a") + '<i class="edge" data-from="a" data-to="b"></i>'
    built = build_slides(tmp_path, {"01.html": slide_with(first, node("b"))})
    assert built.returncode == 1
    assert built.stderr.splitlines()[1:] == ["第 1 页 b：连线端点不存在"]


def test_data_in_parent_from_another_diagram_is_reported(tmp_path):
    built = build_slides(tmp_path, {"01.html": slide_with(node("zone"), node("child", "zone"))})
    assert built.returncode == 1
    assert built.stderr.splitlines()[1:] == ["第 1 页 zone：data-in 指向的容器不存在"]


def test_duplicate_id_inside_one_diagram_is_still_reported(tmp_path):
    built = build_slides(tmp_path, {"01.html": slide_with(node("a") + node("a"))})
    assert built.returncode == 1
    assert built.stderr.splitlines()[1:] == ["第 1 页 a：data-id 重复"]


def test_multi_class_diagram_and_single_quotes_are_checked(tmp_path):
    body = "<div class='node' data-id='a' data-at='1 1 4 2'></div><i class='edge' data-from='a' data-to='nope'></i>"
    built = build_slides(tmp_path, {"01.html": slide_with(body, dg_open="<div class='dg wide' data-grid='24 12'>")})
    assert built.returncode == 1
    assert built.stderr.splitlines()[1:] == ["第 1 页 nope：连线端点不存在"]


def test_same_missing_endpoint_is_reported_once(tmp_path):
    edges = '<i class="edge" data-from="x" data-to="a"></i><i class="edge" data-from="x" data-to="a"></i>'
    built = build_slides(tmp_path, {"01.html": slide_with(node("x") + edges)})
    assert built.returncode == 1
    assert built.stderr.splitlines()[1:] == ["第 1 页 a：连线端点不存在"]


def test_reference_error_in_second_slide_file_uses_global_page_number(tmp_path):
    good = slide_with(node("a")) + slide_with(node("b"))
    bad = slide_with(node("c") + '<i class="edge" data-from="c" data-to="ghost"></i>')
    built = build_slides(tmp_path, {"01_a.html": good, "02_b.html": bad})
    assert built.returncode == 1
    assert built.stderr.splitlines()[1:] == ["第 3 页 ghost：连线端点不存在"]


@pytest.mark.smoke
def test_preview_reports_unknown_edge_kind_with_page_and_id(tmp_path):
    built = build_fixture("连线检查-类型错", tmp_path / "deck.html")
    assert built.returncode == 0, built.stderr
    previewed = preview(tmp_path / "deck.html", tmp_path / "shots")
    assert previewed.returncode == 1
    assert [line for line in previewed.stdout.splitlines() if line.startswith("连线检查：第")] == [
        "连线检查：第 1 页 web→api：连线类型 Sync 未知（可用 sync、async、data、human、tele）",
    ]
