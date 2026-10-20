import json
from pathlib import Path

import pytest

from tools.build_deck import motion_body_attributes

REPO = Path(__file__).resolve().parent.parent


def test_motion_config_is_restricted_to_controlled_values():
    attributes = motion_body_attributes({
        "persona": "training",
        "recipe": "kinetic-classroom",
        "background": "kinetic-grid",
        "transition": "directional",
        "fingerprint": "v1:0123456789abcdef",
    })
    assert 'data-motion-persona="training"' in attributes
    assert 'data-motion-fingerprint="v1:0123456789abcdef"' in attributes
    with pytest.raises(SystemExit):
        motion_body_attributes({"background": "url(https://example.invalid)"})


def test_apple_manifest_bundles_motion_runtime():
    manifest = json.loads((REPO / "styles" / "苹果风" / "manifest.json").read_text())
    assert "styles/苹果风/motion.css" in manifest["css"]
    assert "runtime/motion.js" in manifest["js"]


def test_motion_styles_cover_effects_transitions_and_reduced_motion():
    css = (REPO / "styles" / "苹果风" / "motion.css").read_text()
    for value in ("chart-draw", "ranking-race", "branch-grow", "table-cascade", "hero-focus"):
        assert f'data-motion-effect="{value}"' in css
    for value in ("depth", "directional", "wipe"):
        assert f'data-motion-transition="{value}"' in css
    assert "prefers-reduced-motion:reduce" in css


def test_stamp_entrance_finishes_without_a_residual_rotation():
    css = (REPO / "runtime" / "entrance.css").read_text()
    stamp = css.split("@keyframes a-stamp", 1)[1].split("}", 2)
    assert "transform: none" in stamp[1]
    assert "rotate(-4deg)" not in stamp[1]
