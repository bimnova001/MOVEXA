"""Undo/redo history (Qt-free, bounded, snapshot-based).

Each undoable controller mutation records the whole lossless project data
before and after; undo/redo swap those snapshots back through the
controller. Full-project snapshots are small JSON trees here (screens are
hand-drawn vectors, not video), so exactness beats cleverness on diffing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    label: str
    before: dict
    after: dict


@dataclass
class UndoStack:
    limit: int = 100
    steps: list[Step] = field(default_factory=list)
    _cursor: int = 0  # number of steps currently applied

    def push(self, label: str, before: dict, after: dict) -> None:
        # Any mutation after a partial undo discards the redone branch,
        # matching every mainstream editor's behavior.
        del self.steps[self._cursor:]
        self.steps.append(Step(label=label, before=before, after=after))
        if len(self.steps) > self.limit:
            del self.steps[: len(self.steps) - self.limit]
        self._cursor = len(self.steps)

    def can_undo(self) -> bool:
        return self._cursor > 0

    def can_redo(self) -> bool:
        return self._cursor < len(self.steps)

    def undo(self) -> Step | None:
        if not self.can_undo():
            return None
        self._cursor -= 1
        return self.steps[self._cursor]

    def redo(self) -> Step | None:
        if not self.can_redo():
            return None
        step = self.steps[self._cursor]
        self._cursor += 1
        return step

    def clear(self) -> None:
        self.steps.clear()
        self._cursor = 0


def humanize(method_name: str) -> str:
    """"set_keyframes" -> "Set keyframes" for the Edit menu and palette."""
    words = method_name.replace("_", " ").split()
    if words and words[0]:
        words[0] = words[0].capitalize()
    return " ".join(words) or method_name
