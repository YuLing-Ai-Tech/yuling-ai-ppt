"""连线流动：CSS 动画、速度令牌、S 键暂停、定格、风格豁免。"""
import pytest
from playwright.sync_api import sync_playwright

from tests.diagram_helpers import build_fixture, open_deck, wait_for_entrance_settled

pytestmark = pytest.mark.smoke


FLOW_STATE = ("[...document.querySelectorAll('.slide.active :is(.flowline, .packet, .halo)')]"
              ".map(e => [getComputedStyle(e).animationName, getComputedStyle(e).animationPlayState.split(', ').pop()])")  # 状态取最后一个动画（循环那个）


def test_flow_is_css_animation_paced_by_token_and_s_key_pauses_it(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        running = page.evaluate(FLOW_STATE)
        dash_duration = page.evaluate("getComputedStyle(document.querySelector('.slide.active .flowline')).animationDuration")
        page.keyboard.press("s")
        paused = page.evaluate(FLOW_STATE)
        page.keyboard.press("s")
        resumed = page.evaluate(FLOW_STATE)
        browser.close()
    # 冒烟页：1 条带数据包的流动线（虚线 + 1 个数据包）+ 1 个呼吸光环
    assert sorted(name for name, _ in running) == ["dg-fade, dg-dash", "dg-fade, dg-run", "dg-halo"]
    assert all("running" in state for _, state in running) and all("running" not in state for _, state in paused)
    assert all("running" in state for _, state in resumed)
    assert dash_duration == "0.5s, 3.5s"  # 140 像素一个周期 ÷ --flow-speed 40
    assert errors == []


def go_to_diagram_page(page):
    page.keyboard.press("End")  # 按 → 会先走分步揭示（连线是隐藏的）；从第 3 页退回第 2 页才是"全部揭示"
    page.keyboard.press("ArrowLeft")


def test_flow_freezes_after_settle_and_s_key_cannot_restart_it(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
        page.clock.install()  # 假时钟：不真等 7 秒，定格的 setTimeout 由它推进
        go_to_diagram_page(page)
        page.clock.run_for(200)
        before_settle = page.evaluate(FLOW_STATE)
        page.clock.run_for(6900)
        settled = page.evaluate(FLOW_STATE)
        page.keyboard.press("s")
        page.keyboard.press("s")
        after_toggle = page.evaluate(FLOW_STATE)
        browser.close()
    assert len(before_settle) == 3 and all("running" in state for _, state in before_settle)
    assert len(settled) == 3 and all("running" not in state for _, state in settled)
    assert all("running" not in state for _, state in after_toggle)
    assert errors == []


def test_changing_flow_speed_token_rescales_dash_and_packet_durations(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    durations_script = """() => ({
      dash: getComputedStyle(document.querySelector('.slide.active .flowline')).animationDuration,
      packet: getComputedStyle(document.querySelector('.slide.active .packet')).animationDuration,
      length: Number(document.querySelector('.slide.active .packet').style.getPropertyValue('--len')) })"""
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        at_40 = page.evaluate(durations_script)
        page.evaluate("document.documentElement.style.setProperty('--flow-speed', '80')")
        at_80 = page.evaluate(durations_script)
        browser.close()
    assert at_40["dash"] == "0.5s, 3.5s" and at_80["dash"] == "0.5s, 1.75s"
    packet_seconds_at_40 = float(at_40["packet"].split(", ")[1].rstrip("s"))
    packet_seconds_at_80 = float(at_80["packet"].split(", ")[1].rstrip("s"))
    assert abs(packet_seconds_at_40 - at_40["length"] / 40) < 0.01
    assert abs(packet_seconds_at_80 - at_40["length"] / 80) < 0.01
    assert errors == []


def test_s_pressed_on_earlier_page_pauses_flow_motion_but_not_entrance_fade(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
        page.keyboard.press("s")
        go_to_diagram_page(page)
        wait_for_entrance_settled(page)
        flow_opacity = page.evaluate("[...document.querySelectorAll('.slide.active :is(.flowline, .packet)')].map(e => getComputedStyle(e).opacity)")
        loop_states = page.evaluate(FLOW_STATE)
        node_states = page.evaluate("[...document.querySelectorAll('.slide.active .node[data-flow]')].map(e => getComputedStyle(e).animationPlayState)")
        browser.close()
    assert flow_opacity == ["1", "1"]
    assert len(loop_states) == 3 and all("paused" in state for _, state in loop_states)
    assert node_states == ["running"]
    assert errors == []


def test_s_key_beats_a_second_styles_settle_exemption_however_it_is_written(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    exemptions = [".slide.settled [data-flow]", "body .slide.settled [data-flow]",
                  "body.is-settled .slide.settled [data-flow]:not(.x):not(.y)"]
    for exemption in exemptions:
        with sync_playwright() as playwright:
            browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 1)
            page.clock.install()
            page.add_style_tag(content=exemption + " { animation-play-state: running !important; }")
            go_to_diagram_page(page)
            page.clock.run_for(7100)
            exempt_running = page.evaluate(FLOW_STATE)
            page.keyboard.press("s")
            pressed = page.evaluate(FLOW_STATE)
            browser.close()
        assert len(exempt_running) == 3 and all("running" in state for _, state in exempt_running), exemption
        assert all("paused" in state for _, state in pressed), exemption
        assert errors == []


def test_modifier_s_shortcuts_do_not_toggle_flow_pause(tmp_path):
    assert build_fixture("图元冒烟", tmp_path / "deck.html").returncode == 0
    with sync_playwright() as playwright:
        browser, page, errors = open_deck(playwright, tmp_path / "deck.html", 2)
        for chord in ("Meta+s", "Control+s", "Alt+s"):
            page.keyboard.press(chord)
        with_modifiers = page.evaluate("document.body.classList.contains('flow-paused')")
        page.keyboard.press("s")
        plain = page.evaluate("document.body.classList.contains('flow-paused')")
        browser.close()
    assert with_modifiers is False and plain is True and errors == []
