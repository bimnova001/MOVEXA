"""Native Windows chrome theming: dark titlebars keep the frame row dark.

PySide QSS cannot paint the native frame, so the pro move is the DWM
attribute (Windows 10 1809+ / 11): keep all native behavior (snap, resize,
Win-key shortcuts) while matching the dark theme. Falls back silently on
other platforms.
"""

from __future__ import annotations

import sys


def apply_dark_titlebar(window) -> bool:
    """Best-effort dark titlebar; returns True when the DWM call succeeded."""
    if sys.platform != "win32":
        return False
    import ctypes
    try:
        hwnd = int(window.winId())
    except (RuntimeError, AttributeError):
        return False
    value = ctypes.c_int(1)
    # Attribute 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (19 on some builds).
    result = -1
    for attribute in (20, 19):
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
        if result == 0:
            break
    return result == 0
