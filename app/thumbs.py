"""Dashboard project thumbnails.

Rendered straight from the project JSON (shapes + text at real stage
coordinates) so a card shows a true-looking scene preview without opening
the project into the live editor session or touching its controller.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap

# Stage frame color matches the theme border token.
BORDER = "#2a2a33"

THUMB_W = 320


def _stage(data: dict) -> tuple[int, int]:
    settings = data.get("settings") or {}
    return int(settings.get("width", 1920)), int(settings.get("height", 1080))


def _round(p: float) -> int:
    return int(round(p))


def render_project_pixmap(data: dict, width: int = THUMB_W) -> QPixmap | None:
    """Paint the first scene with objects onto a pixmap (pure, no engine)."""
    scenes = data.get("scenes") or []
    if not scenes:
        return None
    scene = scenes[0]
    sw, sh = _stage(data)
    scale = width / max(1, sw)
    height = _round(sh * scale)
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(scene.get("background_color", "#101018")))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont("Segoe UI", _round(8))
    painter.setFont(font)
    if not scene.get("objects"):
        painter.setPen(QColor(70, 70, 84))
        big = QFont("Segoe UI", _round(22))
        painter.setFont(big)
        painter.drawText(QRectF(0, 0, width, height),
                         Qt.AlignmentFlag.AlignCenter, "▦")
        painter.setFont(font)
    for obj in scene.get("objects", []):
        color = QColor(obj.get("color", "#7c4dff"))
        x, y = float(obj.get("x", sw / 2)), float(obj.get("y", sh / 2))
        if not obj.get("visible", True):
            continue
        if obj.get("type") == "text":
            size = float(obj.get("font_size", 64))
            painter.setPen(color)
            f = QFont(font)
            f.setPointSizeF(max(4.0, size * scale))
            painter.setFont(f)
            painter.drawText(QRectF(0, 0, width, height),
                             Qt.AlignmentFlag.AlignHCenter
                             | Qt.AlignmentFlag.AlignVCenter,
                             str(obj.get("text", "")))
            painter.setFont(font)
            continue
        w = float(obj.get("width", 240) if obj.get("type") == "rect"
                  else obj.get("radius", 120) * 2)
        h = float(obj.get("height", 140) if obj.get("type") == "rect"
                  else obj.get("radius", 120) * 2)
        box = QRectF((x - w / 2) * scale, (y - h / 2) * scale,
                     w * scale, h * scale)
        painter.setPen(QPen(color.darker(140), 2))
        painter.setBrush(color)
        if obj.get("type") == "rect":
            painter.drawRect(box)
        else:
            painter.drawEllipse(box)
    # Stage frame line keeps thumbnails looking like the real viewport.
    painter.setPen(QPen(QColor(BORDER), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(QRectF(0.5, 0.5, width - 1, height - 1))
    painter.end()
    return QPixmap.fromImage(image)


def _cache_dir() -> Path:
    import os
    base = Path(os.environ.get("APPDATA", Path.home())) / "movexa" / "thumbs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def cached_thumbnail(directory: str, width: int = THUMB_W) -> QPixmap | None:
    """Render + cache a thumbnail keyed by path and project.json mtime.

    Returns None when the project cannot be read; callers fall back to a
    placeholder. Cache lives in user storage and never in project files.
    """
    project_path = Path(directory) / "project.json"
    if not project_path.exists():
        return None
    try:
        stamp = int(project_path.stat().st_mtime)
        data = json.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    key = hashlib.sha1(
        f"{Path(directory).resolve()}|{stamp}|{width}".encode()).hexdigest()[:16]
    cache_file = _cache_dir() / f"{key}.png"
    if cache_file.exists():
        pixmap = QPixmap(str(cache_file))
        if not pixmap.isNull():
            return pixmap
    pixmap = render_project_pixmap(data, width)
    if pixmap is not None:
        pixmap.save(str(cache_file), "PNG")
    return pixmap
