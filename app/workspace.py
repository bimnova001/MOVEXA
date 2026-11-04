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

        bar = QHBoxLayout(self.toolbar)
        bar.setContentsMargins(10, 8, 10, 8)
        bar.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(svg_pixmap(24))
        bar.addWidget(logo)
        bar.addWidget(home_btn)
        bar.addSpacing(4)
        bar.addWidget(self.project_label)
        bar.addStretch(1)
        bar.addWidget(add_shape_btn)
        bar.addWidget(add_text_btn)
        bar.addWidget(add_rig_btn)
        bar.addSpacing(4)
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
        rail_widget.setFixedWidth(48)

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
        self.left_dock.setMinimumWidth(220)
        self.left_dock.setMaximumWidth(440)
        self.properties.setMinimumWidth(230)
        self.properties.setMaximumWidth(340)
        splitter.addWidget(left_dock_widget)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.properties_scroll)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(splitter, 1)
        # Timeline row under the viewport, then transport: editor convention.
        layout.addWidget(self.scene_strip)
        layout.addWidget(self.transport)

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