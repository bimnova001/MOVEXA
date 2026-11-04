"""Real timeline: tick ruler, scene blocks, draggable playhead AND clips.

Replaces the scene tab strip with the editing-suite convention users expect:
time moves horizontally, clips occupy proportional widths, clicking the
ruler scrubs, dragging a clip's right edge resizes its scene duration, and
dragging a clip body reorders the sequence. Data comes only from the
controller; every mutation goes through undoable controller methods.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

BLOCK_COLORS = ("#8b5cf6", "#22d3ee", "#c53ef5", "#f59e0b", "#10b981")
RULER_BG = "#17171e"
TRACK_BG = "#1b1b23"
PLAYHEAD = "#f43f5e"

EDGE_TOLERANCE = 6.0
MIN_DURATION = 1
MAX_DURATION = 360000


# -- pure geometry math (unit-tested headlessly, no Qt) ----------------------

def edge_hit(edges: list[tuple[float, float]], x: float,
             tolerance: float = EDGE_TOLERANCE) -> int | None:
    """Index of the clip whose right edge sits within tolerance of x."""
    for index, (x0, x1) in enumerate(edges):
        if x1 - x0 > 12.0 and abs(x - x1) <= tolerance:
            return index
    return None


def block_hit(edges: list[tuple[float, float]], x: float) -> int | None:
    """Index of the clip covering x."""
    for index, (x0, x1) in enumerate(edges):
        if x0 <= x < x1:
            return index
    return None


def resize_duration(orig: int, dx_px: float, total_frames: int, track_px: float,
                    minimum: int = MIN_DURATION,
                    maximum: int = MAX_DURATION) -> int:
    """Scene duration after dragging its edge by dx_px on screen."""
    if total_frames <= 0 or track_px <= 0:
        return orig
    delta = dx_px * total_frames / track_px
    return int(min(maximum, max(minimum, round(orig + delta))))


class TimelineWidget(QWidget):
    """Horizontal sequence view: ruler + scene blocks + drag handles."""

    RULER_H = 26
    BLOCK_H = 30
    LABEL_W = 76

    def __init__(self, controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._mode: str | None = None  # "scrub" | "resize" | "reorder"
        self._press_x = 0.0
        self._resize_index = -1
        self._resize_preview: int | None = None
        self._drag_index = -1
        self._order_preview: list[int] | None = None
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

    def _ordered(self) -> list:
        """Scenes in paint order, honoring an active reorder preview."""
        scenes = self._scenes()
        if self._mode == "reorder" and self._order_preview is not None:
            return [scenes[i] for i in self._order_preview]
        return scenes

    def _paint_pairs(self) -> list[tuple]:
        """(scene, duration) pairs with any active resize preview applied."""
        pairs = [(scene, scene.duration_frames) for scene in self._ordered()]
        if self._mode == "resize" and self._resize_preview is not None:
            dragged = self._scenes()[self._resize_index]
            for index, (scene, duration) in enumerate(pairs):
                if scene.id == dragged.id:
                    pairs[index] = (scene, self._resize_preview)
                    break
        return pairs

    def _total(self) -> int:
        return max(1, sum(duration for _scene, duration in self._paint_pairs()))

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

    def _edges_for(self, pairs: list[tuple]) -> list[tuple[float, float]]:
        rect = self._track_rect()
        total = max(1, sum(duration for _scene, duration in pairs))
        edges: list[tuple[float, float]] = []
        elapsed = 0
        for _scene, duration in pairs:
            x0 = rect.left() + rect.width() * elapsed / total
            elapsed += duration
            edges.append((x0, rect.left() + rect.width() * elapsed / total))
        return edges

    def _clip_edges(self) -> list[tuple[float, float]]:
        return self._edges_for(self._paint_pairs())

    # -- painting ------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(RULER_BG))

        pairs = self._paint_pairs()
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
        painter.setFont(QFont("Segoe UI", 7))
        elapsed = 0
        for _scene, duration in pairs:
            x = self._frame_to_x(elapsed)
            painter.setPen(QPen(QColor("#3a3a4a")))
            painter.drawLine(int(x), 0, int(x), self.height())
            seconds = elapsed / fps
            painter.setPen(QPen(QColor("#8f8fa8")))
            painter.drawText(int(x) + 4, self.RULER_H - 9,
                             f"{int(seconds // 60):02d}:{int(seconds % 60):02d}")
            elapsed += duration

        # end cap
        x_end = self._frame_to_x(total)
        painter.setPen(QPen(QColor("#3a3a4a")))
        painter.drawLine(int(x_end), 0, int(x_end), self.height())
        seconds = total / fps
        painter.setPen(QPen(QColor("#8f8fa8")))
        painter.drawText(min(int(x_end) + 4, self.width() - 44), self.RULER_H - 9,
                         f"{int(seconds // 60):02d}:{int(seconds % 60):02d}")

        # -- scene blocks proportional to duration ---------------------
        elapsed = 0
        for index, (scene, duration) in enumerate(pairs):
            x0 = self._frame_to_x(elapsed)
            x1 = self._frame_to_x(elapsed + duration)
            elapsed += duration
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
            # resize grip: brighter strip on the trailing edge
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 45))
            grip = QRectF(block.right() - 3, block.top() + 4, 2,
                          block.height() - 8)
            painter.drawRect(grip)

        # -- playhead ---------------------------------------------------
        head_x = self._frame_to_x(self._head_frame())
        painter.setPen(QPen(QColor(PLAYHEAD), 2))
        painter.drawLine(int(head_x), 0, int(head_x), self.height())

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
        x = event.position().x()
        edges = self._clip_edges()
        edge = edge_hit(edges, x)
        if edge is not None:
            self._mode = "resize"
            self._resize_index = edge
            self._resize_preview = None
            self._press_x = x
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            return
        block = block_hit(edges, x)
        if block is not None:
            scene = self._ordered()[block]
            if scene.id != self.controller.current_scene_id:
                self.controller.select_scene(scene.id)
            self._mode = "reorder"
            self._drag_index = next(
                i for i, s in enumerate(self._scenes()) if s.id == scene.id)
            self._order_preview = None
            self._press_x = x
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        self._mode = "scrub"
        self.setCursor(Qt.CursorShape.SplitHCursor)
        self._seek_to(x)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        x = event.position().x()
        if self._mode == "resize":
            scenes = self._scenes()
            if 0 <= self._resize_index < len(scenes):
                original = scenes[self._resize_index].duration_frames
                duration = resize_duration(
                    original, x - self._press_x, self._total(),
                    self._track_rect().width())
                if duration != self._resize_preview:
                    self._resize_preview = duration
                    self.update()
        elif self._mode == "reorder":
            order = self._preview_order(x)
            if order != self._order_preview:
                self._order_preview = order
                self.update()
        elif self._mode == "scrub":
            self._seek_to(x)
        else:
            hover = edge_hit(self._clip_edges(), x)
            self.setCursor(Qt.CursorShape.SizeHorCursor if hover is not None
                           else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, _event) -> None:  # noqa: N802 - Qt naming
        mode, self._mode = self._mode, None
        self._press_x = 0.0
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if mode == "resize" and self._resize_preview is not None:
            preview, self._resize_preview = self._resize_preview, None
            scenes = self._scenes()
            if 0 <= self._resize_index < len(scenes):
                scene = scenes[self._resize_index]
                if scene.duration_frames != preview:
                    self.controller.update_scene_metadata(
                        scene.id, duration_frames=preview)
        elif mode == "reorder" and self._order_preview is not None:
            order, self._order_preview = self._order_preview, None
            delta = order.index(self._drag_index) - self._drag_index
            if delta:
                self.controller.reorder_scene(
                    self._scenes()[self._drag_index].id, delta)
        self._resize_index = -1
        self._drag_index = -1
        self.update()

    def _preview_order(self, x: float) -> list[int] | None:
        """Scene indices with the dragged clip re-slotted at x, or None."""
        count = len(self._scenes())
        if count < 2:
            return None
        edges = self._edges_for([(s, s.duration_frames) for s in self._scenes()])
        mids = [(x0 + x1) / 2 for x0, x1 in edges]
        dragged = self._drag_index
        others = [i for i in range(count) if i != dragged]
        slot = sum(1 for i in others if mids[i] < x)
        order = others[:slot] + [dragged] + others[slot:]
        return None if order == list(range(count)) else order

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
