"""Branding helpers: render the SVG logo into a QPixmap at any size.

The SVG is the single source of logo truth for the GUI (docs use it too);
QSvgRenderer ships inside the PySide6 wheel, so no extra dependency.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = _ROOT / "resources" / "branding" / "logo.svg"


def svg_pixmap(size: int, path: Path | None = None) -> QPixmap:
    renderer = QSvgRenderer(str(path or SVG_PATH))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap
