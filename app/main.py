
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

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

    window = MainWindow()
    window.show()
    log.info("%s %s started", APP_NAME, APP_VERSION)
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
