"""图元与分步的纯函数单元测试：JS 在 playwright 空白页里跑（设计 §6 第 2 项），每个测试文件一条 pytest。"""
import pytest

from tests.js_units import run_js_units

pytestmark = pytest.mark.smoke

JS_UNIT_SUITES = {
    "tests/js/test-layout.js": ["components/diagram/layout.js"],
    "tests/js/test-route.js": ["components/diagram/layout.js", "components/diagram/route.js"],
    "tests/js/test-check.js": ["components/diagram/layout.js", "components/diagram/route.js", "components/diagram/check.js"],
    "tests/js/test-steps.js": ["runtime/steps.js"],
    "tests/js/test-focus.js": ["components/diagram/focus-graph.js"],
    "tests/js/test-unit-runner.js": [],
}


@pytest.mark.parametrize("test_path", sorted(JS_UNIT_SUITES))
def test_js_unit_suite(test_path):
    results, page_errors = run_js_units(JS_UNIT_SUITES[test_path], test_path)
    assert page_errors == []
    assert results, "一条用例都没跑到"
    assert [f"{result['name']}：{result['message']}" for result in results if not result["ok"]] == []
