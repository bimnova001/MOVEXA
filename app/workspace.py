"""Workspace assembly: asset browser | canvas | properties, strip + transport.

Layout follows editing-suite conventions: actions grouped in a top bar,
tools docked left, properties right, transport pinned to the bottom edge.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.agent_panel import AgentPanel
from app.branding import svg_pixmap
from app.canvas import CanvasWidget
from app.controller import AppController
from app.panels import AssetBrowser, PropertiesPanel, SceneStrip


class TransportBar(QFrame):
    """Play/pause/stop/step + seek slider bound to the playback controller."""

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("transport")
        self.controller = controller

        def icon_button(text: str, tip: str) -> QPushButton:
            button = QPushButton(text)
            button.setObjectName("transportBtn")
            button.setFixedSize(34, 30)
            button.setToolTip(tip)
            return button

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("transportPlay")
        self.play_btn.setFixedSize(44, 30)
        self.play_btn.setToolTip("Play / Pause (Space)")
        self.play_btn.clicked.connect(self._toggle_play)

        self.stop_btn = icon_button("■", "Stop")
        self.stop_btn.clicked.connect(self._stop)

        self.back_btn = icon_button("‹", "Step one frame back")
        self.back_btn.clicked.connect(lambda: controller.player.step(-1))

        self.fwd_btn = icon_button("›", "Step one frame forward")
        self.fwd_btn.clicked.connect(lambda: controller.player.step(1))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("timeline")
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self._slider_moved)

        self.speed = QComboBox()
        for label, value in (("0.5×", 0.5), ("1.0×", 1.0), ("2.0×", 2.0)):
            self.speed.addItem(label, value)
            self.speed.setCurrentIndex(1)
        self.speed.currentIndexChanged.connect(self._speed_changed)

        self.frame_label = QLabel("0 / 0")
        self.frame_label.setObjectName("frameCounter")
        self.frame_label.setMinimumWidth(84)
        self.frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        layout.addStretch(1)
        layout.addWidget(self.back_btn)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.fwd_btn)
        layout.addWidget(self.stop_btn)
        layout.addSpacing(8)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.frame_label)
        layout.addWidget(self.speed)
        layout.addStretch(1)

        for event in ("timeline.frame", "scene.selected", "scene.updated",
                      "scene.created", "scene.removed",
                      "project.opened", "project.created"):
            controller.bus.subscribe(event, lambda _data: self._refresh())

    def _toggle_play(self) -> None:
        if self.controller.player.toggle():
            self.play_btn.setText("⏸")
            self.play_btn.setToolTip("Pause")
        else:
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Play")
        self._publish_frame()

    def _stop(self) -> None:
        self.controller.player.stop()
        self.play_btn.setText("▶")
        self._publish_frame()

    def _slider_moved(self, value: int) -> None:
        self.controller.player.seek(value)
        self._publish_frame()

    def _speed_changed(self) -> None:
        self.controller.player.speed = float(self.speed.currentData())

    def _publish_frame(self) -> None:
        self.controller.bus.publish(
            "timeline.frame", {"frame": self.controller.player.frame})

    def _refresh(self) -> None:
        player = self.controller.player
        if self.slider.maximum() != player.duration - 1:
            self.slider.setRange(0, player.duration - 1)
        if self.slider.value() != player.frame and not self.slider.isSliderDown():
            self.slider.blockSignals(True)
            self.slider.setValue(player.frame)
            self.slider.blockSignals(False)
        self.frame_label.setText(f"{player.frame} / {player.duration - 1}")


class WorkspaceScreen(QWidget):

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        self.canvas = CanvasWidget(controller)
        self.toolbar = QFrame()
        self.toolbar.setObjectName("topbar")
        home_btn = QPushButton("⌂ Home")
        home_btn.setObjectName("topbarBtn")
        home_btn.setToolTip("Back to the project menu")
        home_btn.clicked.connect(lambda: self.controller.bus.publish(
            "dashboard.shown", {}))

        self.project_label = QLabel()
        self.project_label.setObjectName("topbarTitle")

        # Player header: zoom presets + overlay toggles + timecode.
        player_bar = QFrame()
        player_bar.setObjectName("playerBar")
        player_row = QHBoxLayout(player_bar)
        player_row.setContentsMargins(10, 5, 10, 5)
        player_title = QLabel("Player")
        player_title.setObjectName("panelHeader")

        self.zoom_combo = QComboBox()
        for label, factor in (("Fit", 1.0), ("50%", 0.5), ("100%", 1.0),
                              ("200%", 2.0)):
            self.zoom_combo.addItem(label, factor)
        self.zoom_combo.currentIndexChanged.connect(self._zoom_changed)
        self.zoom_combo.setToolTip("Zoom (mouse wheel zooms on the canvas; "
                                   "Alt-drag or middle-drag pans)")

        self.grid_btn = QPushButton("▦ Grid")
        self.grid_btn.setObjectName("topbarBtn")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setToolTip("Thirds grid overlay")
        self.grid_btn.toggled.connect(self.canvas.toggle_grid)

        self.safe_btn = QPushButton("□ Safe")
        self.safe_btn.setObjectName("topbarBtn")
        self.safe_btn.setCheckable(True)
        self.safe_btn.setToolTip("Title (90%) and action (80%) safe areas")
        self.safe_btn.toggled.connect(self.canvas.toggle_safe)

        self.timecode = QLabel("00:00 / 00:00")
        self.timecode.setObjectName("timecode")
        player_row.addWidget(player_title)
        player_row.addStretch(1)
        player_row.addWidget(self.grid_btn)
        player_row.addWidget(self.safe_btn)
        player_row.addWidget(self.zoom_combo)
        player_row.addWidget(self.timecode)

        center_column = QWidget()
        center_layout = QVBoxLayout(center_column)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(player_bar)
        center_layout.addWidget(self.canvas, 1)
        add_shape_btn = QPushButton("＋ Shape")
        add_shape_btn.setObjectName("topbarBtn")
        add_shape_btn.clicked.connect(self._add_shape)

        add_text_btn = QPushButton("＋ Text")
        add_text_btn.setObjectName("topbarBtn")
        add_text_btn.clicked.connect(self._add_text)

        add_rig_btn = QPushButton("＋ Character")
        add_rig_btn.setObjectName("topbarBtn")
        add_rig_btn.setToolTip("Add a cut-out character rig")
        add_rig_btn.clicked.connect(self._add_rig)

        export_btn = QPushButton("Export MP4")
        export_btn.setObjectName("primary")
        export_btn.clicked.connect(self._export_mp4)

        play_btn = QPushButton("▶")
        play_btn.setObjectName("topbarBtn")
        play_btn.setToolTip("Play / Pause (Space)")
        play_btn.clicked.connect(lambda: self.transport._toggle_play())

        def separator() -> QFrame:
            line = QFrame()
            line.setObjectName("toolbarSep")
            line.setFixedWidth(1)
            line.setFixedHeight(22)
            line.setStyleSheet(
                "QFrame#toolbarSep {{ background: {b}; }}".format(b="#3a3a46"))
            return line

        def group(tag: str) -> QLabel:
            label = QLabel(tag)
            label.setObjectName("topbarGroup")
            return label

        bar = QHBoxLayout(self.toolbar)
        bar.setContentsMargins(10, 6, 10, 6)
        bar.setSpacing(6)
        logo = QLabel()
        logo.setPixmap(svg_pixmap(20))
        bar.addWidget(logo)
        bar.addWidget(group("PROJECT"))
        bar.addWidget(home_btn)
        bar.addWidget(self.project_label)
        bar.addWidget(separator())
        bar.addWidget(group("OBJECTS"))
        bar.addWidget(add_shape_btn)
        bar.addWidget(add_text_btn)
        bar.addWidget(add_rig_btn)
        bar.addWidget(separator())
        bar.addWidget(group("PLAYBACK"))
        bar.addWidget(play_btn)
        bar.addStretch(1)
        bar.addWidget(separator())
        bar.addWidget(group("EXPORT"))
        bar.addWidget(export_btn)

        self.asset_browser = AssetBrowser(controller)
        self.agent_panel = AgentPanel(controller)
        self.properties = PropertiesPanel(controller)
        self.properties_scroll = QScrollArea()
        self.properties_scroll.setWidgetResizable(True)
        self.properties_scroll.setWidget(self.properties)
        self.transport = TransportBar(controller)

        # Editor convention (CapCut/Resolve): an icon rail on the left swaps
        # the dock contents - media, AI agent and later tools share one slot.
        self._rail_actions: list[tuple] = [
            ("▦", "Assets"),
            ("✦", "AI Agent — script, scenes, shapes"),
        ]
        rail_widget = QWidget()
        rail_widget.setObjectName("rail")
        self.rail = QVBoxLayout(rail_widget)
        self.rail.setContentsMargins(4, 8, 4, 8)
        self.rail.setSpacing(6)
        self._rail_group = QButtonGroup(self)
        self.rail_buttons: list[QToolButton] = []
        for index, (glyph, tip) in enumerate(self._rail_actions):
            button = QToolButton()
            button.setText(glyph)
            button.setObjectName("railBtn")
            button.setFixedSize(40, 40)
            button.setToolTip(tip)
            button.setCheckable(True)
            button.clicked.connect(lambda _c=False, i=index: self._set_dock_index(i))
            self._rail_group.addButton(button)
            self.rail.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
            self.rail_buttons.append(button)
        self.rail.addStretch(1)
        rail_widget.setFixedWidth(52)

        self.left_dock = QStackedWidget()
        self.left_dock.addWidget(self.asset_browser)
        self.left_dock.addWidget(self.agent_panel)

        left_row = QHBoxLayout()
        left_row.setContentsMargins(0, 0, 0, 0)
        left_row.setSpacing(2)
        left_row.addWidget(rail_widget)
        left_row.addWidget(self.left_dock, 1)
        left_dock_widget = QWidget()
        left_dock_widget.setLayout(left_row)

        self.scene_strip = SceneStrip(controller)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_dock.setMinimumWidth(240)
        self.left_dock.setMaximumWidth(460)
        self.properties.setMinimumWidth(260)
        self.properties_scroll.setMaximumWidth(520)
        splitter.addWidget(left_dock_widget)
        splitter.addWidget(center_column)
        splitter.addWidget(self.properties_scroll)
        splitter.setStretchFactor(1, 1)
        # Review proportions for 1920x1080: assets ~270, inspector ~320.
        splitter.setSizes([270 + 52, 900, 320])

        # Bottom cluster (scene tools + timeline) sits in a vertical splitter
        # so users can hand more room to the timeline than the preview.
        bottom_cluster = QWidget()
        bottom_layout = QVBoxLayout(bottom_cluster)
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(0)
        bottom_layout.addWidget(self.scene_strip)
        from app.timeline import TimelineWidget
        self.timeline = TimelineWidget(controller)
        bottom_layout.addWidget(self.timeline)

        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.addWidget(splitter)
        vertical_splitter.addWidget(bottom_cluster)
        vertical_splitter.setStretchFactor(0, 1)
        vertical_splitter.setSizes([720, 130])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(vertical_splitter, 1)
        layout.addWidget(self.transport)

        # Timecode follows the playhead even while scrubbing the ruler.
        for event in ("timeline.frame", "scene.updated", "scene.selected",
                      "project.opened", "project.created"):
            controller.bus.subscribe(event, self._update_timecode)
        self._update_timecode({})

        # Preview clock. 30 Hz ticks are cheap; the player converts wall time
        # to fractional frames, so timer jitter does not cause drift.
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

        for event in ("project.opened", "project.created", "project.closed"):
            controller.bus.subscribe(event, self.refresh_project_label)
        self.refresh_project_label({})

        # Editing-suite muscle memory: Space plays/pauses, Delete removes
        # the selected object, Ctrl+D duplicates it. Widget-scope shortcuts
        # keep the bindings valid only while the editor page is on screen.
        QShortcut(QKeySequence(Qt.Key.Key_Space), self,
                  activated=self.transport._toggle_play)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self,
                  activated=self._delete_selection)

    def refresh_project_label(self, _data: dict | None = None) -> None:
        project = self.controller.project
        if project is None:
            self.project_label.setText("no project")
            return
        self.project_label.setText(
            f"{project.name}  ·  {project.settings.width}×{project.settings.height}"
            f"  ·  {project.settings.fps} fps")

    def _on_tick(self) -> None:
        if self.controller.player.tick():
            self.controller.bus.publish(
                "timeline.frame", {"frame": self.controller.player.frame})

    def _set_dock_index(self, index: int) -> None:
        self.left_dock.setCurrentIndex(index)
        for row, button in enumerate(self.rail_buttons):
            button.setChecked(row == index)

    def _zoom_changed(self) -> None:
        factor = self.zoom_combo.currentData()
        if factor is not None:
            self.canvas.set_zoom(float(factor))

    def _update_timecode(self, _data: dict | None = None) -> None:
        player = self.controller.player
        fps = max(1, player.fps)
        frame = getattr(player, "frame", 0)
        duration = max(1, getattr(player, "duration", 1))
        self.timecode.setText(
            f"{frame // fps:02d}:{frame % fps:02d} / "
            f"{duration // fps:02d}:{duration % fps:02d}")

    def _add_shape(self) -> None:
        if self.controller.current_scene_id is None:
            return
        project = self.controller.project
        self.controller.add_object(
            self.controller.current_scene_id, type="rect",
            x=project.settings.width / 2, y=project.settings.height / 2)

    def _add_text(self) -> None:
        if self.controller.current_scene_id is None:
            return
        project = self.controller.project
        self.controller.add_object(
            self.controller.current_scene_id, type="text",
            text="MOVEXA", color="#ffffff",
            x=project.settings.width / 2, y=project.settings.height / 2)

    def _add_rig(self) -> None:
        if self.controller.current_scene_id is None:
            return
        self.controller.create_character_rig(self.controller.current_scene_id)

    def _delete_selection(self) -> None:
        scene_id = self.controller.current_scene_id
        object_id = self.controller.selected_object_id
        if scene_id is None or object_id is None:
            return
        self.controller.remove_object(scene_id, object_id)

    def _export_mp4(self) -> None:
        if self.controller.project is None:
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export MP4", "export.mp4", "MP4 Video (*.mp4)")
        if not path:
            return
        total = sum(s.duration_frames for s in self.controller.project.scenes)
        progress = QProgressDialog("Exporting…", None, 0, total, self)
        progress.setWindowTitle("Export MP4")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def tick(done: int, of: int) -> None:
            progress.setMaximum(of)
            progress.setValue(done)

        try:
            self.controller.export_video(path, progress=tick)
        except Exception as exc:  # noqa: BLE001
            progress.cancel()
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        progress.setValue(progress.maximum())
        # Desktop pattern: success confirmations never steal focus.
        toast = getattr(self.window(), "toast", None)
        if toast is not None:
            toast.info(f"Export complete — saved to {path}")