"""The real builder handles UTF-8 input without relying on Python UTF-8 mode."""
import os
import subprocess
import sys

from tests.test_build import REPO, make_deck


def test_builder_uses_utf8_without_python_utf8_mode(tmp_path):
    deck = make_deck(tmp_path / "中文 目录")
    text = '<section class="slide"><h1>中文与 emoji 🧪</h1></section>'
    (deck / "slides" / "01_cover.html").write_text(text, encoding="utf-8")
    out_path = tmp_path / "单文件 输出.html"
    result = subprocess.run(
        [sys.executable, "-X", "utf8=0", "tools/build_deck.py", "--deck", str(deck),
         "--engine-root", str(REPO), "--out", str(out_path)], cwd=REPO,
        env={**os.environ, "PYTHONUTF8": "0"}, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "中文与 emoji 🧪" in out_path.read_text(encoding="utf-8")
