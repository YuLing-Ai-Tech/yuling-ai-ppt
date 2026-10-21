"""Platform selection and environment drift must never silently skip visual QA."""
import hashlib
import json

import pytest

from tools import regress
from tools.visual_environment import font_inventory_fingerprint, platform_baseline, platform_key, require_environment


@pytest.mark.parametrize("system,arch,key", [("win32", "AMD64", "win32-x64"), ("linux", "x86_64", "linux-x64")])
def test_platform_selects_its_own_baseline(tmp_path, system, arch, key):
    directory = tmp_path / "platforms" / key
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text("{}", encoding="utf-8")
    assert platform_baseline(tmp_path, system, arch) == directory


@pytest.mark.parametrize("system,arch", [("darwin", "x64"), ("linux", "arm64"), ("win32", "x86")])
def test_unsupported_visual_platform_is_an_error(system, arch):
    with pytest.raises(ValueError, match="Unsupported visual platform"):
        platform_key(system, arch)


def test_missing_platform_has_no_historical_fallback(tmp_path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="baseline missing"):
        platform_baseline(tmp_path, "win32", "x64")


@pytest.mark.parametrize("key", ["platform", "architecture", "chromeVersion", "playwrightVersion", "browserSha256", "fontInventorySha256", "browserArgs", "viewport"])
def test_environment_drift_is_an_error(key):
    actual = {key: "actual"}
    with pytest.raises(ValueError, match=key):
        require_environment({key: "wrong"}, actual)
    with pytest.raises(ValueError, match=key):
        require_environment({}, actual)


def test_environment_metadata_is_required():
    with pytest.raises(ValueError, match="environment missing"):
        require_environment(None, {"platform": "linux"})


def test_png_loss_and_corruption_are_detected(tmp_path):
    image = tmp_path / "p01.png"
    image.write_bytes(b"approved image")
    manifest = {"sha256": {image.name: hashlib.sha256(image.read_bytes()).hexdigest()}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert regress.verify_baseline_manifest(tmp_path) == []
    image.write_bytes(b"corrupted image")
    assert regress.verify_baseline_manifest(tmp_path) == ["p01.png"]
    image.unlink()
    assert regress.verify_baseline_manifest(tmp_path) == ["p01.png"]


def test_font_changes_are_detected_with_relative_paths(tmp_path):
    (tmp_path / "one.ttf").write_bytes(b"approved font")
    before = font_inventory_fingerprint(tmp_path, "win32")
    (tmp_path / "readme.txt").write_bytes(b"not a Windows font")
    assert font_inventory_fingerprint(tmp_path, "win32") == before
    (tmp_path / "one.ttf").write_bytes(b"different font")
    assert font_inventory_fingerprint(tmp_path, "win32") != before
