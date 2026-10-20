import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.mark.smoke
def test_new_deck_builds_and_previews_clean(tmp_path):
    target = tmp_path / "新课"
    made = subprocess.run([sys.executable, "tools/new_deck.py", str(target), "--title", "测试课"], cwd=REPO,
                          capture_output=True, text=True)
    assert made.returncode == 0, made.stderr
    built = subprocess.run([sys.executable, "tools/build_deck.py", "--deck", ".", "--engine-root", ".",
                            "--out", "out.html"], cwd=target, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    preview = subprocess.run([sys.executable, "tools/preview_slides.py", "out.html", "shots", "1500"], cwd=target,
                             capture_output=True, text=True)
    assert preview.returncode == 0, preview.stdout
    assert "JS 报错：无；溢出页：无" in preview.stdout


def test_refuses_non_empty_target(tmp_path):
    (tmp_path / "x.txt").write_text("keep")
    made = subprocess.run([sys.executable, "tools/new_deck.py", str(tmp_path), "--title", "t"], cwd=REPO,
                          capture_output=True, text=True)
    assert made.returncode == 1
    assert "非空" in made.stderr
    assert sorted(path.name for path in tmp_path.iterdir()) == ["x.txt"]
    assert (tmp_path / "x.txt").read_text() == "keep"
