"""Command palette (Ctrl+K): fuzzy... well, substring-filtered quick access
to the most useful actions, following the keyboard-first desktop pattern."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class Command(QFrame):
    pass


class CommandPalette(QDialog):
    """Search-to-run launcher, exactly like professional editors."""

    def __init__(self,
                 items: list[tuple[str, Callable[[], None]]],
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        self._items = items
        self._pending_action: Callable[[], None] | None = None

        self.search = QLineEdit()
        self.search.setPlaceholderText("Type a command…")
        self.search.setObjectName("paletteSearch")
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._run_current)

        self.list = QListWidget()
        self.list.setObjectName("paletteList")
        hint = "↑↓ select · Enter run · Esc close"
        self.hint = QLabel(hint)
        self.hint.setObjectName("hint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignRight)

        column = QVBoxLayout()
        column.setContentsMargins(12, 12, 12, 10)
        column.setSpacing(8)
        column.addWidget(self.search)
        column.addWidget(self.list)
        column.addWidget(self.hint)
        self.setLayout(column)
        self.resize(460, 380)

        self._filter()
        self.search.setFocus()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.search.setFocus()
        self.search.selectAll()
        super().showEvent(event)

    def _filter(self, text: str = "") -> None:
        needle = (text or self.search.text()).strip().lower()
        self.list.clear()
        for name, action in self._items:
            if needle in name.lower():
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, action)
                self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _run_current(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        self._pending_action = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.key() == Qt.Key.Key_Down:
            row = min(self.list.row(self.list.currentItem()) + 1, self.list.count() - 1)
            self.list.setCurrentRow(max(0, row))
            return
        if event.key() == Qt.Key.Key_Up:
            row = max(
                0,
                (self.list.row(self.list.currentItem()) or 0) - 1,
            )
            self.list.setCurrentRow(row)
            return
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def exec(self) -> int:  # noqa: D102 - expose the chosen action after close
        choice = super().exec()
        if self._pending_action is not None:
            action = self._pending_action
            self._pending_action = None
            action()
        return choice
