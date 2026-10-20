import os
import subprocess
from pathlib import Path

import pytest

from tools.check_line_limits import over_limit


# 提交钩子（尤其在 git 工作树里）会带着 GIT_DIR、GIT_INDEX_FILE 等变量跑测试；
# 不清掉的话，临时仓库里的 git init / ls-files 会作用到真仓库上（2026-09-30 曾把主仓库改成 core.bare=true）
@pytest.fixture(autouse=True)
def isolate_from_outer_git(monkeypatch):
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)


def make_repo(tmp_path, files):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for relative_path, line_count in files.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n" * line_count, encoding="utf-8")
    return tmp_path


def test_reports_program_files_over_limit(tmp_path):
    repo = make_repo(tmp_path, {"a.js": 801, "b.css": 800, "notes.md": 5000})
    assert over_limit(repo) == [("a.js", 801)]


def test_ignores_example_images_and_non_program_files(tmp_path):
    repo = make_repo(tmp_path, {"examples/甬舟94/images/x.html": 900, "data.json": 900})
    assert over_limit(repo) == []


def test_detects_chinese_named_program_files_over_limit(tmp_path):
    repo = make_repo(tmp_path, {"styles/苹果风/长文件.js": 801})
    assert over_limit(repo) == [("styles/苹果风/长文件.js", 801)]
