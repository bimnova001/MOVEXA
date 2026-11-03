"""Environment checks for the loading screen (Qt-free, deterministic).

Eachh check returns a result the UI just renders; no window code here, so
the suite can verify machine requirements without offscreen Qt.
"""

from __future__ import annotations

import importlib.metadata
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _requirement_ok(py_version: tuple[int, int], minimum: tuple[int, int]) -> bool:
    return py_version >= minimum


def _module_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        try:
            mod = importlib.import_module(name)
            return str(getattr(mod, "__version__", "unknown"))
        except Exception:  # noqa: BLE001 - any failure just reports absent
            return ""


def collect_checks(app_version: str = "", appdata: str | None = None) -> list[CheckResult]:
    """Run every machine/library check. Slow ones (ffmpeg) run first."""
    results: list[CheckResult] = []

    pyv = sys.version_info
    py_ok = _requirement_ok((pyv.major, pyv.minor), (3, 10))
    results.append(CheckResult(
        name="Python",
        ok=py_ok,
        detail=f"{pyv.major}.{pyv.minor}.{pyv.micro} (need 3.10+)",
        required=True,
    ))

    for module, minimum, required in (
        ("PySide6", "6.5", True),
        ("Pillow", "9.0", True),
        ("numpy", "1.24", True),
    ):
        version = _module_version(module)
        ok = bool(version)
        detail = version or "not installed"
        results.append(CheckResult(
            name=module, ok=ok, detail=detail, required=required))

    ff = _ffmpeg_check()
    results.append(ff)

    results.append(_appdata_check(appdata))

    return results


def _ffmpeg_check() -> CheckResult:
    binary = shutil.which("ffmpeg")
    if binary is None:
        return CheckResult(
            name="FFmpeg", ok=False, detail="not on PATH (MP4 export disabled)",
            required=False)
    try:
        out = subprocess.run(
            [binary, "-version"], capture_output=True, text=True, timeout=10)
        first = out.stdout.splitlines()[0] if out.stdout else ""
        return CheckResult(
            name="FFmpeg", ok=True, detail=first[:80] or binary, required=False)
    except (OSError, subprocess.SubprocessError):
        return CheckResult(
            name="FFmpeg", ok=False, detail="found but failed to run",
            required=False)


def _appdata_check(appdata: str | None = None) -> CheckResult:
    root = Path(appdata or os.environ.get("APPDATA", str(Path.home())))
    try:
        # The dir may not exist on first run (fresh profiles); the meaningful
        # property is that we can create/write under it.
        if not root.exists():
            root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return CheckResult(name="User storage", ok=False,
                           detail=str(exc), required=True)
    try:
        target = Path(tempfile.mkdtemp(prefix="movexa_selftest_", dir=root))
        target.rmdir()
        return CheckResult(
            name="User storage", ok=True, detail=str(root), required=True)
    except OSError as exc:
        return CheckResult(
            name="User storage", ok=False, detail=str(exc), required=True)
