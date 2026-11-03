"""Make repo root importable regardless of where pytest is launched from."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolated_appdata(tmp_path, monkeypatch):
    """Redirect recents storage so tests never touch the real user profile."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
