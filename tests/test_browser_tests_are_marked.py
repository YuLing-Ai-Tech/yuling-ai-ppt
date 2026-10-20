"""守卫：凡是会启动浏览器的测试，必须带 smoke 或 slow 标记，否则会溜进提交钩子（tools/ci.sh --fast）。纯静态，不起浏览器。

局限：只看测试函数体里直接出现的名字（BROWSER_NAMES）；经别的 helper 间接起浏览器、类里的测试方法、async 测试都查不出。
漏检的后果只是钩子变慢，全量 CI 仍会跑到它们（Q-018 评审，2026-10-01）。
"""
import ast
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BROWSER_NAMES = {"sync_playwright", "async_playwright", "open_deck", "open_fixture_page", "open_built_deck",
                 "preview", "run_js_units", "samples_page", "shoot", "chromium"}
BROWSER_SCRIPTS = ("preview_slides.py",)
ACCEPTED_MARKS = {"smoke", "slow"}


def mark_names(expression):
    """从 pytest.mark.X / pytest.mark.X(...) 或它们组成的列表里取出标记名。"""
    if isinstance(expression, (ast.List, ast.Tuple)):
        return {name for element in expression.elts for name in mark_names(element)}
    if isinstance(expression, ast.Call):
        expression = expression.func
    if isinstance(expression, ast.Attribute) and isinstance(expression.value, ast.Attribute) and expression.value.attr == "mark":
        return {expression.attr}
    return set()


def module_marks(tree):
    marks = set()
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in statement.targets):
            marks |= mark_names(statement.value)
    return marks


def launches_browser(function):
    argument_names = {argument.arg for argument in function.args.args}
    used_names = {node.id for node in ast.walk(function) if isinstance(node, ast.Name)}
    used_attributes = {node.attr for node in ast.walk(function) if isinstance(node, ast.Attribute)}
    used_strings = [node.value for node in ast.walk(function) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    return bool((argument_names | used_names | used_attributes) & BROWSER_NAMES
                or any(script in text for text in used_strings for script in BROWSER_SCRIPTS))


def unmarked_browser_tests():
    unmarked = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        file_marks = module_marks(tree)
        for function in tree.body:
            if not (isinstance(function, ast.FunctionDef) and function.name.startswith("test_")):
                continue
            own_marks = file_marks | {name for decorator in function.decorator_list for name in mark_names(decorator)}
            if launches_browser(function) and not own_marks & ACCEPTED_MARKS:
                unmarked.append(f"{path.name}::{function.name}")
    return unmarked


def test_every_browser_test_carries_smoke_or_slow():
    assert unmarked_browser_tests() == []


def test_guard_sees_browser_tests_in_the_repo():
    browser_test_count = 0
    for path in TESTS_DIR.glob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        browser_test_count += sum(1 for function in tree.body
                                  if isinstance(function, ast.FunctionDef) and function.name.startswith("test_")
                                  and launches_browser(function))
    assert browser_test_count >= 40
