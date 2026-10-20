"""图元样板 9 页和 baselines/图元样板 的回归比对。单独成文件：test_diagram_samples.py 的同步 playwright 夹具会让事件循环常驻，
同进程里再调 regress 的 asyncio.run 会报 "cannot be called from a running event loop"。"""
import shutil
from pathlib import Path

import pytest

from tools import regress

REPO = Path(__file__).resolve().parent.parent
DECK_DIR = REPO / "examples/图元样板"
BASELINE_DIR = REPO / "baselines/图元样板"


def test_diagram_baseline_manifest_matches_pngs():
    assert regress.verify_baseline_manifest(BASELINE_DIR) == []
    for key in ("win32-x64", "linux-x64"):
        assert regress.verify_baseline_manifest(BASELINE_DIR / "platforms" / key) == []


@pytest.mark.slow
def test_diagram_samples_match_baseline_zero_diff(tmp_path):
    assert regress.run_engine_check(REPO, tmp_path, DECK_DIR, regress.platform_baseline(BASELINE_DIR)) == (True, [])


@pytest.mark.slow
def test_diagram_samples_shot_twice_identical(tmp_path):
    deck_path = regress.build_example_deck(REPO, tmp_path / "build", DECK_DIR)
    assert regress.shoot(deck_path, tmp_path / "a")
    assert regress.shoot(deck_path, tmp_path / "b")
    assert regress.compare_shots(tmp_path / "a", tmp_path / "b", tmp_path / "d") == (True, [])


@pytest.mark.slow
def test_flow_human_mutation_is_caught_on_pages_4_and_5(tmp_path):
    control_deck = regress.build_example_deck(REPO, tmp_path / "control-build", DECK_DIR)
    assert regress.shoot(control_deck, tmp_path / "control-shots")

    root = tmp_path / "root"
    for name in ("runtime", "components", "styles"):
        shutil.copytree(REPO / name, root / name)
    token_file = root / "styles/苹果风/tokens.css"
    assert token_file.read_text().count("--flow-human: #FF2D55;") == 1
    token_file.write_text(token_file.read_text().replace("--flow-human: #FF2D55;", "--flow-human: #2DFF55;"))
    # 样板里只有流程图（第 4 页）和泳道（第 5 页）用了 human 类连线
    mutated_deck = regress.build_example_deck(root, tmp_path / "mutated-build", DECK_DIR)
    assert regress.shoot(mutated_deck, tmp_path / "mutated-shots")
    assert regress.compare_shots(
        tmp_path / "control-shots", tmp_path / "mutated-shots", tmp_path / "mutation-diffs"
    ) == (False, [4, 5])
