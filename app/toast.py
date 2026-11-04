"""Non-blocking success toasts (desktop pattern: confirmations should never
steal focus; errors stay modal in QMessageBox by design)."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class ToastArea(QWidget):
    """Hosts stacked toasts in the bottom-right corner of its parent."""

    LINGER_MS = 3500

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)
        self.hide()
        self.parent().installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt naming
        if watched is self.parent() and event.type() in (
            event.Type.Resize, event.Type.Show,
        ):
            self._reposition()
        return super().eventFilter(watched, event)

    def show(self) -> None:  # noqa: D102 - align to parent geometry
        self._reposition()
        super().show()

    def _reposition(self) -> None:
        parent = self.parent()
        if parent is not None:
            self.setGeometry(parent.rect())

    def info(self, message: str) -> None:
        toast = QFrame(self)
        toast.setObjectName("toast")
        label = QLabel(message)
        label.setObjectName("toastText")
        row = QHBoxLayout(toast)
        row.setContentsMargins(16, 10, 16, 10)
        row.addWidget(label)
        self._layout.addWidget(toast, 0, Qt.AlignmentFlag.AlignBottom)

        def dismiss() -> None:
            toast.hide()
            toast.deleteLater()
            if self._layout.count() <= 1:
                self.hide()

        QTimer.singleShot(self.LINGER_MS, dismiss)
        toast.show()
        self.show()
