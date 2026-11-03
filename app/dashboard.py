"""Dashboard: project landing screen — new, open, recent projects.

Kept separate from the workspace so the editor never loads until a project
exists, mirroring the production workflow (INFO.md 11).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.controller import AppController

log = logging.getLogger(__name__)

RESOLUTION_PRESETS = [
    ("1920 x 1080  (16:9)", 1920, 1080),
    ("1080 x 1920  (9:16)", 1080, 1920),
    ("1080 x 1080  (1:1)", 1080, 1080),
    ("1280 x 720   (16:9)", 1280, 720),
]

def _branding(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "resources" / "branding" / name

class NewProjectDialog(QDialog):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")

        self.name_edit = QLineEdit("My Animation")
        self.folder_edit = QLineEdit(str(Path.home() / "Documents" / "MOVEXA Projects"))
        browse = QPushButton("Browse...")
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
        layout.addLayout(form)
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

class DashboardScreen(QWidget):

    def __init__(self, controller: AppController,
                 enter_workspace: Callable[[], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._enter_workspace = enter_workspace

        logo = QLabel()
        logo.setPixmap(QPixmap(str(_branding("logo.png"))).scaledToWidth(280))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("MOVEXA")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Create Motion. Tell Stories.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        new_btn = QPushButton("New Project")
        new_btn.setObjectName("primary")
        new_btn.clicked.connect(self._new_project)

        open_btn = QPushButton("Open Project...")
        open_btn.clicked.connect(self._open_dialog)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(new_btn)
        buttons.addWidget(open_btn)
        buttons.addStretch(1)

        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._open_recent)

        layout = QVBoxLayout(self)
        layout.addSpacing(24)
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addLayout(buttons)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Recent projects"))
        layout.addWidget(self.recent_list, 1)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._reload_recent()
        super().showEvent(event)

    def _reload_recent(self) -> None:
        self.recent_list.clear()
        for directory in self.controller.manager.load_recent():
            item = QListWidgetItem(Path(directory).name)
            item.setToolTip(directory)
            item.setData(Qt.ItemDataRole.UserRole, directory)
            self.recent_list.addItem(item)

    def _open_recent(self, item: QListWidgetItem) -> None:
        self._open_project(Path(item.data(Qt.ItemDataRole.UserRole)))

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
            QMessageBox.critical(self, "New Project", f"Could not create project:\n{exc}")
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
            QMessageBox.critical(self, "Open Project", f"Could not open project:\n{exc}")
            return
        problems = self.controller.validation_problems(self.controller.project)
        if problems:
            QMessageBox.warning(
                self, "Project warnings",
                "The project loaded with problems:\n\n"
                + "\n".join(f"- {p}" for p in problems[:8]))
        self._enter_workspace()
