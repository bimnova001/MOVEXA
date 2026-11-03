"""Project workspace: asset browser, stage canvas, scene strip, properties.

The canvas paints directly from project data through the scene graph, so the
preview and (later) the frame renderer share one evaluation path. Selection
and drag-editing go through AppController, which broadcasts the changes.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.controller import AppController
from engine.scene_graph import world_transform_with_snapshots
from engine.tracks import camera_state, object_snapshot
from engine.transitions import transition_plan
from project.schema import AssetInfo, Project, SceneObject

log = logging.getLogger(__name__)

# Default stage sizes for procedural shapes (project units / px at scale 1).
DEFAULT_SHAPE_SIZES = {"rect": (240, 160), "ellipse": (180, 180)}
TEXT_FONT_POINT = 64


def _object_size(obj: SceneObject, asset: AssetInfo | None) -> tuple[float, float]:
    """Stage-unit size of an object used for drawing and hit-testing."""
    if obj.type == "image":
        return (float(asset.width or 300), float(asset.height or 300))
    if obj.type in DEFAULT_SHAPE_SIZES:
        return DEFAULT_SHAPE_SIZES[obj.type]
    return (TEXT_FONT_POINT * 8, TEXT_FONT_POINT * 1.6)  # conservative text box


class CanvasWidget(QWidget):
    """Stage preview of the current scene with click-select and drag-move.

    Coordinates: object x/y are stage centers; the stage is letterboxed into
    the widget preserving aspect ratio.
    """

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._pixmaps: dict[tuple[str, int, int], QPixmap] = {}
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._drag: tuple[str, float, float] | None = None  # (obj id, grab dx, grab dy)
        bus = controller.bus
        for event in ("scene.updated", "scene.selected", "scene.created",
                      "scene.removed", "project.opened", "project.created",
                      "timeline.frame"):
            bus.subscribe(event, lambda _data: self.update())

    def _stage_size(self) -> tuple[float, float]:
        project = self.controller.project
        if project is None:
            return 1920.0, 1080.0
        return float(project.settings.width), float(project.settings.height)

    def _view_params(self) -> tuple[float, float, float]:
        """Return (scale, offset_x, offset_y) mapping stage->widget pixels."""
        sw, sh = self._stage_size()
        scale = min((self.width() - 2) / sw, (self.height() - 2) / sh)
        return scale, (self.width() - sw * scale) / 2, (self.height() - sh * scale) / 2

    def _to_stage(self, pos: QPointF) -> tuple[float, float]:
        scale, ox, oy = self._view_params()
        return (pos.x() - ox) / scale, (pos.y() - oy) / scale

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        scale, ox, oy = self._view_params()
        painter.translate(ox, oy)
        painter.scale(scale, scale)

        project = self.controller.project
        scene = None
        if project is not None and self.controller.current_scene_id:
            scene = project.scene_by_id(self.controller.current_scene_id)
        if project is None or scene is None:
            self._paint_empty(painter)
            return

        sw, sh = self._stage_size()
        frame = self.controller.player.frame
        # Transition passes are painted bottom-up; the black/white dip
        # overlay goes between the outgoing and incoming scenes.
        plan = transition_plan(project, scene, frame)
        for index, pas in enumerate(plan.passes):
            if pas.alpha <= 0.0:
                continue
            painter.save()
            self._paint_scene_pass(painter, project, pas.scene,
                                   pas.frame, pas.alpha, sw, sh)
            painter.restore()
            if index == 0 and plan.black_overlay > 0.0:
                dip_color = "#ffffff" if scene.transition == "dip_white" else "#000000"
                painter.setOpacity(plan.black_overlay)
                painter.fillRect(QRectF(0, 0, sw, sh), QColor(dip_color))
                painter.setOpacity(1.0)

        # Selection is a UI affordance: only meaningful for the scene the
        # user is editing, never for transition ghost passes.
        graph = _graph_map(self.controller, scene.id)
        snapshots = {o.id: object_snapshot(o, frame) for o in scene.objects}
        self._paint_selection(painter, scene, graph, snapshots)

    def _paint_scene_pass(
        self, painter: QPainter, project: Project, scene, frame: int,
        alpha: float, sw: float, sh: float,
    ) -> None:
        """One full scene render at an alpha level (camera, bg, objects)."""
        camera = camera_state(scene, frame, sw, sh)
        # View center at (camera.x, camera.y), zoom about that point, applied
        # after the letterbox so the stage frame stays fixed in the widget.
        if camera.x != sw / 2 or camera.y != sh / 2 or camera.zoom != 1.0:
            painter.translate(sw / 2, sh / 2)
            painter.scale(1.0 / camera.zoom, 1.0 / camera.zoom)
            painter.translate(-camera.x, -camera.y)

        painter.setOpacity(alpha)
        painter.fillRect(QRectF(0, 0, sw, sh), QColor(scene.background_color))
        self._paint_background_asset(painter, scene.background_asset_id,
                                     sw, sh, alpha)

        frame_snapshots = {
            obj.id: object_snapshot(obj, frame) for obj in scene.objects
        }
        # Paint in scene.objects order (authoritative paint order per schema).
        graph = _graph_map(self.controller, scene.id)
        for obj in scene.objects:
            snap = frame_snapshots[obj.id]
            if not snap.visible:
                continue
            node = graph.get(obj.id)
            world = world_transform_with_snapshots(node, frame_snapshots)
            painter.save()
            painter.translate(world.x, world.y)
            painter.rotate(world.rotation)
            painter.scale(world.scale_x, world.scale_y)
            self._paint_object(painter, obj, alpha)
            painter.restore()

    def _paint_empty(self, painter: QPainter) -> None:
        sw, sh = self._stage_size()
        painter.fillRect(QRectF(0, 0, sw, sh), QColor("#141420"))
        painter.setPen(QPen(QColor("#9a9ab8")))
        painter.drawText(QRectF(0, 0, sw, sh), Qt.AlignmentFlag.AlignCenter,
                         "Create or open a project to start")

    def _paint_background_asset(self, painter: QPainter,
                                asset_id: str | None, sw: float, sh: float,
                                alpha: float = 1.0) -> None:
        if not asset_id:
            return
        pixmap = self._pixmap_for(asset_id)
        if pixmap is None:
            return  # missing file: background color remains visible
        # Cover-fit (crop, never distort): backgrounds must always fill the
        # stage regardless of source aspect ratio.
        scale = max(sw / pixmap.width(), sh / pixmap.height())
        dw, dh = pixmap.width() * scale, pixmap.height() * scale
        painter.setOpacity(alpha)
        painter.drawPixmap(
            QRectF((sw - dw) / 2, (sh - dh) / 2, dw, dh), pixmap,
            QRectF(0, 0, pixmap.width(), pixmap.height()))

    def _pixmap_for(self, asset_id: str) -> QPixmap | None:
        project = self.controller.project
        if project is None or self.controller.manager.current_dir is None:
            return None
        asset = project.asset_by_id(asset_id)
        if asset is None:
            return None
        path = self.controller.asset_manager.absolute_path(asset)
        try:
            stat = path.stat()
            key = (asset_id, stat.st_size, stat.st_mtime_ns)
        except OSError:
            return None
        pixmap = self._pixmaps.get(key)
        if pixmap is None:
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                return None
            self._pixmaps[key] = pixmap
        return pixmap

    def _paint_object(self, painter: QPainter, obj: SceneObject,
                      pass_alpha: float = 1.0) -> None:
        project = self.controller.project
        asset = project.asset_by_id(obj.asset_id) if (project and obj.asset_id) else None

        # Object opacity multiplies the transition pass alpha so ghost
        # passes render correctly over the incoming scene.
        painter.setOpacity(max(0.0, min(1.0, obj.opacity * pass_alpha)))
        if obj.type == "image":
            if asset is None:
                self._paint_missing(painter)
                return
            pixmap = self._pixmap_for(asset.id)
            if pixmap is None:
                self._paint_missing(painter)
                return
            half_w, half_h = pixmap.width() / 2, pixmap.height() / 2
            painter.drawPixmap(QPointF(-half_w, -half_h), pixmap)
            return

        w, h = _object_size(obj, asset)
        rect = QRectF(-w / 2, -h / 2, w, h)
        if obj.type == "ellipse":
            painter.setPen(QPen(QColor("#0a0a14"), 2))
            painter.setBrush(QColor(obj.color))
            painter.drawEllipse(rect)
        elif obj.type == "text":
            font = QFont()
            font.setPointSize(TEXT_FONT_POINT)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(obj.color))
            if obj.text:
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, obj.text)
            else:
                painter.setPen(QPen(QColor("#9a9ab8"), 2, Qt.PenStyle.DashLine))
                painter.drawRect(rect)
        else:  # rect
            painter.setPen(QPen(QColor("#0a0a14"), 2))
            painter.setBrush(QColor(obj.color))
            painter.drawRect(rect)

    def _paint_missing(self, painter: QPainter) -> None:
        # Asset file vanished after import: report loudly instead of silently
        # skipping (architecture doc 15 - avoid silent failures).
        w, h = 260, 120
        rect = QRectF(-w / 2, -h / 2, w, h)
        pen = QPen(QColor("#f43f5e"), 3, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QColor(30, 10, 16, 160))
        painter.drawRect(rect)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "missing asset")

    def _paint_selection(self, painter: QPainter, scene, graph, snapshots) -> None:
        obj_id = self.controller.selected_object_id
        if not obj_id:
            return
        obj = scene.object_by_id(obj_id)
        if obj is None or not obj.visible:
            return
        node = graph.get(obj_id)
        world = world_transform_with_snapshots(node, snapshots)
        asset = self.controller.project.asset_by_id(obj.asset_id) if obj.asset_id else None
        w, h = _object_size(obj, asset)
        painter.save()
        painter.translate(world.x, world.y)
        painter.rotate(world.rotation)
        # Selection must not inherit object scale/opacity: the outline is a
        # UI affordance drawn with stage metrics, not part of the artwork.
        painter.scale(world.scale_x, world.scale_y)
        painter.setOpacity(1.0)
        painter.setPen(QPen(QColor("#22d3ee"), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(-w / 2 - 6, -h / 2 - 6, w + 12, h + 12))
        painter.restore()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        scene = self._current_scene()
        if scene is None:
            return
        sx, sy = self._to_stage(event.position())
        hit = self._hit_test(scene, sx, sy)
        if hit is None:
            if self.controller.selected_object_id is not None:
                self.controller.select_object(scene.id, None)
            return
        self.controller.select_object(scene.id, hit.id)
        world_x, world_y = self._worldxy(hit)
        self._drag = (hit.id, sx - world_x, sy - world_y)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag is None:
            return
        scene = self._current_scene()
        if scene is None:
            return
        obj_id, grab_dx, grab_dy = self._drag
        obj = scene.object_by_id(obj_id)
        if obj is None:
            return
        sx, sy = self._to_stage(event.position())
        # Rapid moves must keep the grab offset even if an intermediate event
        # is dropped - controller round-trips only x/y, nothing else moves.
        self.controller.update_object(scene.id, obj_id, x=sx - grab_dx, y=sy - grab_dy)

    def mouseReleaseEvent(self, _event) -> None:  # noqa: N802
        self._drag = None

    def _current_scene(self):
        project = self.controller.project
        if project is None or self.controller.current_scene_id is None:
            return None
        return project.scene_by_id(self.controller.current_scene_id)

    def _worldxy(self, obj: SceneObject) -> tuple[float, float]:
        scene = self._current_scene()
        if scene is None:
            return obj.x, obj.y
        frame = self.controller.player.frame
        node = _graph_map(self.controller, scene.id).get(obj.id)
        world = world_transform_with_snapshots(
            node, {o.id: object_snapshot(o, frame) for o in scene.objects})
        return world.x, world.y

    def _hit_test(self, scene, sx: float, sy: float):
        """Topmost object under a stage point (rotation ignored for MVP)."""
        frame = self.controller.player.frame
        graph = _graph_map(self.controller, scene.id)
        snapshots = {o.id: object_snapshot(o, frame) for o in scene.objects}
        project = self.controller.project
        for obj in reversed(scene.objects):
            snap = snapshots[obj.id]
            if not snap.visible:
                continue
            world = world_transform_with_snapshots(graph.get(obj.id), snapshots)
            asset = project.asset_by_id(obj.asset_id) if (project and obj.asset_id) else None
            w, h = _object_size(obj, asset)
            if abs(sx - world.x) <= w / 2 and abs(sy - world.y) <= h / 2:
                return obj
        return None


def _graph_map(controller: AppController, scene_id: str) -> dict[str, Any]:
    """object id -> SceneNode, or {} when the graph cannot be built."""
    try:
        roots = controller.scene_graph(scene_id)
    except ValueError as exc:
        log.warning("scene graph unusable: %s", exc)
        return {}
    return {node.object.id: node
            for root in roots for node in root.iterate()}
