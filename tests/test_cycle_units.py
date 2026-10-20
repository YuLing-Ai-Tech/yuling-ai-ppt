"""循环图纯函数的 JS 单元测试（在 playwright 空白页里跑）。"""
import pytest

from tests.js_units import run_js_units

pytestmark = pytest.mark.smoke


def test_cycle_layout_units():
    results, page_errors = run_js_units(["components/diagram/route.js", "components/diagram/cycle.js"], "tests/js/test-cycle.js")
    assert page_errors == []
    assert results, "一条用例都没跑到"
    assert [f"{result['name']}：{result['message']}" for result in results if not result["ok"]] == []
