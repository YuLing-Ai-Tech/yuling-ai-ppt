"""Fail closed when a platform visual baseline or its environment changes."""
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import json
import subprocess
import sys


def platform_key(system=None, architecture=None):
    system = sys.platform if system is None else system
    architecture = platform.machine() if architecture is None else architecture
    if system == "darwin" and architecture.lower() == "arm64":
        return "darwin-arm64"
    if system not in ("win32", "linux") or architecture.lower() not in ("amd64", "x86_64", "x64"):
        raise ValueError(f"Unsupported visual platform: {system}/{architecture}")
    return f"{system}-x64"


def platform_baseline(root, system=None, architecture=None):
    directory = Path(root) / "platforms" / platform_key(system, architecture)
    if not (directory / "manifest.json").is_file():
        if directory.name == "darwin-arm64":
            raise ValueError("Mac visual baseline not established; capture candidates and obtain owner approval")
        raise ValueError(f"Platform visual baseline missing: {directory.name}")
    return directory


def font_inventory_fingerprint(root=None, system=None):
    system = sys.platform if system is None else system
    if system == "darwin":
        inventory = subprocess.check_output(
            ["/usr/sbin/system_profiler", "-json", "SPFontsDataType"], timeout=60)
        return mac_font_fingerprint(json.loads(inventory))
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


def mac_font_fingerprint(inventory):
    """Hash registered font files, including libraries outside default directories.

    Unknown/incomplete profiler output is an error, never an empty fingerprint.
    Raw paths stay local; the manifest stores only the aggregate digest.
    """
    records = inventory.get("SPFontsDataType") if isinstance(inventory, dict) else None
    if not isinstance(records, list) or not records:
        raise ValueError("Mac font inventory is empty or unsupported")
    entries = {}
    for record in records:
        filename = record.get("path") if isinstance(record, dict) else None
        if not isinstance(filename, str) or not Path(filename).is_absolute():
            raise ValueError("Mac font inventory has a missing file path")
        path = Path(filename).resolve(strict=True)
        relative = ("user/" + path.relative_to(Path.home()).as_posix()
                    if path.is_relative_to(Path.home()) else "root/" + path.as_posix().lstrip("/"))
        entries[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    text = "".join(f"{name}\0{entries[name]}\n" for name in sorted(entries, key=lambda value: value.encode("utf-8")))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reserve_candidate_directory(directory):
    directory = Path(directory).resolve()
    if directory.exists():
        raise ValueError("Candidate output already exists; choose a new evidence directory")
    if any((parent / ".git").exists() for parent in (directory, *directory.parents)):
        raise ValueError("Candidate output must be outside Git repositories")
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def environment_snapshot(browser_path, chrome_version, browser_args, viewport):
    key = platform_key()
    if not browser_path or not Path(browser_path).is_file():
        raise ValueError("Set PPT_CHROME_PATH to the approved visual browser")
    snapshot = {
        "platform": key.rsplit("-", 1)[0], "architecture": key.rsplit("-", 1)[1],
        "chromeVersion": chrome_version,
        "playwrightVersion": importlib.metadata.version("playwright"),
        "browserSha256": hashlib.sha256(Path(browser_path).read_bytes()).hexdigest(),
        "fontInventorySha256": font_inventory_fingerprint(),
        "browserArgs": list(browser_args), "viewport": dict(viewport),
    }
    if key == "darwin-arm64":
        snapshot["macOS"] = subprocess.check_output(["/usr/bin/sw_vers"], timeout=15).decode().strip()
        snapshot["fontInventoryMethod"] = "system_profiler-SPFontsDataType-path-v1"
    return snapshot


def require_environment(expected, actual):
    if not isinstance(expected, dict):
        raise ValueError("Platform baseline environment missing")
    for key, value in actual.items():
        if key not in expected or expected[key] != value:
            raise ValueError(f"Visual environment mismatch: {key}; restore the approved environment")
