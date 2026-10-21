"""Mac routing and candidate safety, without claiming native Mac acceptance."""
import subprocess
import sys

import pytest

from tools import visual_environment as visual
from tools import regress


def test_mac_routes_to_its_own_target(tmp_path):
    assert visual.platform_key("darwin", "arm64") == "darwin-arm64"
    with pytest.raises(ValueError, match="Mac visual baseline not established"):
        visual.platform_baseline(tmp_path, "darwin", "arm64")
    target = tmp_path / "platforms/darwin-arm64"
    target.mkdir(parents=True)
    (target / "manifest.json").write_text("{}")
    assert visual.platform_baseline(tmp_path, "darwin", "arm64") == target


def test_registered_mac_fonts_include_custom_locations_and_fail_closed(tmp_path):
    font = tmp_path / "custom library/font.otf"
    font.parent.mkdir()
    font.write_bytes(b"font")
    inventory = {"SPFontsDataType": [{"path": str(font)}]}
    fingerprint = visual.mac_font_fingerprint(inventory)
    font.write_bytes(b"changed")
    assert visual.mac_font_fingerprint(inventory) != fingerprint
    for invalid in ({}, {"SPFontsDataType": []}, {"SPFontsDataType": [{}]}):
        with pytest.raises(ValueError, match="font inventory"):
            visual.mac_font_fingerprint(invalid)
    font.unlink()
    with pytest.raises((OSError, ValueError)):
        visual.mac_font_fingerprint(inventory)


def test_candidate_cli_rejects_existing_output_without_touching_it(tmp_path):
    marker = tmp_path / "keep.txt"
    marker.write_text("keep")
    result = subprocess.run([sys.executable, str(regress.HERE / "regress.py"),
                             "candidate", "--suite", "图元样板", "--work", str(tmp_path)],
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode != 0
    assert "Candidate output already exists" in result.stderr
    assert marker.read_text() == "keep"


def test_candidate_output_cannot_be_inside_any_repository(tmp_path):
    (tmp_path / ".git").write_text("gitdir: elsewhere")
    with pytest.raises(ValueError, match="outside Git repositories"):
        visual.reserve_candidate_directory(tmp_path / "new")
    assert not (tmp_path / "new").exists()


def test_mac_os_drift_is_rejected():
    with pytest.raises(ValueError, match="macOS"):
        visual.require_environment({"macOS": "old"}, {"macOS": "new"})
