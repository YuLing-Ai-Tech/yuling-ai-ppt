"""放映时拖动（Q-017 D2 形态 A）：开关、拖动后 data-at 吸附 0.1 格并重画连线、移动阈值内算点选、拖完不触发聚焦、
没揭示的元素拖不动、拖动模式暂停触摸翻页、重画保持分步状态且跳过登场动画、按钮只在含图元的课件出现。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_fixture, build_slides, open_deck

pytestmark = pytest.mark.smoke

AT = "id => document.querySelector(`.slide.active [data-id=\"${id}\"]`).dataset.at"
WIRE = "edge => document.querySelector(`.slide.active .dg .wire[data-edge=\"${edge}\"]`)"
NOT_FOCUSING = "document.querySelector('.dg.is-focusing') === null"


def center_of(page, node_id):
    box = page.locator(f'.slide.active [data-id="{node_id}"]').bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def mouse_drag(page, node_id, dx, dy):
    x, y = center_of(page, node_id)
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + dx / 2, y + dy / 2, steps=4)
    page.mouse.move(x + dx, y + dy, steps=4)
    page.mouse.up()


def cell_size(page):
    return page.evaluate("(() => { const dg = document.querySelector('.slide.active .dg'); return [dg.clientWidth / 24, dg.clientHeight / 12]; })()")


@pytest.fixture
def diagram_page(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        page.evaluate("document.getAnimations().forEach(a => { if (a.effect.getTiming().iterations !== Infinity) a.finish(); })")
        yield page, errors
        browser.close()


def test_drag_is_off_by_default(diagram_page):
    page, errors = diagram_page
    _, cell_h = cell_size(page)
    mouse_drag(page, "web", 0, cell_h)
    assert page.evaluate(f"({AT})('web')") == "0.5 4.5 6 1.8"
    assert page.evaluate("document.body.classList.contains('drag-on')") is False and errors == []


def test_drag_moves_box_snaps_and_redraws_wires_without_focusing(diagram_page):
    page, errors = diagram_page
    _, cell_h = cell_size(page)
    old_path = page.evaluate(f"({WIRE})('lb→web').getAttribute('d')")
    page.keyboard.press("t")
    mouse_drag(page, "web", 0, cell_h * 1.04)  # 1.04 格吸附成 1 格
    assert page.evaluate(f"({AT})('web')") == "0.5 5.5 6 1.8"
    assert page.evaluate(f"({WIRE})('lb→web').getAttribute('d')") != old_path
    assert page.evaluate("['.dg-wires', '.dg-packets', '.dg-labels'].map(layer => document.querySelectorAll(`.slide.active .dg > ${layer}`).length)") == [1, 1, 1]
    assert page.evaluate("window.getSelection().toString()") == ""  # 鼠标拖动不留文字选区
    assert page.evaluate("document.querySelectorAll('.slide.active .dg .wire').length") == 5
    assert page.evaluate(f"getComputedStyle(({WIRE})('lb→web')).strokeDashoffset") == "0px"  # 重画的线不再播描线动画
    assert page.evaluate(NOT_FOCUSING) and errors == []


def test_tiny_move_counts_as_click_and_focuses(diagram_page):
    page, errors = diagram_page
    page.keyboard.press("t")
    mouse_drag(page, "api", 3, 0)
    assert page.evaluate(f"({AT})('api')") == "0.5 1 6.5 1.8"
    assert not page.evaluate(NOT_FOCUSING) and errors == []


def test_swipe_turns_page_only_when_drag_is_off(diagram_page):
    page, errors = diagram_page
    swipe = """() => { const target = document.querySelector('.slide.active .dg');
      const touch = x => new Touch({ identifier: 1, target, clientX: x, clientY: 500 });
      target.dispatchEvent(new TouchEvent('touchstart', { bubbles: true, touches: [touch(1200)], changedTouches: [touch(1200)] }));
      target.dispatchEvent(new TouchEvent('touchend', { bubbles: true, touches: [], changedTouches: [touch(900)] })); }"""
    page.keyboard.press("t")
    page.evaluate(swipe)
    stayed = page.evaluate("location.hash")
    page.keyboard.press("t")
    page.evaluate(swipe)
    assert (stayed, page.evaluate("location.hash")) == ("#2", "#3") and errors == []


def test_hidden_step_box_cannot_be_dragged_and_redraw_keeps_step_state(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
        for _ in range(3):
            page.keyboard.press("ArrowRight")  # 进第 2 页（第 0 步），再揭示到第 2 步：api 在第 3 步，还藏着
        page.keyboard.press("t")
        page.evaluate("""() => { const api = document.querySelector('.slide.active [data-id="api"]');
          const fire = (type, target, y) => target.dispatchEvent(new PointerEvent(type, { bubbles: true, pointerId: 1, button: 0, clientX: 900, clientY: y }));
          fire('pointerdown', api, 400); fire('pointermove', window, 480); fire('pointerup', window, 480); }""")
        api_at = page.evaluate(f"({AT})('api')")
        _, cell_h = cell_size(page)
        mouse_drag(page, "user", 0, cell_h)
        shown = page.evaluate(f"[({WIRE})('user→lb').classList.contains('step-shown'), ({WIRE})('web→api').classList.contains('step-shown')]")
        browser.close()
    assert api_at == "0.5 1 6.5 1.8"
    assert shown == [True, False] and errors == []


def test_drag_button_only_on_decks_with_diagrams_and_hidden_until_pointer_moves(tmp_path, diagram_page):
    page, errors = diagram_page
    hidden_at_start = page.evaluate("getComputedStyle(document.getElementById('drag-toggle')).visibility")
    page.mouse.move(500, 500)
    page.click("#drag-toggle")
    assert (hidden_at_start, page.evaluate("document.body.classList.contains('drag-on')")) == ("hidden", True)
    # 没有图元的课件现场造一个（不借别的任务的夹具，拖道工作树里也能跑）；build_slides 的产物是 tmp_path / "out.html"
    assert build_slides(tmp_path, {"01_无图元.html": '<section class="slide"><h2>无图元</h2></section>'}).returncode == 0
    page.goto((tmp_path / "out.html").as_uri())
    assert page.evaluate("document.getElementById('drag-toggle')") is None and errors == []


def test_second_pointer_cannot_take_over_a_drag_in_progress(diagram_page):
    page, errors = diagram_page
    _, cell_h = cell_size(page)
    x, y = center_of(page, "web")
    page.keyboard.press("t")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + cell_h / 2, steps=4)
    page.evaluate("""() => document.querySelector('.slide.active [data-id="api"]').dispatchEvent(
      new PointerEvent('pointerdown', { bubbles: true, pointerId: 2, button: 0, clientX: 900, clientY: 300 }))""")
    page.mouse.move(x, y + cell_h, steps=4)
    page.mouse.up()
    assert page.evaluate(f"({AT})('web')") == "0.5 5.5 6 1.8"
    assert page.evaluate("document.querySelectorAll('.is-dragging').length") == 0 and errors == []


def test_closing_drag_mode_mid_drag_ends_the_drag(diagram_page):
    page, errors = diagram_page
    _, cell_h = cell_size(page)
    x, y = center_of(page, "web")
    page.keyboard.press("t")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + cell_h / 2, steps=4)
    assert page.evaluate("document.querySelectorAll('.is-dragging').length") == 1  # 拖动确实开始了
    page.keyboard.press("t")
    stopped_at = page.evaluate(f"({AT})('web')")
    page.mouse.move(x, y + cell_h * 2, steps=4)
    page.mouse.up()
    assert page.evaluate("document.querySelectorAll('.is-dragging').length") == 0
    assert page.evaluate("document.body.classList.contains('drag-on')") is False
    assert page.evaluate(f"({AT})('web')") == stopped_at and errors == []
    assert page.evaluate(NOT_FOCUSING)  # 中途关掉的拖动，松手也不触发聚焦


def test_drag_is_clamped_inside_the_diagram_area_and_inside_the_parent_container(diagram_page):
    page, errors = diagram_page
    page.keyboard.press("t")
    mouse_drag(page, "user", 3000, 2000)  # 往图区右下角外面拖
    assert page.evaluate(f"({AT})('user')") == "19.5 10.2 4.5 1.8"
    mouse_drag(page, "user", -3000, -2000)  # 再往左上角外面拖
    assert page.evaluate(f"({AT})('user')") == "0 0 4.5 1.8"
    inside = "id => { const dg = document.querySelector('.slide.active .dg').getBoundingClientRect(); const box = document.querySelector(`.slide.active [data-id=\"${id}\"]`).getBoundingClientRect(); return box.left >= dg.left - 1 && box.top >= dg.top - 1 && box.right <= dg.right + 1 && box.bottom <= dg.bottom + 1; }"
    assert page.evaluate(f"({inside})('user')")
    x, y = page.locator('.slide.active [data-id="pub"] .tab').bounding_box()["x"] + 20, page.locator('.slide.active [data-id="pub"] .tab').bounding_box()["y"] + 10
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 1500, y, steps=6)  # 拖容器 pub 往右：不能超出父容器 vpc（宽 16.5，pub 宽 7，最多到 9.5）
    page.mouse.up()
    assert page.evaluate(f"({AT})('pub')") == "9.5 1 7 7.8"
    assert page.evaluate(f"({AT})('lb')") == "0.5 1 6 1.8" and errors == []  # 子节点相对父容器，坐标不变


def test_closing_drag_mode_mid_drag_keeps_and_records_the_move(diagram_page):
    page, errors = diagram_page
    page.evaluate("""window.savedPositions = null;
      window.showSaveFilePicker = async options => ({ createWritable: async () => ({
        write: async text => { window.savedPositions = text; }, close: async () => {} }) });""")
    _, cell_h = cell_size(page)
    x, y = center_of(page, "web")
    page.keyboard.press("t")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + cell_h, steps=4)
    page.keyboard.press("t")  # 拖到一半关掉
    page.mouse.up()
    assert page.evaluate(f"({AT})('web')") == "0.5 5.5 6 1.8"  # 节点停在拖到的位置
    page.keyboard.press("t")  # 再打开，保存按钮应当出现
    assert page.evaluate("getComputedStyle(document.getElementById('drag-save')).visibility") == "visible"
    page.click("#drag-save")
    page.wait_for_function("window.savedPositions !== null")
    assert '"at": "0.5 5.5 6 1.8"' in page.evaluate("window.savedPositions") and errors == []
