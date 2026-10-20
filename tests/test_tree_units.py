"""树布局纯函数的 JS 单元测试（在 playwright 空白页里跑）。单独成文件，免得和别的任务同改 test_diagram_units.py。"""
import pytest

from tests.js_units import run_js_units

pytestmark = pytest.mark.smoke


def test_tree_layout_units():
    results, page_errors = run_js_units(["components/diagram/tree.js"], "tests/js/test-tree.js")
    assert page_errors == []
    assert results, "一条用例都没跑到"
    assert [f"{result['name']}：{result['message']}" for result in results if not result["ok"]] == []
