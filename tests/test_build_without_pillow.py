"""没装 Pillow 的系统 python3 也能构建不含图片的课件：PIL 只在真正压缩图片时才导入。"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUILD_WITHOUT_PIL = ("import sys, runpy; sys.modules['PIL'] = None; "
                     "sys.argv = ['build_deck.py', '--deck', sys.argv[1], '--engine-root', '.', '--out', sys.argv[2]]; "
                     "runpy.run_path('tools/build_deck.py', run_name='__main__')")


def test_deck_without_images_builds_when_pillow_is_missing(tmp_path):
    deck = tmp_path / "deck"
    (deck / "slides").mkdir(parents=True)
    (deck / "deck.json").write_text('{"title": "t", "output": "t.html", "style": "苹果风"}', encoding="utf-8")
    (deck / "slides" / "01_a.html").write_text('<section class="slide"><h2>没有图片</h2></section>', encoding="utf-8")
    result = subprocess.run([sys.executable, "-c", BUILD_WITHOUT_PIL, str(deck), str(tmp_path / "out.html")],
                            cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "没有图片" in (tmp_path / "out.html").read_text(encoding="utf-8")


def test_trusted_svg_logo_is_inlined_without_pillow(tmp_path):
    deck = tmp_path / "deck"
    (deck / "slides").mkdir(parents=True)
    (deck / "logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>', encoding="utf-8")
    (deck / "deck.json").write_text('{"title":"t","brand":"毓灵 YuLing AI","logo":"logo.svg","style":"苹果风"}', encoding="utf-8")
    (deck / "slides" / "01_a.html").write_text('<section class="slide"><h2>品牌页</h2></section>', encoding="utf-8")
    result = subprocess.run([sys.executable, "-c", BUILD_WITHOUT_PIL, str(deck), str(tmp_path / "out.html")],
                            cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    built = (tmp_path / "out.html").read_text(encoding="utf-8")
    assert 'data:image/svg+xml;base64,' in built
    assert '<span>毓灵 YuLing AI</span>' in built


def test_trusted_png_logo_is_inlined_without_pillow(tmp_path):
    deck = tmp_path / "deck"
    (deck / "slides").mkdir(parents=True)
    (deck / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\ntrusted-logo")
    (deck / "deck.json").write_text('{"title":"t","logo":"logo.png","style":"苹果风"}', encoding="utf-8")
    (deck / "slides" / "01_a.html").write_text('<section class="slide"><h2>PNG 品牌页</h2></section>', encoding="utf-8")
    result = subprocess.run([sys.executable, "-c", BUILD_WITHOUT_PIL, str(deck), str(tmp_path / "out.html")],
                            cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'data:image/png;base64,' in (tmp_path / "out.html").read_text(encoding="utf-8")
