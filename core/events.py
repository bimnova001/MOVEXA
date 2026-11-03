"""Event-driven communication between subsystems (architecture doc 4.1).

The bus is deliberately framework-free so that engine logic stays testable
without a QApplication. GUI layers bridge bus events to Qt when needed.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger(__name__)

#: Event names published by the application (architecture doc 4.1).
Event = str

Handler = Callable[[dict[str, Any]], None]


class EventBus:
    """Minimal synchronous publish/subscribe hub.

    Handlers that raise are reported to the log instead of breaking the
    dispatch loop, so one bad listener cannot freeze a publish.
    """

    def __init__(self) -> None:
        self._handlers: dict[Event, list[Handler]] = defaultdict(list)

    def subscribe(self, event: Event, handler: Handler) -> None:
        """Register *handler* for *event*, or ``"*"`` for every event."""
        if handler not in self._handlers[event]:
            self._handlers[event].append(handler)

    def unsubscribe(self, event: Event, handler: Handler) -> None:
        """Remove a previously registered handler (silently ignores unknown)."""
        listeners = self._handlers.get(event, [])
        if handler in listeners:
            listeners.remove(handler)

    def publish(self, event: Event, data: dict[str, Any] | None = None) -> None:
        """Dispatch *event* to its handlers and to wildcard handlers.

        This is synchronous on purpose: subscribers run in the publisher's
        thread, which keeps ordering predictable. Long-running work belongs
        in background workers, not in event handlers.
        """
        payload = {} if data is None else dict(data)
        for handler in list(self._handlers.get(event, [])) + list(self._handlers.get("*", [])):
            try:
                handler(payload)
            except Exception:  # noqa: BLE001 - one bad handler must not stop dispatch
                log.exception("event handler failed for %s", event)

    def clear(self) -> None:
        self._handlers.clear()
