"""研究级数据图冒烟：散点、雷达、堆叠和热力矩阵必须真实画出受控 SVG，不能只有容器。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_slides, open_deck

pytestmark = pytest.mark.smoke


def advanced_slides():
    return {
        "01_scatter.html": '''<section class="slide"><h2>散点</h2><figure class="chart" data-chart="scatter"><script type="application/json">{"xAxis":{"label":"影响力","min":0,"max":100},"yAxis":{"label":"增长","min":0,"max":100},"points":[{"label":"A","x":20,"y":30,"group":"跟随"},{"label":"B","x":78,"y":82,"group":"领先"},{"label":"C","x":58,"y":46,"group":"稳定"}],"referenceLines":[{"axis":"x","value":50,"label":"基准"}]}</script></figure></section>''',
        "02_radar.html": '''<section class="slide"><h2>雷达</h2><figure class="chart" data-chart="radar"><script type="application/json">{"axes":["产品","品牌","渠道","服务"],"maxValue":100,"series":[{"name":"本品牌","values":[88,76,58,64]},{"name":"均值","values":[70,68,66,72]}]}</script></figure></section>''',
        "03_stacked.html": '''<section class="slide"><h2>堆叠</h2><figure class="chart" data-chart="stacked-bar"><script type="application/json">{"mode":"percent","labels":["Q1","Q2","Q3"],"series":[{"name":"高","values":[20,30,40]},{"name":"中","values":[35,40,40]},{"name":"低","values":[45,30,20]}]}</script></figure></section>''',
        "04_heatmap.html": '''<section class="slide"><h2>热力</h2><figure class="chart" data-chart="heatmap"><script type="application/json">{"columns":["声量","内容","转化"],"rows":[{"label":"华东","values":[82,91,88]},{"label":"华南","values":[76,70,69]},{"label":"华北","values":[68,72,63]}],"colorScale":"sequential"}</script></figure></section>''',
    }


def test_advanced_charts_render_semantic_svg_nodes(tmp_path):
    built = build_slides(tmp_path, advanced_slides())
    assert built.returncode == 0, built.stderr
    selectors = [".scatter-point", ".radar-series", ".stack-segment", ".heatmap-cell"]
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "out.html", 1)
        for page_index, selector in enumerate(selectors):
            page.evaluate(f"show({page_index}, true)")
            page.wait_for_function(f"document.querySelectorAll('.slide.active {selector}').length > 0")
            assert page.evaluate(f"document.querySelectorAll('.slide.active {selector}').length") > 0
            assert page.evaluate("window.diagramProblems") == []
        assert errors == []
        browser.close()
