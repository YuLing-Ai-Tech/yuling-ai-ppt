"""风格清单里的脚本拼成一个 <script>，共用一个全局作用域：顶层名字不许跨文件重名，也不许和 window.X 赋值撞名。
重名的 function 会静默覆盖前一个，const 重名整份脚本报错，window.X = … 会盖掉同名的顶层函数。"""
import json
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOP_LEVEL_DECLARATION = re.compile(r"^(?:(?:async\s+)?function\s*\*?|class|const|let|var)\s*([A-Za-z_$][\w$]*)([^\n]*)", re.M)
EXTRA_DECLARATOR = re.compile(r",\s*([A-Za-z_$][\w$]*)\s*=(?!=)")
WINDOW_ASSIGNMENT = re.compile(r"\bwindow\.([A-Za-z_$][\w$]*)\s*=(?!=)")


def top_level_names(source_text):
    """顶层声明的名字，含 async function、function*，以及 const a = 1, b = 2 里的 b（只认同一行、逗号后紧跟 名字 =）。"""
    names = set()
    for match in TOP_LEVEL_DECLARATION.finditer(source_text):
        names.add(match.group(1))
        if match.group(0).startswith(("const", "let", "var")):
            names |= set(EXTRA_DECLARATOR.findall(match.group(2)))
    return names


def global_name_clashes(script_paths):
    """返回 (跨文件重名的顶层名字, 同时被 window.X 赋值的顶层名字)，都排好序。"""
    top_level, assigned = Counter(), set()
    for path in script_paths:
        source_text = path.read_text(encoding="utf-8")
        top_level.update(top_level_names(source_text))
        assigned |= set(WINDOW_ASSIGNMENT.findall(source_text))
    return sorted(name for name, count in top_level.items() if count > 1), sorted(assigned & set(top_level))


def test_style_scripts_share_global_scope_without_clashes():
    manifests = sorted((REPO / "styles").glob("*/manifest.json"))
    assert manifests
    for manifest_path in manifests:
        script_paths = [REPO / path for path in json.loads(manifest_path.read_text())["js"]]
        assert global_name_clashes(script_paths) == ([], []), manifest_path


def test_clash_check_catches_window_assignment_over_function(tmp_path):
    (tmp_path / "a.js").write_text("function diagramProblems() {}\n")
    (tmp_path / "b.js").write_text("window.diagramProblems = [];\nconst stage = 1;\n")
    (tmp_path / "c.js").write_text("const stage = 2;\n")
    assert global_name_clashes([tmp_path / "a.js", tmp_path / "b.js", tmp_path / "c.js"]) == (["stage"], ["diagramProblems"])


def test_clash_check_covers_async_generator_and_multi_declarator(tmp_path):
    (tmp_path / "a.js").write_text("async function loadIt() {}\nfunction* walk() {}\nconst first = 1, second = 2;\n")
    (tmp_path / "b.js").write_text("const loadIt = 1;\nlet walk = 2;\nvar second = 3;\n")
    assert global_name_clashes([tmp_path / "a.js", tmp_path / "b.js"]) == (["loadIt", "second", "walk"], [])
