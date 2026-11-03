"""Loading screen: branding + machine/library checks before the menu shows.

Checks run on a worker thread and stream into the checklist; the screen
auto-advances to the main window only when every required check passed.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import envcheck
from app.branding import svg_pixmap
from app.theme import BRAND

log = logging.getLogger(__name__)


class _CheckWorker(QThread):
    """Runs every check off the GUI thread; one result signal per check."""

    check_done = Signal(int)          # row index, mirrored into _results
    finished_all = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._results: list[envcheck.CheckResult] = []

    @property
    def results(self) -> list[envcheck.CheckResult]:
        return list(self._results)

    def run(self) -> None:  # noqa: D102 - QThread entrypoint
        self._results = envcheck.collect_checks()
        for index in range(len(self._results)):
            self.check_done.emit(index)
        self.finished_all.emit()


class LoadingScreen(QWidget):
    """Brand splash. Returns from exec() automatically when safe to start."""

    CONTINUE_DELAY_MS = 500

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SplashScreen
                            | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(560, 560)

        self._row_labels: list[QLabel] = []
        self._results: list[envcheck.CheckResult] = []

        logo = QLabel()
        logo.setPixmap(svg_pixmap(160))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("MOVEXA")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Preparing your studio…")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Check list in a fixed-height frame so rows appear in order even
        # before their results arrive.
        self._check_frame = QFrame()
        self._check_frame.setObjectName("checkFrame")
        check_layout = QVBoxLayout(self._check_frame)
        check_layout.setContentsMargins(14, 10, 14, 10)
        check_layout.setSpacing(6)
        # Rows are created after collect order is known; envcheck is cheap,
        # so building placeholders from a fresh call keeps names honest.
        for name in _expected_names():
            row = QLabel(f"○  {name}")
            row.setObjectName("checkRow")
            check_layout.addWidget(row)
            self._row_labels.append(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, len(self._row_labels))
        self.progress.setTextVisible(False)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.reject_or_close)
        self.exit_btn.setVisible(False)

        controls = QHBoxLayout()
        controls.addStretch(1)
        controls.addWidget(self.exit_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 20)
        layout.addSpacing(6)
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(self._check_frame)
        layout.addWidget(self.progress)
        layout.addSpacing(4)
        layout.addLayout(controls)

        self._worker: _CheckWorker | None = None
        self.canceled = False
        self.continued = False
        self._continue_timer = QTimer(self)
        self._continue_timer.setSingleShot(True)
        self._continue_timer.timeout.connect(self.accept_or_close)

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        self._worker = _CheckWorker()
        self._worker.check_done.connect(self._on_check_done)
        self._worker.finished_all.connect(self._on_all_done)
        self._worker.start()

    def exec_blocking(self) -> bool:
        """Modal helper for direct use; returns True when startup may proceed."""
        self.show()
        self.start()
        log.info("MOVEXA loading screen: running environment checks")
        return True

    # -- slots ---------------------------------------------------------------

    def _on_check_done(self, index: int) -> None:
        results = self._worker.results if self._worker else []
        if index >= len(results) or index >= len(self._row_labels):
            return
        result = results[index]
        icon = "✓" if result.ok else ("!" if result.required else "!")
        color = BRAND["cyan"] if result.ok else BRAND["danger"]
        row = self._row_labels[index]
        row.setText(f"{icon}  {result.name} — {result.detail}")
        row.setStyleSheet(f"color: {color};")
        self.progress.setValue(index + 1)

    def _on_all_done(self) -> None:
        results = self._worker.results if self._worker else []
        self._results = results
        required_failed = [r for r in results if r.required and not r.ok]
        if required_failed:
            self.progress.setStyleSheet("QProgressBar::chunk { background: #f43f5e; }")
            self.exit_btn.setVisible(True)
            log.error("MOVEXA startup blocked by: %s",
                      ", ".join(r.name for r in required_failed))
            return
        self._continue_timer.start(self.CONTINUE_DELAY_MS)

    def apply_result(self, result: envcheck.CheckResult, index: int) -> None:
        """Test seam: feed one result without any thread."""
        self._on_check_done_structural(result, index)
        self.progress.setValue(index + 1)
        self._results.append(result)

    def _on_check_done_structural(self, result: envcheck.CheckResult, index: int) -> None:
        if index >= len(self._row_labels):
            return
        icon = "✓" if result.ok else "!"
        color = BRAND["cyan"] if result.ok else BRAND["danger"]
        row = self._row_labels[index]
        row.setText(f"{icon}  {result.name} — {result.detail}")
        row.setStyleSheet(f"color: {color};")

    def accept_or_close(self) -> None:
        self.continued = True
        on_continue = getattr(self, "on_continue", None)
        if on_continue is not None:
            on_continue()
        else:
            self.close()

    def reject_or_close(self) -> None:
        self.canceled = True
        self.close()
        log.warning("MOVEXA exited from the loading screen")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(2000)
        self.deleteLater()
        event.accept()


def _expected_names() -> list[str]:
    """Row labels mirror collect_checks() ordering; used before results land."""
    return [r.name for r in envcheck.collect_checks()] or ["Environment"]
