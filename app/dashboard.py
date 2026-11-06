"""Dashboard: landing menu in the style of editor home screens (hero +
recent-project cards). The editor page stays unloaded until a project
exists, mirroring the production workflow (INFO.md 11).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.branding import svg_pixmap
from app.controller import AppController
from app.thumbs import cached_thumbnail

log = logging.getLogger(__name__)

RESOLUTION_PRESETS = [
    ("1920 × 1080  (16:9)", 1920, 1080),
    ("1080 × 1920  (9:16)", 1080, 1920),
    ("1080 × 1080  (1:1)", 1080, 1080),
    ("1280 × 720  (16:9)", 1280, 720),
]

MAX_RECENT_CARDS = 9


def _branding(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "resources" / "branding" / name


class NewProjectDialog(QDialog):
    """Project creation wizard (uses the shared brand fonts/buttons)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")

        self.name_edit = QLineEdit("My Animation")
        self.folder_edit = QLineEdit(str(Path.home() / "Documents" / "MOVEXA Projects"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_folder)

        self.resolution = QComboBox()
        for label, _w, _h in RESOLUTION_PRESETS:
            self.resolution.addItem(label)

        self.fps = QComboBox()
        self.fps.addItems(["24", "30", "60"])
        self.fps.setCurrentIndex(1)

        self.path_hint = QLabel()
        self.path_hint.setObjectName("hint")

        form = QFormLayout()
        form.addRow("Project name", self.name_edit)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(browse)
        form.addRow("Location", folder_row)
        form.addRow("Resolution", self.resolution)
        form.addRow("Frame rate", self.fps)
        form.addRow(self.path_hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addSpacing(6)
        layout.addLayout(form)
        layout.addSpacing(12)
        layout.addWidget(buttons)

        self.name_edit.textChanged.connect(self._refresh_path_hint)
        self.folder_edit.textChanged.connect(self._refresh_path_hint)
        self._refresh_path_hint()

    def _browse_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose location")
        if chosen:
            self.folder_edit.setText(chosen)

    def target_directory(self) -> Path:
        """Slugged project folder inside the chosen location."""
        slug = re.sub(r"[^\w\- ]", "", self.name_edit.text().strip()).strip() or "project"
        folder = Path(self.folder_edit.text().strip())
        return folder / re.sub(r"\s+", "_", slug)

    def _refresh_path_hint(self) -> None:
        self.path_hint.setText(str(self.target_directory()))

    def validate(self) -> str | None:
        """Return an error message, or None when creation may proceed."""
        if not self.name_edit.text().strip():
            return "Enter a project name."
        target = self.target_directory()
        if (target / "project.json").exists():
            return f"A project already exists at:\n{target}"
        parts = [target]
        parts.extend(target.parents[:3])
        for p in parts:
            if p.exists() and p.is_file():
                return f"Path blocked by an existing file:\n{p}"
        if target.exists() and any(target.iterdir()):
            return f"Folder is not empty:\n{target}"
        return None

    def accept(self) -> None:  # keep the standard dialog flow gated on validation
        problem = self.validate()
        if problem:
            QMessageBox.warning(self, "New Project", problem)
            return
        super().accept()

    # -- workflow ------------------------------------------------------------

class ProjectCard(QFrame):
    """Recent project card: thumbnail, name, meta, dbl-click opens, ✕ unpins."""

    def __init__(self, directory: str, on_open: Callable[[Path], None],
                 on_remove: Callable[[Path], None] | None = None) -> None:
        super().__init__()
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(directory)
        self.setMaximumWidth(320)
        if on_remove is not None:
            self._on_remove = on_remove
        else:
            self._on_remove = lambda _d: None
        self._on_open = on_open
        self._directory = directory

        from json import JSONDecodeError, loads
        scenes = 0
        total_frames = 0
        width = height = 0
        fps = 30
        project_path = Path(directory) / "project.json"
        modified = "—"
        data: dict = {}
        try:
            if project_path.exists():
                mtime = project_path.stat().st_mtime
                modified = datetime.fromtimestamp(mtime).strftime("%d %b %H:%M")
                with open(project_path, encoding="utf-8") as fh:
                    data = loads(fh)
                scenes = len(data.get("scenes", []))
                total_frames = sum(int(s.get("duration_frames", 0))
                                   for s in data.get("scenes", []))
                settings = data.get("settings", {})
                width = int(settings.get("width", 0))
                height = int(settings.get("height", 0))
                fps = int(settings.get("fps", 30))
        except (OSError, JSONDecodeError, TypeError, ValueError):
            pass

        self._thumbnail = QLabel()
        self._thumbnail.setObjectName("cardThumb")
        self._thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = cached_thumbnail(directory, width=296)
        if pixmap is not None and not pixmap.isNull():
            self._thumbnail.setPixmap(pixmap.scaled(
                self._thumbnail.width() or 296, 100,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation))
        else:
            self._thumbnail.setFixedHeight(96)
            self._thumbnail.setText("▦")
            self._thumbnail.setStyleSheet(
                "color:#3a3a46; font-size: 26px;"
                "background:#232329; border-radius:8px;")

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        inner_name = QLabel(Path(directory).name or directory)
        inner_name.setObjectName("cardTitle")
        inner_name.setWordWrap(True)
        title_row.addWidget(inner_name, 1)
        if on_remove is not None:
            remove_btn = QPushButton("✕")
            remove_btn.setObjectName("cardRemove")
            remove_btn.setFixedSize(22, 22)
            remove_btn.setToolTip("Remove from recents (folder is kept)")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(
                lambda: self._on_remove(Path(self._directory)))
            title_row.addWidget(remove_btn)

        caption = QLabel(f"Modified {modified}")
        caption.setObjectName("cardMeta")
        stats = QLabel(
            (f"{width}×{height} · {fps} fps · {total_frames} frames"
             if scenes else "empty project"))
        stats.setObjectName("cardMeta")
        stats.setToolTip(f"{scenes} scene(s)")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(4)
        layout.addWidget(self._thumbnail)
        layout.addLayout(title_row)
        layout.addWidget(caption)
        layout.addWidget(stats)
        layout.addStretch(1)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self._on_open(Path(self._directory))


class DashboardScreen(QWidget):
    """Menu screen: hero New Project + recents-as-cards (editor style)."""

    def __init__(self, controller: AppController,
                 enter_workspace: Callable[[], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._enter_workspace = enter_workspace

        # -- left branding column (compact per review: 240px) --------------------
        logo = QLabel()
        logo.setPixmap(svg_pixmap(72))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("MOVEXA")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Create Motion. Tell Stories.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel("v0.1.0")
        version.setObjectName("hint")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tagline = QLabel("AI-assisted 2D animation studio: keyframes, rigs,\n"
                         "AI takes and MP4 export in one place.")
        tagline.setObjectName("subtitle")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setWordWrap(True)

        browse_btn = QPushButton("Browse Projects…")
        browse_btn.setObjectName("topbarBtn")
        browse_btn.setToolTip("Open any MOVEXA project folder")
        browse_btn.clicked.connect(self._open_dialog)

        branding = QVBoxLayout()
        branding.setContentsMargins(12, 16, 12, 12)
        branding.setSpacing(6)
        branding.addStretch(1)
        branding.addWidget(logo)
        branding.addWidget(title)
        branding.addWidget(subtitle)
        branding.addSpacing(6)
        branding.addWidget(tagline)
        branding.addSpacing(10)
        branding.addWidget(browse_btn)
        branding.addStretch(2)
        branding.addWidget(version)

        brand_panel = QFrame()
        brand_panel.setObjectName("brandPanel")
        brand_panel.setLayout(branding)
        brand_panel.setFixedWidth(240)

        # -- right column: balanced hero actions + recents -----------------------
        new_btn = QPushButton("＋ New Project")
        new_btn.setObjectName("hero")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setMinimumHeight(44)
        new_btn.clicked.connect(self._new_project)

        open_btn = QPushButton("Open Project Folder")
        open_btn.setObjectName("secondary")
        open_btn.setMinimumHeight(44)
        open_btn.clicked.connect(self._open_dialog)

        hero_row = QHBoxLayout()
        hero_row.setSpacing(10)
        hero_row.addWidget(new_btn, 1)
        hero_row.addWidget(open_btn, 1)

        recents_caption = QLabel("Recent projects")
        recents_caption.setObjectName("sectionHeader")
        refresh_btn = QPushButton("⟳ Recent")
        refresh_btn.setObjectName("topbarBtn")
        refresh_btn.setToolTip("Refresh the recents list")
        refresh_btn.clicked.connect(self._reload_recent)

        recents_row = QHBoxLayout()
        recents_row.addWidget(recents_caption)
        recents_row.addStretch(1)
        recents_row.addWidget(refresh_btn)

        self.cards_area = QScrollArea()
        self.cards_area.setWidgetResizable(True)
        self.cards_area.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_container = QWidget()
        self.cards_container.setObjectName("cardsBackground")
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setSpacing(10)
        self.cards_grid.setContentsMargins(0, 0, 12, 0)
        self.cards_area.setWidget(self.cards_container)

        # Empty state: welcoming panel with its own CTA.
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.addStretch(1)
        empty_icon = QLabel()
        empty_icon.setPixmap(svg_pixmap(56))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text = QLabel("No projects yet.\n"
                            "Create your first animation to get started.")
        empty_text.setObjectName("hint")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_cta = QPushButton("Create your first project")
        self.empty_cta.setObjectName("primary")
        self.empty_cta.setMinimumHeight(40)
        self.empty_cta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_cta.clicked.connect(self._new_project)
        empty_layout.addWidget(empty_icon)
        empty_layout.addSpacing(8)
        empty_layout.addWidget(empty_text)
        empty_layout.addSpacing(10)
        empty_layout.addWidget(self.empty_cta, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch(2)
        self.empty_state = empty_widget

        column = QVBoxLayout()
        column.setContentsMargins(20, 20, 20, 20)
        column.setSpacing(12)
        column.addLayout(hero_row)
        column.addLayout(recents_row)
        column.addWidget(self.cards_area, 1)

        column_widget = QWidget()
        column_widget.setLayout(column)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(brand_panel)
        row.addWidget(column_widget, 1)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._reload_recent()
        super().showEvent(event)

    def _reload_recent(self) -> None:
        # Remove previous cards, but never delete the shared empty-state
        # widget itself - it gets re-added to the grid on every pass.
        keep_empty = self.empty_state
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not keep_empty:
                widget.deleteLater()
        self.cards_grid.addWidget(self.empty_state, 0, 0, 1, 3)
        directories = self.controller.manager.load_recent()[:MAX_RECENT_CARDS]
        if not directories:
            self.empty_state.show()
            return
        self.empty_state.hide()
        for index, directory in enumerate(directories):
            card = ProjectCard(str(directory), self._open_project,
                               on_remove=self._remove_recent)
            self.cards_grid.addWidget(card, index // 3, index % 3)

    def _remove_recent(self, directory: Path) -> None:
        self.controller.manager.remove_recent(directory)
        self._reload_recent()

    def _new_project(self) -> None:
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        width, height = RESOLUTION_PRESETS[dialog.resolution.currentIndex()][1:]
        try:
            self.controller.new_project(
                directory=dialog.target_directory(),
                name=dialog.name_edit.text().strip(),
                width=width, height=height,
                fps=int(dialog.fps.currentText()),
            )
        except OSError as exc:
            QMessageBox.critical(self, "New Project",
                                 f"Could not create project:\n{exc}")
            return
        self._enter_workspace()

    def _open_dialog(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Open MOVEXA project folder")
        if directory:
            self._open_project(Path(directory))

    def _open_project(self, directory: Path) -> None:
        try:
            self.controller.open_project(directory)
        except FileNotFoundError:
            QMessageBox.information(
                self, "Open Project",
                f"That folder is not a MOVEXA project:\n{directory}")
            return
        except OSError as exc:
            QMessageBox.critical(self, "Open Project",
                                 f"Could not open project:\n{exc}")
            return
        problems = self.controller.validation_problems(self.controller.project)
        if problems:
            QMessageBox.warning(
                self, "Project warnings",
                "The project loaded with problems:\n\n"
                + "\n".join(f"- {p}" for p in problems[:8]))
        self._enter_workspace()
