"""Workspace side panels: asset browser, scene strip, object properties.

Panels stay thin: they read the model to repaint, and every edit goes through
AppController so other widgets stay in sync via the event bus.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.controller import AppController
from engine.actions import ACTIONS
from engine.tracks import camera_state, object_snapshot
from project.schema import SCENE_TRANSITIONS, SceneObject

# Display names for the action combo; rig-only actions carry a marker so the
# user understands why they fail on plain objects.
ACTION_LABELS: dict[str, str] = {
    "spin": "Spin 360",
    "fade_in": "Fade in",
    "fade_out": "Fade out",
    "bob": "Bob",
    "idle": "Idle (rig)",
    "walk": "Walk (rig)",
    "wave": "Wave (rig)",
    "jump": "Jump (rig)",
}

_RIG_ONLY_ACTIONS = {name for name, needs_rig in ACTIONS if needs_rig}

log = logging.getLogger(__name__)

def _panel_header(title: str) -> QLabel:
    label = QLabel(title)
    label.setObjectName("panelHeader")
    return label

@contextmanager
def _block_signals(*widgets: Iterable[QWidget]):
    """Block widget signals while bulk-populating fields to avoid loops."""
    flat: list[QWidget] = []
    for group in widgets:
        if isinstance(group, QWidget):
            flat.append(group)
        else:
            flat.extend(group)
    for widget in flat:
        widget.blockSignals(True)
    try:
        yield
    finally:
        for widget in flat:
            widget.blockSignals(False)

class AssetBrowser(QWidget):

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(72, 72))
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.itemDoubleClicked.connect(lambda _item: self._add_to_scene())

        import_btn = QPushButton("Import assets...")
        import_btn.clicked.connect(self._import)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_panel_header("Assets"))
        layout.addWidget(self.list, 1)
        layout.addWidget(import_btn)

        for event in ("asset.imported", "asset.removed", "project.opened", "project.created"):
            controller.bus.subscribe(event, lambda _data: self._reload())
        self._reload()

    def _reload(self) -> None:
        self.list.clear()
        if self.controller.project is None:
            return
        for asset in self.controller.asset_manager.assets():
            item = QListWidgetItem(asset.name)
            if asset.type == "image":
                path = self.controller.asset_manager.absolute_path(asset)
                if path.is_file():
                    item.setIcon(QIcon(str(path)))
            caption = asset.category
            if asset.type == "image" and asset.width:
                caption += f"  {asset.width}x{asset.height}"
            item.setToolTip(f"{asset.name}\n{caption}")
            item.setData(Qt.ItemDataRole.UserRole, asset.id)
            if not self.controller.asset_manager.exists_on_disk(asset):
                item.setText(f"{asset.name}  (file missing)")
            self.list.addItem(item)

    def _selected_assets(self):
        assets = []
        for item in self.list.selectedItems():
            asset = self.controller.asset_manager.get(item.data(Qt.ItemDataRole.UserRole))
            if asset is not None:
                assets.append(asset)
        return assets

    def _import(self) -> None:
        files, _filter = QFileDialog.getOpenFileNames(
            self, "Import assets", "", self.controller.file_filter())
        for path in files:
            try:
                self.controller.import_asset(path)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Import assets", f"{path}\n\n{exc}")

    def _add_to_scene(self) -> None:
        scene_id = self.controller.current_scene_id
        if scene_id is None:
            QMessageBox.information(self, "Assets", "Select a scene first.")
            return
        for asset in self._selected_assets():
            if asset.type != "image":
                # Audio import now; audio tracks arrive with the timeline phase.
                log.info("audio asset stored for later audio track phase: %s", asset.id)
                QMessageBox.information(
                    self, "Assets",
                    f"{asset.name}: audio tracks arrive in the timeline phase.")
                continue
            self.controller.add_object_from_asset(scene_id, asset.id)

    def _set_background(self) -> None:
        scene_id = self.controller.current_scene_id
        images = [a for a in self._selected_assets() if a.type == "image"]
        if scene_id is None or not images:
            return
        self.controller.set_scene_background(scene_id, images[0].id)

    def _remove(self) -> None:
        for asset in self._selected_assets():
            try:
                self.controller.remove_asset(asset.id)
            except RuntimeError as exc:
                QMessageBox.information(self, "Assets", str(exc))

    def _context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction("Add to scene", self._add_to_scene)
        background_action = menu.addAction("Set as scene background", self._set_background)
        background_action.setEnabled(
            any(a.type == "image" for a in self._selected_assets()))
        menu.addSeparator()
        menu.addAction("Remove from project", self._remove)
        menu.exec(self.list.mapToGlobal(pos))

class SceneStrip(QWidget):

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        add_btn = QPushButton("+")
        add_btn.setFixedWidth(34)
        add_btn.setToolTip("New scene")
        add_btn.clicked.connect(lambda: self.controller.add_scene())

        left_btn = QPushButton("<")
        left_btn.setFixedWidth(30)
        left_btn.setToolTip("Move scene earlier")
        left_btn.clicked.connect(lambda: self._reorder(-1))

        right_btn = QPushButton(">")
        right_btn.setFixedWidth(30)
        right_btn.setToolTip("Move scene later")
        right_btn.clicked.connect(lambda: self._reorder(1))

        dup_btn = QPushButton("Duplicate")
        dup_btn.clicked.connect(self._duplicate)

        rename_btn = QPushButton("Rename")
        rename_btn.clicked.connect(self._rename)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete)

        self.list = QListWidget()
        self.list.setFlow(QListWidget.Flow.LeftToRight)
        self.list.setFixedHeight(68)
        self.list.currentRowChanged.connect(self._on_row)

        buttons = QHBoxLayout()
        for widget in (add_btn, left_btn, right_btn, dup_btn, rename_btn, del_btn):
            buttons.addWidget(widget)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(buttons)
        layout.addWidget(self.list)

        for event in ("scene.created", "scene.removed", "scene.reordered",
                      "project.opened", "project.created"):
            controller.bus.subscribe(event, lambda _data: self._reload())
        controller.bus.subscribe("scene.selected", self._on_scene_selected_event)
        self._reload()

    def _reload(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        project = self.controller.project
        if project is not None:
            for scene in project.scenes:
                item = QListWidgetItem(f"{scene.name}\n{scene.duration_frames}f")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setSizeHint(QSize(100, 60))
                item.setData(Qt.ItemDataRole.UserRole, scene.id)
                self.list.addItem(item)
            if self.controller.current_scene_id:
                scene = project.scene_by_id(self.controller.current_scene_id)
                if scene is not None:
                    self.list.setCurrentRow(project.scenes.index(scene))
        self.list.blockSignals(False)

    def _on_row(self, row: int) -> None:
        item = self.list.item(row)
        if item is None:
            return
        scene_id = item.data(Qt.ItemDataRole.UserRole)
        if scene_id != self.controller.current_scene_id:
            self.controller.select_scene(scene_id)

    def _on_scene_selected_event(self, data: dict) -> None:
        project = self.controller.project
        if project is None:
            return
        scene = project.scene_by_id(data.get("scene_id", ""))
        if scene is None:
            return
        row = project.scenes.index(scene)
        if self.list.currentRow() != row:
            self.list.setCurrentRow(row)

    def _duplicate(self) -> None:
        if self.controller.current_scene_id:
            self.controller.duplicate_scene(self.controller.current_scene_id)

    def _rename(self) -> None:
        scene_id = self.controller.current_scene_id
        project = self.controller.project
        if scene_id is None or project is None:
            return
        scene = project.scene_by_id(scene_id)
        name, ok = QInputDialog.getText(self, "Rename scene", "Scene name",
                                        text=scene.name)
        if ok and name.strip():
            self.controller.update_scene_metadata(scene_id, name=name.strip())

    def _delete(self) -> None:
        scene_id = self.controller.current_scene_id
        if scene_id is None:
            return
        project = self.controller.project
        scene = project.scene_by_id(scene_id)
        confirm = QMessageBox.question(
            self, "Delete scene",
            f"Delete {scene.name!r}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.controller.remove_scene(scene_id)

    def _reorder(self, delta: int) -> None:
        if self.controller.current_scene_id:
            self.controller.reorder_scene(self.controller.current_scene_id, delta)

class PropertiesPanel(QWidget):

    FIELDS = (
        ("x", "X", -100000, 100000, 1.0),
        ("y", "Y", -100000, 100000, 1.0),
        ("rotation", "Rotation (deg)", -3600, 3600, 1.0),
        ("scale_x", "Scale X", 0.01, 50.0, 0.05),
        ("scale_y", "Scale Y", 0.01, 50.0, 0.05),
        ("opacity", "Opacity", 0.0, 1.0, 0.05),
    )

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._scene_id: str | None = None
        self._obj: SceneObject | None = None

        self._spinboxes: dict[str, QDoubleSpinBox] = {}
        form = QFormLayout()
        for key, label, lo, hi, step in self.FIELDS:
            box = QDoubleSpinBox()
            box.setRange(lo, hi)
            box.setDecimals(2)
            box.setSingleStep(step)
            box.valueChanged.connect(self._commit_numbers)
            self._spinboxes[key] = box
            form.addRow(label, box)

        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(self._commit_text_field)

        self.visible_check = QCheckBox("Visible")
        self.visible_check.toggled.connect(self._commit_visible)

        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#7c4dff")
        self.color_edit.editingFinished.connect(self._commit_text_field)
        color_btn = QPushButton("...")
        color_btn.setFixedWidth(34)
        color_btn.clicked.connect(self._pick_color)
        color_row = QHBoxLayout()
        color_row.addWidget(self.color_edit, 1)
        color_row.addWidget(color_btn)

        self.text_edit = QLineEdit()
        self.text_edit.editingFinished.connect(self._commit_text_field)
        self.text_label = QLabel("Text")

        key_btn = QPushButton("Set key @f")
        key_btn.clicked.connect(self._add_keyframes)
        del_key_btn = QPushButton("Delete key @f")
        del_key_btn.clicked.connect(self._delete_keyframes)
        clear_btn = QPushButton("Clear tracks")
        clear_btn.clicked.connect(self._clear_tracks)
        self.kf_status = QLabel()
        self.kf_status.setObjectName("hint")
        key_row = QHBoxLayout()
        key_row.addWidget(key_btn)
        key_row.addWidget(del_key_btn)
        key_row.addWidget(clear_btn)
        key_row.addStretch(1)

        # -- procedural / character actions ------------------------------
        self.action_combo = QComboBox()
        for name, _needs_rig in ACTIONS:
            self.action_combo.addItem(ACTION_LABELS.get(name, name), name)
        self.action_start = QSpinBox()
        self.action_start.setRange(0, 359999)
        self.action_end = QSpinBox()
        self.action_end.setRange(1, 360000)
        action_apply = QPushButton("Apply")
        action_apply.clicked.connect(self._apply_action)
        action_row = QHBoxLayout()
        action_row.addWidget(self.action_combo, 1)
        action_row.addWidget(self.action_start)
        action_row.addWidget(self.action_end)
        action_row.addWidget(action_apply)
        follow_btn = QPushButton("Camera follow object (over window)")
        follow_btn.clicked.connect(self._camera_follow)
        action_status = QLabel()
        action_status.setObjectName("hint")
        self.action_status = action_status

        self.none_label = QLabel("Select an object on the canvas")
        self.none_label.setObjectName("hint")
        self.editor = QWidget()
        editor_layout = QVBoxLayout(self.editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addLayout(form)
        editor_layout.addLayout(key_row)
        editor_layout.addWidget(_panel_header("Actions"))
        editor_layout.addLayout(action_row)
        editor_layout.addWidget(follow_btn)
        editor_layout.addWidget(action_status)
        editor_layout.addWidget(self.kf_status)
        editor_layout.addWidget(self.name_edit)
        editor_layout.addWidget(self.visible_check)
        editor_layout.addLayout(color_row)
        editor_layout.addWidget(self.text_label)
        editor_layout.addWidget(self.text_edit)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.none_label)
        self.stack.addWidget(self.editor)
        self.stack.setCurrentIndex(0)

        self.bg_edit = QLineEdit()
        self.bg_edit.setPlaceholderText("#141420")
        self.bg_edit.editingFinished.connect(self._commit_background)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 360000)
        self.duration_spin.valueChanged.connect(self._commit_duration)

        self.camera_spins: dict[str, QDoubleSpinBox] = {}
        camera_form = QFormLayout()
        for key, label, lo, hi in (
            ("x", "Camera X", -100000, 100000),
            ("y", "Camera Y", -100000, 100000),
            ("zoom", "Camera zoom", 0.01, 20.0),
        ):
            box = QDoubleSpinBox()
            box.setRange(lo, hi)
            box.setDecimals(3)
            box.valueChanged.connect(self._commit_camera)
            self.camera_spins[key] = box
            camera_form.addRow(label, box)
        camera_row = QHBoxLayout()
        camera_clear = QPushButton("Clear camera keys")
        camera_clear.clicked.connect(self._clear_camera)
        camera_row.addStretch(1)
        camera_row.addWidget(camera_clear)

        self.transition_combo = QComboBox()
        self.transition_combo.addItems(list(SCENE_TRANSITIONS))
        self.transition_combo.currentTextChanged.connect(self._commit_transition)
        self.transition_spin = QSpinBox()
        self.transition_spin.setRange(1, 359999)
        self.transition_spin.valueChanged.connect(self._commit_transition_frames)

        scene_form = QFormLayout()
        scene_form.addRow("Background", self.bg_edit)
        scene_form.addRow("Duration (frames)", self.duration_spin)
        scene_form.addRow("Transition", self.transition_combo)
        scene_form.addRow("Transition frames", self.transition_spin)
        scene_form.addRow(camera_form)
        scene_form.addRow(camera_row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_panel_header("Properties"))
        layout.addWidget(self.stack)
        layout.addWidget(_panel_header("Scene"))
        layout.addLayout(scene_form)
        layout.addStretch(1)

        for event in ("object.selected", "scene.updated", "scene.selected",
                      "project.opened", "project.created", "timeline.frame"):
            controller.bus.subscribe(event, self._refresh)
        self._refresh({})

    def _current_scene(self):
        project = self.controller.project
        if project is None or self._scene_id is None:
            return None
        return project.scene_by_id(self._scene_id)

    def _refresh(self, data: dict) -> None:
        self._scene_id = data.get("scene_id") or self.controller.current_scene_id
        scene = self._current_scene()
        selected = self.controller.selected_object_id
        self._obj = scene.object_by_id(selected) if (scene and selected) else None

        with _block_signals(self._spinboxes.values(), self.name_edit,
                            self.visible_check, self.color_edit,
                            self.text_edit, self.bg_edit,
                            self.duration_spin, self.camera_spins.values(),
                            self.transition_combo, self.transition_spin,
                            self.action_combo, self.action_start,
                            self.action_end):
            if scene is not None:
                self.bg_edit.setText(scene.background_color)
                self.duration_spin.setValue(scene.duration_frames)
                mix = scene.transition if scene.transition in SCENE_TRANSITIONS else "none"
                self.transition_combo.setCurrentText(mix)
                # 0 frames means "no transition configured"; display at least
                # 1 so the spinbox stays valid without forcing a commit.
                self.transition_spin.setValue(max(1, scene.transition_frames))
                project = self.controller.project
                stage_w = float(project.settings.width)
                stage_h = float(project.settings.height)
                camera = camera_state(scene, self.controller.player.frame,
                                      stage_w, stage_h)
                for key, box in self.camera_spins.items():
                    box.setValue(float(getattr(camera, key)))
            if self._obj is None:
                self.stack.setCurrentIndex(0)
                return
            self.stack.setCurrentIndex(1)
            # Spinboxes show evaluated values at the playback frame: during
            # playback they act as an animation readout, instant by instant.
            snap = object_snapshot(self._obj, self.controller.player.frame)
            for key, box in self._spinboxes.items():
                box.setValue(float(getattr(snap, key)))
            self.name_edit.setText(self._obj.name)
            self.visible_check.setChecked(self._obj.visible)
            self.color_edit.setText(self._obj.color)
            is_text = self._obj.type == "text"
            self.text_label.setVisible(is_text)
            self.text_edit.setVisible(is_text)
            self.text_edit.setText(self._obj.text)
            tracked = {name: len(kfs) for name, kfs in self._obj.tracks.items() if kfs}
            self.kf_status.setText(
                "tracks: " + ", ".join(f"{n}({c}k)" for n, c in tracked.items())
                if tracked else "no keyframes yet")
            self._refresh_action_window(scene)

    def _refresh_action_window(self, scene) -> None:
        """Window spins default to [playhead, playhead + 2 s] clamped."""
        if scene is None:
            return
        fps = self.controller.project.settings.fps
        head = self.controller.player.frame
        start = min(head, max(0, scene.duration_frames - 2))
        end = min(scene.duration_frames - 1, max(start + 1, head + fps * 2))
        self.action_start.setValue(start)
        self.action_end.setValue(end)
        in_rig = bool(self._obj and self._obj.extras.get("rig"))
        if self.action_combo.currentData() in _RIG_ONLY_ACTIONS and not in_rig:
            self.action_status.setText("rig actions need a character rig part")
        else:
            self.action_status.setText("")

    # Two commit shapes exist on purpose:
    # - *_commit_numbers: continuous editing (dragging a spinbox) must not
    #   spam one controller event per tick, so it sends a single combined update.
    # - *_commit_text_field: discrete commits on editingFinished.

    def _commit_numbers(self) -> None:
        if self._obj is None or self._scene_id is None:
            return
        values = {key: float(box.value()) for key, box in self._spinboxes.items()}
        self.controller.update_object(self._scene_id, self._obj.id, **values)

    def _commit_text_field(self) -> None:
        if self._obj is None or self._scene_id is None:
            return
        self.controller.update_object(
            self._scene_id, self._obj.id,
            name=self.name_edit.text().strip(),
            color=self.color_edit.text().strip(),
            text=self.text_edit.text(),
        )

    def _commit_visible(self, visible: bool) -> None:
        if self._obj is None or self._scene_id is None:
            return
        self.controller.update_object(self._scene_id, self._obj.id, visible=visible)

    def _add_keyframes(self) -> None:
        if self._obj is None or self._scene_id is None:
            return
        values = {key: float(box.value()) for key, box in self._spinboxes.items()}
        self.controller.set_keyframes(
            self._scene_id, self._obj.id, self.controller.player.frame, values)

    def _delete_keyframes(self) -> None:
        if self._obj is None or self._scene_id is None:
            return
        self.controller.remove_keyframe_at(
            self._scene_id, self._obj.id, self.controller.player.frame)

    def _clear_tracks(self) -> None:
        if self._obj is None or self._scene_id is None:
            return
        self.controller.clear_object_tracks(self._scene_id, self._obj.id)

    def _commit_duration(self, frames: int) -> None:
        if self._scene_id is not None:
            self.controller.update_scene_metadata(
                self._scene_id, duration_frames=frames)

    def _commit_camera(self) -> None:
        if self._scene_id is None:
            return
        values = {key: float(box.value()) for key, box in self.camera_spins.items()}
        self.controller.set_camera_keyframes(
            self._scene_id, self.controller.player.frame, values)

    def _clear_camera(self) -> None:
        if self._scene_id is not None:
            self.controller.clear_camera_tracks(self._scene_id)

    def _apply_action(self) -> None:
        # Engine validation errors (bad window, missing rig) surface in the
        # hint label instead of a modal - actions are trial-and-error edits.
        if self._obj is None or self._scene_id is None:
            return
        action = self.action_combo.currentData()
        try:
            self.controller.apply_action(
                self._scene_id, self._obj.id, action,
                self.action_start.value(), self.action_end.value())
        except (ValueError, KeyError) as exc:
            self.action_status.setText(str(exc))
        else:
            self.action_status.setText(f"{ACTION_LABELS.get(action, action)} applied")

    def _camera_follow(self) -> None:
        if self._obj is None or self._scene_id is None:
            return
        try:
            self.controller.set_camera_follow(
                self._scene_id, self._obj.id,
                self.action_start.value(), self.action_end.value())
        except (ValueError, KeyError) as exc:
            self.action_status.setText(str(exc))
        else:
            self.action_status.setText("camera follow applied")

    def _commit_transition(self, transition: str) -> None:
        if self._scene_id is not None:
            self.controller.update_scene_metadata(self._scene_id, transition=transition)

    def _commit_transition_frames(self, frames: int) -> None:
        if self._scene_id is not None:
            self.controller.update_scene_metadata(
                self._scene_id, transition_frames=frames)

    def _commit_background(self) -> None:
        if self._scene_id is None:
            return
        self.controller.update_scene_metadata(
            self._scene_id, background_color=self.bg_edit.text().strip())

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(parent=self, title="Object color")
        if color.isValid():
            self.color_edit.setText(color.name())
            self._commit_text_field()
