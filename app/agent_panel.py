"""AI agent dock: chat-driven authoring inside the editor page.

Local intents apply instantly and stay offline; outline/scene requests hit
the provider on a worker thread, with validated JSON applied back on the
GUI thread so the controller never mutates off-thread.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ai.providers import (
    ProviderError,
    ProviderManager,
    ProviderNotConfiguredError,
)
from ai._impl import apply_scene_output, validate_scene_output
from app import agent
from app.controller import AppController

log = logging.getLogger(__name__)


class _ProviderWorker(QThread):
    """Provider round-trip off the GUI thread; result lands via signal."""

    result_ready = Signal(str, str)  # kind, payload text
    failed = Signal(str)

    def __init__(self, kind: str, prompt: str, provider, schema: dict | None) -> None:
        super().__init__()
        self._kind = kind
        self._prompt = prompt
        self._provider = provider
        self._schema = schema

    def run(self) -> None:
        try:
            if self._schema is not None:
                result = self._provider.generate_structured(self._prompt, self._schema)
            else:
                result = self._provider.generate_text(self._prompt)
            self.result_ready.emit(self._kind, result.text)
        except (ProviderNotConfiguredError, ProviderError, OSError) as exc:
            self.failed.emit(str(exc))


SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "scene_name": {"type": "string"},
        "duration_frames": {"type": "integer"},
        "objects": {"type": "array"},
        "actions": {"type": "array"},
    },
}


class AgentPanel(QWidget):
    """Chat dock driving local edits + AI providers, CapCut-style."""

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.manager = ProviderManager()
        self._worker: _ProviderWorker | None = None

        head = QHBoxLayout()
        head.setContentsMargins(2, 0, 2, 0)
        title = QLabel("AI Agent")
        title.setObjectName("panelTitle")
        self.status_chip = QLabel()
        self.status_chip.setObjectName("agentChip")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.status_chip)
        self._refresh_chip()

        self.log = QListWidget()
        self.log.setObjectName("agentLog")
        self.log.setWordWrap(True)
        self.log.setUniformItemSizes(False)
        self.log.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        self.input = QLineEdit()
        self.input.setPlaceholderText(
            'e.g. "add circle at 500,300" · "outline: a cat story" · "generate a scene"')
        self.input.returnPressed.connect(self._send)
        send_btn = QPushButton("Send")
        send_btn.setObjectName("primary")
        send_btn.clicked.connect(self._send)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(2, 2, 2, 2)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(send_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(head)
        layout.addWidget(self.log, 1)
        layout.addLayout(input_row)

        self.system_say("Agent ready. Try “help”.")

    # -- display helpers ------------------------------------------------------

    def _append(self, role: str, text: str) -> None:
        color = {
            "user": "#e8e8f0",
            "agent": "#22d3ee",
            "system": "#8f8fa8",
            "error": "#f43f5e",
        }[role]
        item = QListWidgetItem(f"{'🧑' if role == 'user' else '🤖'} {text}")
        item.setForeground(QColor(color))
        self.log.addItem(item)
        self.log.scrollToBottom()

    def user_say(self, text: str) -> None:
        self._append("user", text)

    def agent_say(self, text: str) -> None:
        self._append("agent", text)

    def system_say(self, text: str) -> None:
        self._append("system", text)

    def error_say(self, text: str) -> None:
        self._append("error", text)

    def _refresh_chip(self) -> None:
        provider_name = self.manager.settings.default_provider or "mock"
        offline = provider_name == "mock"
        self.status_chip.setText("OFFLINE · mock" if offline else provider_name)
        self.status_chip.setStyleSheet(
            "color: #8f8fa8; border: 1px solid #2a2a36; border-radius: 9px; "
            "padding: 2px 8px;" if offline else
            "color: #22d3ee; border: 1px solid #2a2a36; border-radius: 9px; "
            "padding: 2px 8px;")

    # -- dispatch --------------------------------------------------------------

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text or self._worker is not None:
            return
        self.input.clear()
        self.user_say(text)
        route, payload = agent.route(text)
        if route == "help":
            self.agent_say(agent.HELP_TEXT)
        elif route == "local":
            self.agent_say(agent.execute_local(payload, self.controller))
        elif route == "outline":
            self.agent_say("Drafting an outline…")
            self._launch("outline", f"Outline a short 2D animation storyboard for: {payload}",
                         None)
        elif route == "scene":
            project = self.controller.project
            if project is None:
                self.error_say("Open a project first.")
                return
            brief = agent._take_after(str(payload), ("generate", "create", "สร้าง")) or str(payload)
            prompt = (f"Scene brief: {brief}. Stage "
                      f"{project.settings.width}x{project.settings.height} at "
                      f"{project.settings.fps} fps, up to 180 frames. JSON only.")
            self.agent_say("Generating scene…")
            self._launch("scene", prompt, SCENE_SCHEMA)

    def _launch(self, kind: str, prompt: str, schema: dict | None) -> None:
        try:
            provider = self.manager.create()
        except (ProviderNotConfiguredError, ProviderError) as exc:
            self.error_say(f"Provider unavailable: {exc}")
            return
        self._worker = _ProviderWorker(kind, prompt, provider, schema)
        self._worker.result_ready.connect(self._on_provider_result)
        self._worker.failed.connect(self._on_provider_failed)
        self._worker.finished.connect(self._worker_cleanup)
        self._worker.start()

    def _worker_cleanup(self) -> None:
        self._worker = None

    def _on_provider_failed(self, message: str) -> None:
        self.error_say(f"Provider failed: {message}")

    def _on_provider_result(self, kind: str, text: str) -> None:
        if kind == "outline":
            self.agent_say(text or "(empty outline)")
            return
        scene_id = self.controller.current_scene_id
        project = self.controller.project
        if scene_id is None or project is None:
            self.error_say("No open scene to receive the scene.")
            return
        payload = agent.parse_payload(text)
        if payload is None:
            self.error_say("Provider returned non-JSON; kept as text.")
            self.agent_say(text[:400])
            return
        errors = validate_scene_output(payload)
        if errors:
            self.error_say("Provider JSON rejected: " + "; ".join(errors[:4]))
            return
        try:
            apply_scene_output(
                self.controller, scene_id, payload,
                project.settings.width, project.settings.height)
        except (ValueError, KeyError) as exc:
            self.error_say(f"Could not apply scene: {exc}")
            return
        objects = len(payload.get("objects", []))
        actions = len(payload.get("actions", []))
        self.agent_say(
            f"Scene built: {objects} object(s), {actions} action(s), "
            f"{payload.get('duration_frames', '?')} frames.")
