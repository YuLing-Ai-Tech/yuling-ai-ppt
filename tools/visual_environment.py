"""Fail closed when a platform visual baseline or its environment changes."""
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import sys


def platform_key(system=None, architecture=None):
    system = sys.platform if system is None else system
    architecture = platform.machine() if architecture is None else architecture
    if system not in ("win32", "linux") or architecture.lower() not in ("amd64", "x86_64", "x64"):
        raise ValueError(f"Unsupported visual platform: {system}/{architecture}")
    return f"{system}-x64"


def platform_baseline(root, system=None, architecture=None):
    directory = Path(root) / "platforms" / platform_key(system, architecture)
    if not (directory / "manifest.json").is_file():
        raise ValueError(f"Platform visual baseline missing: {directory.name}")
    return directory


def font_inventory_fingerprint(root=None, system=None):
    system = sys.platform if system is None else system
    platform_key(system, "x64")
    root = Path(root) if root is not None else (
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" if system == "win32" else Path("/usr/share/fonts")
    )
    if not root.is_dir():
        raise ValueError("Visual font directory missing")
    candidates = root.iterdir() if system == "win32" else root.rglob("*")
    entries = {}
    for path in candidates:
        if path.is_file() and (system != "win32" or path.suffix.lower() in (".ttf", ".ttc", ".otf")):
            entries[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not entries:
        raise ValueError("Visual font inventory is empty")
    text = "".join(f"{name}\0{entries[name]}\n" for name in sorted(entries, key=lambda value: value.encode("utf-8")))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def environment_snapshot(browser_path, chrome_version, browser_args, viewport):
    key = platform_key()
    if not browser_path or not Path(browser_path).is_file():
        raise ValueError("Set PPT_CHROME_PATH to the approved visual browser")
    return {
        "platform": key.rsplit("-", 1)[0], "architecture": "x64",
        "chromeVersion": chrome_version,
        "playwrightVersion": importlib.metadata.version("playwright"),
        "browserSha256": hashlib.sha256(Path(browser_path).read_bytes()).hexdigest(),
        "fontInventorySha256": font_inventory_fingerprint(),
        "browserArgs": list(browser_args), "viewport": dict(viewport),
    }


def require_environment(expected, actual):
    if not isinstance(expected, dict):
        raise ValueError("Platform baseline environment missing")
    for key, value in actual.items():
        if key not in expected or expected[key] != value:
            raise ValueError(f"Visual environment mismatch: {key}; restore the approved environment")
