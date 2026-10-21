"""位置文件写回源文件（tools/apply_positions.py）与构建记来源文件（build_deck.py 的 data-source）。纯文件操作，不起浏览器。"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import apply_positions, build_deck

REPO = Path(__file__).resolve().parent.parent
TWO_DIAGRAMS = """<section class="slide" data-section="x">
  <div class="dg" data-grid="24 12">
    <div class="node" data-id="a" data-at="1 1 4 2"><b>A</b></div>
  </div>
  <div class="dg" data-grid="24 12" data-tree="down">
    <div class="node" data-id="a" data-at='2 2 4 2'><b>A2</b></div>
    <div class="node" data-id="b" data-parent="a"><b>B</b></div>
  </div>
</section>
"""


def make_deck(tmp_path, slides):
    (tmp_path / "slides").mkdir(parents=True)
    (tmp_path / "deck.json").write_text('{"title": "t", "output": "t.html", "style": "苹果风"}', encoding="utf-8")
    for name, body in slides.items():
        (tmp_path / "slides" / name).write_text(body, encoding="utf-8", newline="")
    return tmp_path


def positions_file(tmp_path, moves, file_format="yuling-positions-1", deck_title="t"):
    path = tmp_path / "位置.json"
    path.write_text(json.dumps({"format": file_format, "deck": deck_title, "moves": moves}, ensure_ascii=False), encoding="utf-8")
    return path


def test_rewrites_data_at_in_the_right_diagram_and_adds_it_when_missing(tmp_path):
    deck = make_deck(tmp_path / "deck", {"01_a.html": TWO_DIAGRAMS})
    moves = [{"page": 1, "source": "01_a.html", "diagram": 1, "id": "a", "at": "3.5 2 4 2", "was": "2 2 4 2"},
             {"page": 1, "source": "01_a.html", "diagram": 1, "id": "b", "at": "9 6.1 4 1.4", "was": ""}]
    assert apply_positions.apply_positions(deck, positions_file(tmp_path, moves)) == (2, [])
    expected = TWO_DIAGRAMS.replace("data-at='2 2 4 2'", 'data-at="3.5 2 4 2"').replace(
        '<div class="node" data-id="b" data-parent="a">', '<div class="node" data-id="b" data-parent="a" data-at="9 6.1 4 1.4">')
    assert (deck / "slides/01_a.html").read_text(encoding="utf-8") == expected


def test_any_missing_target_is_listed_and_nothing_is_written(tmp_path):
    deck = make_deck(tmp_path / "deck", {"01_a.html": TWO_DIAGRAMS})
    moves = [{"page": 1, "source": "01_a.html", "diagram": 0, "id": "a", "at": "5 5 4 2", "was": "1 1 4 2"},
             {"page": 1, "source": "01_a.html", "diagram": 2, "id": "a", "at": "1 1 1 1", "was": ""},
             {"page": 1, "source": "01_a.html", "diagram": 0, "id": "zz", "at": "1 1 1 1", "was": ""},
             {"page": 2, "source": "09_none.html", "diagram": 0, "id": "a", "at": "1 1 1 1", "was": ""},
             {"page": 3, "source": "", "diagram": 0, "id": "a", "at": "1 1 1 1", "was": ""},
             {"page": 4, "source": "../deck.json", "diagram": 0, "id": "a", "at": "1 1 1 1", "was": ""}]
    changed, problems = apply_positions.apply_positions(deck, positions_file(tmp_path, moves))
    assert changed == 0 and problems == [
        "第 1 页 a：01_a.html 里没有第 3 个图（序号 2，共 2 个）",
        "第 1 页 zz：01_a.html 第 1 个图（序号 0）里没有 data-id=zz",
        "第 2 页 a：来源文件 09_none.html 不存在",
        "第 3 页 a：来源文件 （空，课件要用新版 build_deck 重新构建） 不存在",
        "第 4 页 a：来源文件 ../deck.json 不在 slides/ 里，拒绝写入"]
    assert (deck / "deck.json").read_text(encoding="utf-8").startswith('{"title"')
    assert (deck / "slides/01_a.html").read_text(encoding="utf-8") == TWO_DIAGRAMS


def test_wrong_format_is_refused_and_cli_exits_1(tmp_path):
    deck = make_deck(tmp_path / "deck", {"01_a.html": TWO_DIAGRAMS})
    path = positions_file(tmp_path, [], file_format="other")
    result = subprocess.run([sys.executable, "tools/apply_positions.py", "--deck", str(deck), str(path)], cwd=REPO,
                            capture_output=True, text=True)
    assert result.returncode == 1 and "位置文件格式不是 yuling-positions-1：other" in result.stderr


def test_build_marks_every_slide_with_its_source_file(tmp_path):
    two_pages = '<section class="slide chapter"><h2>甲</h2></section>\n<section class="slide" data-section="乙">' \
                '<div class="dg"><section class="zone" data-id="z" data-at="1 1 4 4"></section></div></section>'
    deck = make_deck(tmp_path / "deck", {"01_两页.html": two_pages, "02_一页.html": '<section class="slide"><h2>丙</h2></section>'})
    page = build_deck.build(deck, REPO, tmp_path / "out.html", [])["out"].read_text(encoding="utf-8")
    assert page.count('<section class="slide chapter" data-source="01_两页.html">') == 1
    assert page.count('<section class="slide" data-section="乙" data-source="01_两页.html">') == 1
    assert page.count('<section class="slide" data-source="02_一页.html">') == 1
    assert '<section class="zone" data-id="z" data-at="1 1 4 4">' in page  # 图元容器 <section class="zone"> 不加


def test_source_file_changed_after_reading_is_refused_not_overwritten(tmp_path, monkeypatch):
    deck = make_deck(tmp_path / "deck", {"01_a.html": TWO_DIAGRAMS})
    moves = [{"page": 1, "source": "01_a.html", "diagram": 0, "id": "a", "at": "5 5 4 2", "was": "1 1 4 2"}]
    real_planned_edits = apply_positions.planned_edits

    def planned_then_file_changes(slides_dir, planned_moves):
        planned = real_planned_edits(slides_dir, planned_moves)
        (slides_dir / "01_a.html").write_text("<!-- 别人刚改过 -->\n" + TWO_DIAGRAMS, encoding="utf-8")
        return planned

    monkeypatch.setattr(apply_positions, "planned_edits", planned_then_file_changes)
    with pytest.raises(RuntimeError, match="01_a.html 在读取后被改过"):
        apply_positions.apply_positions(deck, positions_file(tmp_path, moves))
    assert (deck / "slides/01_a.html").read_text(encoding="utf-8").startswith("<!-- 别人刚改过 -->")


def move_a(at="5 5 4 2", was="1 1 4 2", source="01_a.html", diagram=0, node="a"):
    return {"page": 1, "source": source, "diagram": diagram, "id": node, "at": at, "was": was}


def test_crlf_source_keeps_every_other_byte(tmp_path):
    deck = make_deck(tmp_path / "deck", {"01_a.html": "x"})
    crlf_bytes = TWO_DIAGRAMS.replace("\n", "\r\n").encode("utf-8")
    (deck / "slides/01_a.html").write_bytes(crlf_bytes)
    assert apply_positions.apply_positions(deck, positions_file(tmp_path, [move_a()])) == (1, [])
    assert (deck / "slides/01_a.html").read_bytes() == crlf_bytes.replace(b'data-at="1 1 4 2"', b'data-at="5 5 4 2"')


def test_source_edited_after_saving_is_refused_with_both_values(tmp_path):
    deck = make_deck(tmp_path / "deck", {"01_a.html": TWO_DIAGRAMS})
    saved = positions_file(tmp_path, [move_a(at="3.5 2 4 2", was="2 2 4 2", diagram=1)])  # 保存时 a 在第 2 个图里
    inserted = '<div class="dg"><div class="node" data-id="a" data-at="7 7 1 1"></div></div>\n' + TWO_DIAGRAMS
    (deck / "slides/01_a.html").write_text(inserted, encoding="utf-8")  # 保存后有人在顶部插了一个图：序号 1 现在是原来的第 1 个图
    changed, problems = apply_positions.apply_positions(deck, saved)
    assert changed == 0 and len(problems) == 1
    assert "第 1 条" in problems[0] and "01_a.html" in problems[0] and "a" in problems[0]
    assert "保存时是 '2 2 4 2'" in problems[0] and "现在是 '1 1 4 2'" in problems[0]
    assert (deck / "slides/01_a.html").read_text(encoding="utf-8") == inserted


def test_was_empty_means_source_had_no_data_at_and_deck_title_must_match(tmp_path):
    deck = make_deck(tmp_path / "deck", {"01_a.html": TWO_DIAGRAMS})
    wrong_was = positions_file(tmp_path, [move_a(was="")])  # 保存时源里没写 data-at，现在写了
    assert apply_positions.apply_positions(deck, wrong_was)[1][0].count("现在是 '1 1 4 2'") == 1
    other_deck = positions_file(tmp_path, [move_a()], deck_title="别的课件")
    assert apply_positions.apply_positions(deck, other_deck) == (0, ["位置文件来自课件 别的课件，这个课件是 t"])
    assert (deck / "slides/01_a.html").read_text(encoding="utf-8") == TWO_DIAGRAMS


def test_duplicate_target_and_second_file_failure_write_nothing(tmp_path, monkeypatch):
    deck = make_deck(tmp_path / "deck", {"01_a.html": TWO_DIAGRAMS, "02_b.html": TWO_DIAGRAMS})
    twice = positions_file(tmp_path, [move_a(), move_a(at="6 6 4 2")])
    changed, problems = apply_positions.apply_positions(deck, twice)
    assert changed == 0 and len(problems) == 1 and "重复" in problems[0] and "第 2 条" in problems[0]
    moves = [move_a(), move_a(source="02_b.html")]
    real_planned_edits = apply_positions.planned_edits

    def planned_then_second_file_changes(slides_dir, planned_moves):
        planned = real_planned_edits(slides_dir, planned_moves)
        (slides_dir / "02_b.html").write_text("<!-- 改过 -->\n" + TWO_DIAGRAMS, encoding="utf-8")
        return planned

    monkeypatch.setattr(apply_positions, "planned_edits", planned_then_second_file_changes)
    with pytest.raises(RuntimeError, match="02_b.html 在读取后被改过"):
        apply_positions.apply_positions(deck, positions_file(tmp_path, moves))
    assert (deck / "slides/01_a.html").read_text(encoding="utf-8") == TWO_DIAGRAMS  # 第 1 个文件也没写


@pytest.mark.parametrize("bad_move, expected", [
    ({"page": 1, "source": "01_a.html", "diagram": 0, "id": "a", "was": "1 1 4 2"}, "at 要写 4 个数"),
    ({"page": 1, "source": "01_a.html", "diagram": 0, "id": "a", "at": 7, "was": "1 1 4 2"}, "at 要写 4 个数"),
    ({"page": 1, "source": "01_a.html", "diagram": 0, "id": "a", "at": "hello 1 2 3", "was": "1 1 4 2"}, "at 要写 4 个数"),
    ({"page": 1, "source": "01_a.html", "diagram": 0, "id": "a", "at": "5 5 4 2"}, "缺少 was"),
    ({"page": 1, "source": "01_a.html", "diagram": 0, "at": "5 5 4 2", "was": ""}, "缺少 id"),
    ({"page": 1, "source": "a\0b.html", "diagram": 0, "id": "a", "at": "5 5 4 2", "was": ""}, "来源文件"),
    ("不是对象", "不是对象"),
])
def test_bad_move_fields_give_a_clear_problem_not_a_traceback(tmp_path, bad_move, expected):
    deck = make_deck(tmp_path / "deck", {"01_a.html": TWO_DIAGRAMS})
    changed, problems = apply_positions.apply_positions(deck, positions_file(tmp_path, [bad_move]))
    assert changed == 0 and len(problems) == 1 and expected in problems[0]


def test_non_utf8_source_is_reported(tmp_path):
    deck = make_deck(tmp_path / "deck", {"01_a.html": "x"})
    (deck / "slides/01_a.html").write_bytes("<div class=\"dg\">甲</div>".encode("gbk"))
    changed, problems = apply_positions.apply_positions(deck, positions_file(tmp_path, [move_a()]))
    assert changed == 0 and len(problems) == 1 and "不是 UTF-8" in problems[0]


def test_line_breaks_other_than_newline_do_not_shift_offsets(tmp_path):
    source = '<section class="slide">\x0c\u2028\x85<div class="dg">\n  <div class="node" data-id="a" data-at="1 1 4 2"></div></div></section>\n'
    deck = make_deck(tmp_path / "deck", {"01_a.html": source})
    assert apply_positions.apply_positions(deck, positions_file(tmp_path, [move_a()])) == (1, [])
    assert (deck / "slides/01_a.html").read_bytes().decode("utf-8") == source.replace('"1 1 4 2"', '"5 5 4 2"')


def test_only_the_real_data_at_attribute_is_replaced(tmp_path):
    source = '<div class="dg"><div class="node" title=" data-at=9" data-id="a" data-at="1 1 4 2"></div></div>\n'
    deck = make_deck(tmp_path / "deck", {"01_a.html": source})
    assert apply_positions.apply_positions(deck, positions_file(tmp_path, [move_a()])) == (1, [])
    assert (deck / "slides/01_a.html").read_text(encoding="utf-8") == source.replace('data-at="1 1 4 2"', 'data-at="5 5 4 2"')
