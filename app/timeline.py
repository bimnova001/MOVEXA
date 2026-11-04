"""Real timeline: tick ruler, scene blocks, draggable playhead.

Replaces the scene tab strip with the editing-suite convention users expect:
time moves horizontally, clips occupy proportional widths, clicking the
ruler scrubs. Data comes only from the controller; playback stays drivable
by the existing transport.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

BLOCK_COLORS = ("#8b5cf6", "#22d3ee", "#c53ef5", "#f59e0b", "#10b981")
RULER_BG = "#17171e"
TRACK_BG = "#1b1b23"
PLAYHEAD = "#f43f5e"


class TimelineWidget(QWidget):
    """Horizontal sequence view: ruler + scene blocks + playhead."""

    RULER_H = 26
    BLOCK_H = 30
    LABEL_W = 76

    def __init__(self, controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._scrubbing = False
        self.setMinimumHeight(64)
        self.setMouseTracking(True)
        for event in ("timeline.frame", "scene.updated", "scene.created",
                      "scene.removed", "scene.reordered", "scene.selected",
                      "project.opened", "project.created"):
            controller.bus.subscribe(event, lambda _d: self.update())

    # -- data ----------------------------------------------------------------

    def _scenes(self) -> list:
        project = self.controller.project
        return list(project.scenes) if project else []

    def _total(self) -> int:
        return max(1, sum(s.duration_frames for s in self._scenes()))

    def _track_rect(self) -> QRectF:
        width = max(1.0, self.width() - self.LABEL_W)
        return QRectF(self.LABEL_W, self.RULER_H, width,
                      max(self.BLOCK_H, self.height() - self.RULER_H - 4))

    def _frame_to_x(self, frame: int) -> float:
        rect = self._track_rect()
        return rect.left() + rect.width() * frame / self._total()

    def _x_to_frame(self, x: float) -> int:
        rect = self._track_rect()
        ratio = (x - rect.left()) / max(1.0, rect.width())
        return max(0, min(self._total() - 1, int(ratio * self._total())))

    # -- painting ------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(RULER_BG))

        scenes = self._scenes()
        total = self._total()
        track = self._track_rect()
        fps = getattr(self.controller.player, "fps", 30)

        # -- lane label + track bed -----------------------------------
        painter.setPen(QPen(QColor("#8f8fa8")))
        painter.drawText(QRectF(0, track.top(), self.LABEL_W - 8, track.height()),
                         Qt.AlignmentFlag.AlignCenter, "Scenes")
        painter.fillRect(track, QColor(TRACK_BG))
        painter.setPen(QPen(QColor("#2a2a36")))
        painter.drawRect(track.adjusted(0, 0, -1, -1))

        # -- ruler: cut lines + mm:ss labels at scene starts -----------
        elapsed = 0
        for scene in scenes:
            x = self._frame_to_x(elapsed)
            painter.setPen(QPen(QColor("#3a3a4a")))
            painter.drawLine(int(x), 0, int(x), self.height())
            seconds = elapsed / fps
            painter.setPen(QColor("#8f8fa8"))
            painter.drawText(int(x) + 4, self.RULER_H - 9,
                             f"{int(seconds // 60):02d}:{int(seconds % 60):02d}")
            elapsed += scene.duration_frames

        # end cap
        x_end = self._frame_to_x(total)
        painter.setPen(QPen(QColor("#3a3a4a")))
        painter.drawLine(int(x_end), 0, int(x_end), self.height())
        seconds = total / fps
        painter.setPen(QColor("#8f8fa8"))
        painter.drawText(min(int(x_end) + 4, self.width() - 44), self.RULER_H - 9,
                         f"{int(seconds // 60):02d}:{int(seconds % 60):02d}")

        # -- scene blocks proportional to duration ---------------------
        elapsed = 0
        for index, scene in enumerate(scenes):
            x0 = self._frame_to_x(elapsed)
            x1 = self._frame_to_x(elapsed + scene.duration_frames)
            elapsed += scene.duration_frames
            block = QRectF(x0 + 1, track.top() + 1,
                           max(8.0, x1 - x0 - 2), track.height() - 2)
            color = QColor(BLOCK_COLORS[index % len(BLOCK_COLORS)])
            if scene.id == self.controller.current_scene_id:
                color = color.lighter(150)
            painter.setPen(QPen(color.darker(160)))
            painter.setBrush(color)
            painter.drawRoundedRect(block, 4, 4)
            painter.setPen(QColor("#0a0a14" if color.lightness() > 120 else "#ffffff"))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(block.adjusted(4, 0, -4, 0),
                             Qt.AlignmentFlag.AlignVCenter, scene.name)

        # -- playhead ---------------------------------------------------
        head_x = self._frame_to_x(self._head_frame())
        painter.setPen(QPen(QColor(PLAYHEAD), 2))
        painter.drawLine(int(head_x), 0, int(head_x), self.height())
        painter.setBrush(QColor(PLAYHEAD))
        painter.drawPolygon(
            [QRectF(head_x - 5, 0, 10, 8).topLeft(),
             QRectF(head_x - 5, 0, 10, 8).topRight(),
             QRectF(head_x, 8, 1, 1).topLeft()], Qt.FillRule.OddEvenFill)

    def _head_frame(self) -> int:
        """Local player frame expressed in global-sequence frames."""
        scenes = self._scenes()
        elapsed = 0
        for scene in scenes:
            if scene.id == self.controller.current_scene_id:
                return elapsed + self.controller.player.frame
            elapsed += scene.duration_frames
        return 0

    # -- interaction ---------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._scrubbing = True
        self._seek_to(event.position().x())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._scrubbing:
            self._seek_to(event.position().x())

    def mouseReleaseEvent(self, _event) -> None:  # noqa: N802 - Qt naming
        self._scrubbing = False

    def _seek_to(self, x: float) -> None:
        """Scrub across the whole sequence; crossing a cut selects it."""
        scenes = self._scenes()
        if not scenes:
            return
        total = sum(s.duration_frames for s in scenes)
        frame = max(0, min(total - 1, self._x_to_frame(x)))
        elapsed = 0
        for scene in scenes:
            duration = scene.duration_frames
            if frame < elapsed + duration or scene is scenes[-1]:
                local = max(0, min(duration - 1, frame - elapsed))
                if scene.id != self.controller.current_scene_id:
                    self.controller.select_scene(scene.id)
                self.controller.player.seek(local)
                break
            elapsed += duration
        self.controller.bus.publish(
            "timeline.frame", {"frame": self.controller.player.frame})
