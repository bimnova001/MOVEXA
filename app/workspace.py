"""Workspace assembly: asset browser | canvas | properties, strip + transport.

The main window switches between DashboardScreen and this page depending on
whether a project is open.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QComboBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.canvas import CanvasWidget
from app.controller import AppController
from app.panels import AssetBrowser, PropertiesPanel, SceneStrip


class TransportBar(QWidget):
    """Play/pause/stop/step + seek slider bound to the playback controller."""

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        self.play_btn = QPushButton("\u25B6 Play")
        self.play_btn.setFixedWidth(84)
        self.play_btn.clicked.connect(self._toggle_play)

        self.stop_btn = QPushButton("\u23F9 Stop")
        self.stop_btn.setFixedWidth(76)
        self.stop_btn.clicked.connect(self._stop)

        self.back_btn = QPushButton("<")
        self.back_btn.setFixedWidth(30)
        self.back_btn.setToolTip("Step one frame back")
        self.back_btn.clicked.connect(lambda: controller.player.step(-1))

        self.fwd_btn = QPushButton(">")
        self.fwd_btn.setFixedWidth(30)
        self.fwd_btn.setToolTip("Step one frame forward")
        self.fwd_btn.clicked.connect(lambda: controller.player.step(1))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self._slider_moved)

        self.speed = QComboBox()
        for label, value in (("0.5x", 0.5), ("1.0x", 1.0), ("2.0x", 2.0)):
            self.speed.addItem(label, value)
            self.speed.setCurrentIndex(1)
        self.speed.currentIndexChanged.connect(self._speed_changed)

        self.frame_label = QLabel("f 0 / 0")
        self.frame_label.setMinimumWidth(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self.play_btn, self.stop_btn, self.back_btn,
                       self.fwd_btn, self.slider, self.speed, self.frame_label):
            layout.addWidget(widget)
        layout.setStretch(4, 1)

        for event in ("timeline.frame", "scene.selected", "scene.updated",
                      "scene.created", "scene.removed",
                      "project.opened", "project.created"):
            controller.bus.subscribe(event, lambda _data: self._refresh())

    def _toggle_play(self) -> None:
        if self.controller.player.toggle():
            self.play_btn.setText("\u23F8 Pause")
        else:
            self.play_btn.setText("\u25B6 Play")
        self._publish_frame()

    def _stop(self) -> None:
        self.controller.player.stop()
        self.play_btn.setText("\u25B6 Play")
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
        self.frame_label.setText(f"f {player.frame} / {player.duration - 1}")


class WorkspaceScreen(QWidget):

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        self.canvas = CanvasWidget(controller)
        self.canvas_block = _CanvasFrame(self.canvas)

        self.asset_browser = AssetBrowser(controller)
        self.properties = PropertiesPanel(controller)
        self.properties_scroll = QScrollArea()
        self.properties_scroll.setWidgetResizable(True)
        self.properties_scroll.setWidget(self.properties)
        self.transport = TransportBar(controller)

        add_text_btn = QPushButton("Add text")
        add_text_btn.clicked.connect(self._add_text)
        add_rect_btn = QPushButton("Add shape")
        add_rect_btn.clicked.connect(self._add_shape)
        add_rig_btn = QPushButton("Add character rig")
        add_rig_btn.clicked.connect(self._add_rig)
        export_btn = QPushButton("Export MP4")
        export_btn.clicked.connect(self._export_mp4)

        buttons = QHBoxLayout()
        buttons.addWidget(add_text_btn)
        buttons.addWidget(add_rect_btn)
        buttons.addWidget(add_rig_btn)
        buttons.addWidget(export_btn)
        buttons.addStretch(1)

        self.scene_strip = SceneStrip(controller)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.asset_browser.setMinimumWidth(180)
        self.asset_browser.setMaximumWidth(320)
        self.properties.setMinimumWidth(220)
        self.properties.setMaximumWidth(340)
        splitter.addWidget(self.asset_browser)
        splitter.addWidget(self.canvas_block)
        splitter.addWidget(self.properties_scroll)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.scene_strip)
        layout.addLayout(buttons)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.transport)

        # Preview clock. 30 Hz ticks are cheap; the player converts wall time
        # to fractional frames, so timer jitter does not cause drift.
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def _on_tick(self) -> None:
        if self.controller.player.tick():
            self.controller.bus.publish(
                "timeline.frame", {"frame": self.controller.player.frame})

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

    def _export_mp4(self) -> None:
        if self.controller.project is None:
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(
            self, "Export MP4", "export.mp4", "MP4 Video (*.mp4)")
        if not path:
            return
        try:
            self.controller.export_video(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Export complete", f"Saved to {path}")


class _CanvasFrame(QWidget):

    def __init__(self, canvas: CanvasWidget) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(canvas)
