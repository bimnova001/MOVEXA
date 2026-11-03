"""Environment checks feed the loading screen (pure, GUI-free)."""

from app.envcheck import _appdata_check, collect_checks


def test_collect_checks_covers_every_required_surface():
    results = collect_checks()
    names = {r.name for r in results}
    assert {"Python", "PySide6", "Pillow", "numpy", "FFmpeg",
            "User storage"} <= names
    py = next(r for r in results if r.name == "Python")
    assert py.ok and "Python" not in py.detail
    for result in results:
        assert result.ok is result.required or not result.required or result.ok
        assert result.detail


def test_all_required_pass_on_dev_machine():
    for result in collect_checks():
        if result.required:
            assert result.ok, f"{result.name} failing: {result.detail}"


def test_appdata_check_reports_failure_cleanly(tmp_path):
    blocked = tmp_path / "blocked.bin"
    blocked.write_bytes(b"x")
    result = _appdata_check(str(blocked))  # not a directory -> OSError path
    assert result.ok is False and result.name == "User storage"


def test_appdata_check_accepts_existing_directory(tmp_path):
    result = _appdata_check(str(tmp_path))
    assert result.ok is True
