"""Main window: dashboard <-> workspace switching, menus, save guard."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
)

from app.controller import AppController
from app.dashboard import DashboardScreen
from app.workspace import WorkspaceScreen

log = logging.getLogger(__name__)


def _branding(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "resources" / "branding" / name


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MOVEXA")
        self.setWindowIcon(QIcon(str(_branding("icon-256.png"))))
        self.resize(1280, 800)

        self.controller = AppController()
        self._dirty = False

        self.pages = QStackedWidget()
        self.dashboard = DashboardScreen(self.controller, self._enter_workspace)
        self.workspace = WorkspaceScreen(self.controller)
        self.pages.addWidget(self.dashboard)
        self.pages.addWidget(self.workspace)
        self.setCentralWidget(self.pages)

        bus = self.controller.bus
        for event in ("scene.updated", "scene.created", "scene.removed",
                      "object.added", "asset.imported", "asset.removed",
                      "project.created", "project.opened"):
            bus.subscribe(event, self._mark_dirty)
        bus.subscribe("project.saved", self._clear_dirty)
        for event in ("project.created", "project.opened"):
            bus.subscribe(event, self._show_workspace_on_open)
            bus.subscribe(event, self._update_status)
        bus.subscribe("project.saved", self._update_status)
        bus.subscribe("project.closed", self._show_dashboard)

        self._build_menus()
        self._build_status_bar()
        self._show_dashboard({})

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("&New Project...", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(lambda: self._switch_to_dashboard_and(None))
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_from_menu)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save)
        file_menu.addAction(save_action)

        close_action = QAction("Close Project", self)
        close_action.triggered.connect(self._close_project)
        file_menu.addAction(close_action)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("About MOVEXA", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

    def _build_status_bar(self) -> None:
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._update_status({})

    def _switch_to_dashboard_and(self, _checked: bool) -> None:
        self._show_dashboard({})
        self.controller.bus.publish("dashboard.shown", {})

    def _show_dashboard(self, _data: dict) -> None:
        self.pages.setCurrentWidget(self.dashboard)
        self._update_status({})

    def _show_workspace_on_open(self, _data: dict) -> None:
        self.pages.setCurrentWidget(self.workspace)

    def _enter_workspace(self) -> None:
        self.pages.setCurrentWidget(self.workspace)
        self._update_status({})

    def _open_from_menu(self) -> None:
        self._show_dashboard({})
        self.dashboard._open_dialog()  # noqa: SLF001 - single shared flow with dashboard

    def _save(self) -> None:
        if self.controller.has_project():
            self.controller.save()

    def _close_project(self) -> None:
        if self._confirm_exit("Close the project?"):
            self.controller.close_project()

    def _mark_dirty(self, _data: dict) -> None:
        self._dirty = True
        self._update_status({})

    def _clear_dirty(self, _data: dict) -> None:
        self._dirty = False
        self._update_status({})

    def _update_status(self, _data: dict) -> None:
        project = self.controller.project
        directory = self.controller.manager.current_dir
        if project is None:
            self.status.showMessage("MOVEXA - no project open")
        else:
            flag = "  -  UNSAVED CHANGES" if self._dirty else ""
            self.status.showMessage(
                f"{project.name}  -  {directory}{flag}")

    def _confirm_exit(self, message: str) -> bool:
        if self.controller.has_project() and self._dirty:
            answer = QMessageBox.question(
                self, "Unsaved changes",
                f"{message}\n\nYou have unsaved changes. Save first?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel)
            if answer == QMessageBox.StandardButton.Save:
                self.controller.save()
                return True
            if answer == QMessageBox.StandardButton.Cancel:
                return False
            return True
        return True

    def _about(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("About MOVEXA")
        box.setIconPixmap(QPixmap(str(_branding("logo.png"))).scaledToWidth(200))
        box.setText("MOVEXA 0.1.0\n\nCreate Motion. Tell Stories.\n\n"
                    "AI-assisted 2D animation studio for Windows.")
        box.exec()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._confirm_exit("Quit MOVEXA?"):
            event.accept()
        else:
            event.ignore()
