import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def make_deck(tmp_path):
    deck = tmp_path / "deck"
    (deck / "slides").mkdir(parents=True)
    (deck / "styles").mkdir()
    (deck / "deck.json").write_text(
        '{"title":"Portable fixture","style":"苹果风"}', encoding="utf-8"
    )
    (deck / "slides" / "01_cover.html").write_text(
        '<!-- private author note --><section class="slide"><h1>Cover</h1></section>', encoding="utf-8"
    )
    (deck / "slides" / "02_content.html").write_text(
        '<section class="slide"><h2>Content</h2></section>', encoding="utf-8"
    )
    (deck / "slides" / "03_close.html").write_text(
        '<section class="slide"><h2>Close</h2></section>', encoding="utf-8"
    )
    (deck / "styles" / "zz_fixture.css").write_text(
        '/* portable fixture */\n.fixture-marker { color: var(--text); }\n', encoding="utf-8"
    )
    return deck


def run_build(tmp_path, *extra):
    deck = make_deck(tmp_path)
    out_path = tmp_path / "deck.html"
    result = subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(deck), "--engine-root", ".",
                             "--out", str(out_path), *extra], cwd=REPO, capture_output=True, text=True)
    return result, out_path


def test_builds_all_portable_fixture_pages(tmp_path):
    result, out_path = run_build(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "3 页" in result.stdout
    assert out_path.read_text().count('<section class="slide') == 3


def test_only_filter_builds_subset(tmp_path):
    result, out_path = run_build(tmp_path, "--only", "02")
    assert result.returncode == 0, result.stderr
    assert out_path.read_text().count('<section class="slide') == 1


def test_strips_html_comments_from_output(tmp_path):
    result, out_path = run_build(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "<!-- private author note -->" not in out_path.read_text()


def test_manifest_order_decides_css_order(tmp_path):
    result, out_path = run_build(tmp_path)
    assert result.returncode == 0, result.stderr
    page = out_path.read_text()
    assert page.index(".glass {") < page.index("/* portable fixture */")


def test_backdrop_comes_from_style_file(tmp_path):
    result, out_path = run_build(tmp_path)
    assert result.returncode == 0, result.stderr
    assert '<div id="backdrop"><i></i><i></i><i></i><i></i></div>' in out_path.read_text()
