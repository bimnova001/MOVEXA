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
    """Recent project card: name, modified date, tooltip path, dbl-click opens."""

    def __init__(self, directory: str,
                 on_open: Callable[[Path], None]) -> None:
        super().__init__()
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(directory)
        self._on_open = on_open
        self._directory = directory

        project_path = Path(directory) / "project.json"
        modified = "—"
        if project_path.exists():
            try:
                mtime = project_path.stat().st_mtime
                modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            except OSError:
                pass

        inner_name = QLabel(Path(directory).name or directory)
        inner_name.setObjectName("cardTitle")
        inner_name.setWordWrap(True)
        inner_name.setMaximumHeight(44)

        caption = QLabel(f"Modified {modified}")
        caption.setObjectName("cardMeta")
        caption.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.addWidget(inner_name)
        layout.addWidget(caption)
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

        # -- left branding column ------------------------------------------------
        logo = QLabel()
        logo.setPixmap(svg_pixmap(120))
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

        tagline = QLabel("AI-assisted 2D animation studio.\nKeyframes, rigs, AI takes, "
                         "MP4 export — all in one place.")
        tagline.setObjectName("subtitle")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setWordWrap(True)

        branding = QVBoxLayout()
        branding.addStretch(1)
        branding.addWidget(logo)
        branding.addWidget(title)
        branding.addWidget(subtitle)
        branding.addSpacing(8)
        branding.addWidget(tagline)
        branding.addSpacing(8)
        branding.addWidget(version)
        branding.addStretch(2)

        brand_panel = QFrame()
        brand_panel.setObjectName("brandPanel")
        brand_panel.setLayout(branding)
        brand_panel.setFixedWidth(300)

        # -- right column: hero actions + recents --------------------------------
        new_btn = QPushButton("＋ New Project")
        new_btn.setObjectName("hero")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setMinimumHeight(64)
        new_btn.clicked.connect(self._new_project)

        open_btn = QPushButton("Open Project Folder")
        open_btn.setObjectName("secondary")
        open_btn.setMinimumHeight(64)
        open_btn.clicked.connect(self._open_dialog)

        hero_row = QHBoxLayout()
        hero_row.setSpacing(10)
        hero_row.addWidget(new_btn, 2)
        hero_row.addWidget(open_btn, 1)

        recents_caption = QLabel("Recent projects")
        recents_caption.setObjectName("sectionHeader")

        self.cards_area = QScrollArea()
        self.cards_area.setWidgetResizable(True)
        self.cards_area.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_container = QWidget()
        self.cards_container.setObjectName("cardsBackground")
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setSpacing(12)
        self.cards_grid.setContentsMargins(0, 0, 12, 0)
        self.cards_area.setWidget(self.cards_container)

        self.empty_state = QLabel(
            "No projects yet — create your first one to get started.")
        self.empty_state.setObjectName("hint")
        self.empty_state.setWordWrap(True)
        self.cards_grid.addWidget(self.empty_state, 0, 0)

        column = QVBoxLayout()
        column.setContentsMargins(24, 24, 24, 24)
        column.setSpacing(14)
        column.addLayout(hero_row)
        column.addWidget(recents_caption)
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
        # label itself - it gets re-added to the grid on every pass.
        keep_empty = self.empty_state
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not keep_empty:
                widget.deleteLater()
        directories = self.controller.manager.load_recent()[:MAX_RECENT_CARDS]
        if not directories:
            self.cards_grid.addWidget(self.empty_state, 0, 0)
            self.empty_state.show()
            return
        self.empty_state.hide()
        for index, directory in enumerate(directories):
            card = ProjectCard(str(directory), self._open_project)
            self.cards_grid.addWidget(card, index // 3, index % 3)

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
