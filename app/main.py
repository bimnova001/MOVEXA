
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from app.loading_screen import LoadingScreen
from app.main_window import MainWindow
from app.theme import QSS

APP_NAME = "MOVEXA"
APP_VERSION = "0.1.0"


def _branding(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "resources" / "branding" / name


def main() -> int:
    log = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("MOVEXA")
    app.setWindowIcon(QIcon(str(_branding("icon-256.png"))))
    app.setStyleSheet(QSS)
    # Windows renders the UI, not Qt defaults.
    app.setFont(QFont("Segoe UI", 10))

    # Loading screen first: machine/library checks stream onto the splash,
    # then (only when required checks pass) the menu opens automatically via
    # the loading screen's on_continue callback — no modal exec, so the same
    # path works for the app and for tests.
    loading = LoadingScreen()
    state = {"opened": False}

    def launch_main() -> None:
        if loading.canceled or state["opened"]:
            return
        state["opened"] = True
        window = MainWindow()
        app.main_window = window  # keep a reference alive for the process
        window.show()
        loading.close()
        loading.deleteLater()

    loading.on_continue = launch_main
    loading.show()
    loading.start()
    log.info("%s %s started", APP_NAME, APP_VERSION)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
