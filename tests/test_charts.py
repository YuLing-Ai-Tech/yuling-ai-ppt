"""数据图冒烟（M4 先做的 4 种）：柱高与数值成比例、折线点的高低顺序、环饼各段加起来一整圈、KPI 数字滚到终值；坏数据报页码。"""
import subprocess
import sys

import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import FIXTURES, REPO, build_slides, open_deck, preview

pytestmark = pytest.mark.smoke

REWIND_CHART_ANIMATIONS = """(() => {
  const animations = [...document.querySelectorAll('.slide.active .chart')].flatMap(figure => figure.getAnimations({ subtree: true }));
  animations.forEach(animation => { animation.pause(); animation.currentTime = 0; });
  return animations.length;
})()"""
FINISH_ENTRANCES = "document.getAnimations().forEach(a => { if (a.effect.getTiming().iterations !== Infinity) a.finish(); })"


def build_charts(tmp_path, name="数据图"):
    out = tmp_path / f"{name}.html"
    built = subprocess.run([sys.executable, "tools/build_deck.py", "--deck", str(FIXTURES / name), "--engine-root", ".",
                            "--out", str(out)], cwd=REPO, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    return out


@pytest.fixture
def charts_page(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, build_charts(tmp_path), 1)
        yield page, errors
        browser.close()


def test_bars_are_proportional_to_values_and_grow_from_zero(charts_page):
    page, errors = charts_page
    assert page.evaluate(REWIND_CHART_ANIMATIONS) > 0  # 柱有动画
    first_frame = page.evaluate("[...document.querySelectorAll('.slide.active .chart .bar')].map(bar => getComputedStyle(bar).transform)")
    assert first_frame == ["matrix(1, 0, 0, 0, 0, 0)"] * 6  # 首帧柱高为 0（scaleY(0)）
    page.evaluate(FINISH_ENTRANCES)
    bars = page.evaluate("""[...document.querySelectorAll('.slide.active .chart .bar')].map(bar =>
      [bar.dataset.tone, +bar.getAttribute('y') + +bar.getAttribute('height'), +bar.getAttribute('height'), getComputedStyle(bar).transform])""")
    assert [tone for tone, *_ in bars] == ["1", "1", "1", "2", "2", "2"]  # 先画第 1 组（期中）的 3 根，再画第 2 组
    zero_line = page.evaluate("+[...document.querySelectorAll('.slide.active .chart .tick-label')].find(t => t.textContent === '0').getAttribute('y')")
    assert {round(bottom, 3) for _, bottom, _, _ in bars} == {round(zero_line, 3)}  # 都从纵轴的 0 刻度线长出
    heights = [height for _, _, height, _ in bars]
    assert abs(heights[0] / heights[1] - 80 / 90) < 1e-6 and abs(heights[2] / heights[5] - 60 / 72) < 1e-6
    assert all(transform == "matrix(1, 0, 0, 1, 0, 0)" for *_, transform in bars) and errors == []  # 长到原高
    assert page.evaluate("window.diagramProblems") == []


def test_line_points_follow_values_and_line_is_drawn(charts_page):
    page, errors = charts_page
    page.evaluate("show(1)")
    assert page.evaluate(REWIND_CHART_ANIMATIONS) > 0
    first_frame = page.evaluate("""(() => { const line = document.querySelector('.slide.active .chart .line'); const style = getComputedStyle(line);
      return [parseFloat(style.strokeDashoffset), parseFloat(line.style.getPropertyValue('--len')),
        [...document.querySelectorAll('.slide.active .chart .dot')].map(dot => getComputedStyle(dot).opacity)]; })()""")
    assert abs(first_frame[0] - first_frame[1]) < 0.01 and first_frame[1] > 0 and first_frame[2] == ["0"] * 4  # 首帧整条线还没描出来、点还没出现
    page.evaluate(FINISH_ENTRANCES)
    ys = page.evaluate("[...document.querySelectorAll('.slide.active .chart .dot')].map(dot => +dot.getAttribute('cy'))")
    offset = page.evaluate("getComputedStyle(document.querySelector('.slide.active .chart .line')).strokeDashoffset")
    assert ys[3] < ys[1] < ys[2] < ys[0]  # 86 最高、72 最低（SVG 的 y 向下）
    assert offset == "0px" and errors == []


def test_donut_slices_close_the_ring_and_kpi_counts_to_final_value(charts_page):
    page, errors = charts_page
    page.evaluate("show(2)")
    assert page.evaluate(REWIND_CHART_ANIMATIONS) > 0
    first_frame = page.evaluate("[...document.querySelectorAll('.slide.active .chart .slice')].map(slice => getComputedStyle(slice).strokeDasharray)")
    assert first_frame == ["0px, 100px"] * 4  # 首帧所有扇区都没展开
    page.evaluate(FINISH_ENTRANCES)
    slices = page.evaluate("""[...document.querySelectorAll('.slide.active .chart .slice')].map(slice =>
      [parseFloat(slice.getAttribute('stroke-dasharray')), parseFloat(slice.getAttribute('stroke-dashoffset')), getComputedStyle(slice).strokeDasharray])""")
    labels = page.evaluate("[...document.querySelectorAll('.slide.active .chart .cat-label')].map(label => label.textContent)")
    assert [length for length, _, _ in slices] == [20, 40, 30, 10] and [start for _, start, _ in slices] == [0, -20, -60, -90]
    assert slices[1][2] == "40px, 100px"  # 动画结束后回到属性给的长度
    assert labels == ["优  20%", "良  40%", "中  30%", "待提高  10%"]
    page.evaluate("show(3)")
    page.wait_for_timeout(1000)  # 内核的数字滚动 0.5 秒后开始：此刻在滚动途中
    rolling = page.evaluate("document.querySelector('.slide.active .kpi-value').textContent")
    assert rolling != "92.5%" and 0 < float(rolling.rstrip("%")) < 92.5
    page.wait_for_timeout(1600)  # 内核的数字滚动 0.5 秒后开始、1.6 秒滚完
    assert page.evaluate("document.querySelector('.slide.active .kpi-value').textContent") == "92.5%" and errors == []


def test_bad_chart_data_is_reported_with_page_and_type(tmp_path):
    previewed = preview(build_charts(tmp_path, "数据图-坏"), tmp_path / "shots")
    assert previewed.returncode == 1
    assert "连线检查：第 1 页 数据图 bar：第 1 组 values 要有 3 个数" in previewed.stdout
    assert "连线检查：第 1 页 数据图 pie：data-chart 只能是 bar、line、donut、kpi、funnel、matrix、ranking" in previewed.stdout


def test_business_charts_render_labels_and_deterministic_ranking(tmp_path):
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, build_charts(tmp_path, "数据图-商业"), 1)
        assert page.evaluate("document.querySelectorAll('.slide.active .chart .funnel-stage').length") == 4
        assert page.evaluate("[...document.querySelectorAll('.slide.active .funnel-label')].map(node => node.textContent)") == ["触达", "打开", "领券", "到店"]
        page.evaluate("show(1)")
        assert page.evaluate("document.querySelectorAll('.slide.active .chart .matrix-point').length") == 3
        assert page.evaluate("document.querySelector('.slide.active .chart svg').viewBox.baseVal.width") > 100
        assert page.evaluate("document.querySelector('.slide.active .chart .matrix-point').getBoundingClientRect().width") > 5
        assert page.evaluate("[...document.querySelectorAll('.slide.active .matrix-point-label')].map(node => node.textContent)") == ["排班", "文案", "设备"]
        page.evaluate("show(2)")
        assert page.evaluate("[...document.querySelectorAll('.slide.active .ranking-label')].map(node => node.textContent)") == ["1. 宁波", "2. 杭州", "3. 上海"]
        page.wait_for_timeout(1000)
        assert page.evaluate("document.querySelector('.slide.active .chart .ranking-bar').getBoundingClientRect().width") > 5
        assert page.evaluate("window.diagramProblems") == [] and errors == []
        browser.close()


def test_single_series_bars_use_distinct_category_colours(tmp_path):
    body = '''<section class="slide" data-section="品类销售">
      <h2>各品类销售对比</h2>
      <figure class="chart" data-chart="bar"><script type="application/json">
        {"labels":["热餐","饮品","烘焙","零食","生鲜"],"series":[{"name":"销售额","values":[320,210,150,120,95]}]}
      </script></figure>
    </section>'''
    built = build_slides(tmp_path, {"01_品类.html": body})
    assert built.returncode == 0, built.stderr
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "out.html", 1)
        tones = page.evaluate("[...document.querySelectorAll('.slide.active .chart .bar')].map(node => node.dataset.tone)")
        colours = page.evaluate("[...document.querySelectorAll('.slide.active .chart .bar')].map(node => getComputedStyle(node).fill)")
        assert page.evaluate("document.querySelector('.slide.active .chart svg').viewBox.baseVal.width") > 100
        assert page.evaluate("document.querySelector('.slide.active .chart .bar').getBoundingClientRect().width") > 5
        assert tones == ["1", "2", "3", "4", "5"]
        assert len(set(colours)) == 5
        assert errors == []
        browser.close()
