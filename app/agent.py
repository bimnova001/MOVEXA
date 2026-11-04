"""AI agent core (Qt-free): routes editor chat to local edits or providers.

Three paths answer a user line:
- local intent  -> deterministic controller edits (works fully offline)
- outline brief -> provider.generate_text (mock provider gives a deterministic
  offline outline; real providers need an API key in %APPDATA%/movexa)
- scene brief   -> provider.generate_structured + validate + apply

The GUI thread keeps ownership of all controller mutations; provider calls
may run off-thread and hand validated JSON back.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

SHAPE_WORDS = {
    "rect": "add_rect", "rectangle": "add_rect", "box": "add_rect",
    "square": "add_rect", "shape": "add_rect",
    "circle": "add_ellipse", "ellipse": "add_ellipse",
    "text": "add_text", "rig": "add_rig", "character": "add_rig",
}
ACTION_WORDS = ("spin", "bob", "jump", "wave", "walk", "idle", "fade_in", "fade_out")
OUTLINE_WORDS = ("outline", "storyboard", "script", "บท", "เรื่องราว")
SCENE_WORDS = ("scene", "generate scene", "ai scene", "ซีน", "สร้างซีน")


@dataclass
class Intent:
    kind: str
    payload: dict = field(default_factory=dict)


def _parse_position(text: str) -> tuple[float, float] | None:
    match = re.search(r"at\s+(-?\d+(?:\.\d+)?)\s*[,x]\s*(-?\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None


def _parse_color(text: str) -> str | None:
    match = re.search(r"#([0-9a-fA-F]{6})", text)
    return f"#{match.group(1)}" if match else None


def route(text: str) -> tuple[str, object]:
    """Return (route, payload): "local"/Intent, "outline"/brief,
    "scene"/brief, or "help"/None."""
    stripped = text.strip()
    lowered = stripped.lower()

    if not stripped:
        return "help", None

    if lowered.startswith(("add ", "สร้าง", "put ")):
        word, point, color = _shape_word(lowered), _parse_position(lowered), _parse_color(lowered)
        if word == "add_text":
            quoted = re.search(r'"([^"]+)"', stripped)
            text_payload = quoted.group(1)
            if not text_payload:
                after = re.sub(r"^(add|สร้าง|put)\s+(text|ข้อความ)\s*", "", stripped, flags=re.IGNORECASE)
                text_payload = after.strip() if "&#" not in after else ""
            payload = {"text": text_payload}
            if point:
                payload["x"], payload["y"] = point
            if color:
                payload["color"] = color
            return "local", Intent(kind="add_text", payload=payload)
        if word in SHAPE_WORDS.values():
            payload: dict = {}
            if point:
                payload["x"], payload["y"] = point
            if color:
                payload["color"] = color
            return "local", Intent(kind=word, payload=payload)

    for word in ACTION_WORDS:
        if lowered.startswith(word) or lowered.startswith("animate "):
            window = re.search(r"(\d+)\s*(?:-|to|..)\s*(\d+)", lowered)
            start, end = (int(window.group(1)), int(window.group(2))) if window else (0, 90)
            return "local", Intent(kind="animate", payload={
                "action": word if word in ACTION_WORDS else "bob",
                "start": start, "end": end,
            })

    for word in OUTLINE_WORDS:
        brief = _take_after(stripped, (word,))
        if brief is not None:
            return "outline", brief

    if any(word in lowered for word in SCENE_WORDS):
        return "scene", stripped

    return "help", None


def _shape_word(lowered: str) -> str | None:
    for word, kind in SHAPE_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return kind
    return None


def _take_after(text: str, starters: tuple[str, ...]) -> str | None:
    for starter in starters:
        index = text.lower().find(starter)
        if index >= 0:
            rest = text[index + len(starter):].strip(" :–-")
            if rest:
                return rest
    return None


def execute_local(intent: Intent, controller) -> str:
    """Run a local intent through the controller. Returns a chat reply."""
    scene_id = controller.current_scene_id
    if scene_id is None:
        return "Open a project and select a scene first."
    payload = intent.payload
    if intent.kind == "add_rect":
        obj = controller.add_object(scene_id, type="rect",
                                    color=payload.get("color", "#7c4dff"))
    elif intent.kind == "add_ellipse":
        obj = controller.add_object(scene_id, type="ellipse",
                                    color=payload.get("color", "#22d3ee"))
    elif intent.kind == "add_text":
        payload.setdefault("text", "MOVEXA")
        obj = controller.add_object(scene_id, type="text", **payload)
    elif intent.kind == "add_rig":
        obj = controller.create_character_rig(scene_id)
    elif intent.kind == "animate":
        target = controller.selected_object_id
        if target is None:
            return "Select an object on the canvas, then ask again."
        try:
            controller.apply_action(scene_id, target, payload["action"],
                                    payload["start"], payload["end"])
        except (ValueError, KeyError) as exc:
            return f"Cannot apply {payload['action']}: {exc}"
        return (f"{payload['action']} applied over frames "
                f"{payload['start']}..{payload['end']}.")
    else:
        return "Unknown local command."
    position = payload.get("x"), payload.get("y")
    if intent.kind in ("add_rect", "add_ellipse") and position != (None, None):
        controller.update_object(scene_id, obj.id, x=position[0], y=position[1])
    return f"Added {obj.type} '{obj.name}'. Double-click or drag to adjust."


HELP_TEXT = (
    "Try:\n"
    "• “add rect at 600,300” / “add circle” / “add text \"Hello\"”\n"
    "• “spin 0-60” (need a selected object; rig actions need a rig)\n"
    "• “outline: a cat chasing a ball” — covers script/storyboard\n"
    "• “generate a scene: sun rising over hills” — AI builds objects+actions\n\n"
    "Offline mode uses the deterministic Mock provider everywhere; connect a "
    "key in %APPDATA%/movexa/ai_settings.json to unlock real models."
)


def parse_payload(raw: str) -> dict | None:
    """Extract a scene JSON object from provider text (tolerates fences)."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        if start >= 0:
            text = text[start:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
