"""Hybrid evaluation: object + camera state at one integer frame.

Both engines (cut-out rig and procedural) read the same snapshot per frame;
this module is where the two stay in lockstep (architecture doc 7.3).
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.keyframes import evaluate_keyframes
from project.schema import ANIMATABLE_PROPS, Scene, SceneObject


@dataclass(frozen=True)
class ObjectSnapshot:
    """Effective property values of one object at a frame."""

    x: float
    y: float
    rotation: float
    scale_x: float
    scale_y: float
    opacity: float
    visible: bool


def object_snapshot(obj: SceneObject, frame: int) -> ObjectSnapshot:
    """Track values override static fields only where a track exists.

    Static fields stay untouched by evaluation, so clearing a track snaps the
    object back to its stored position - no zombie animation data.
    """
    values = {}
    for prop in ANIMATABLE_PROPS:
        track = obj.tracks.get(prop)
        static = float(getattr(obj, prop))
        values[prop] = evaluate_keyframes(track, frame, static)
    return ObjectSnapshot(visible=obj.visible, **values)


@dataclass(frozen=True)
class CameraState:
    """Camera framing: stage-space center point plus zoom."""

    x: float
    y: float
    zoom: float


def camera_state(
    scene: Scene, frame: int, stage_width: float, stage_height: float
) -> CameraState:
    """Default camera centers the full stage at zoom 1.0."""
    x = evaluate_keyframes(scene.camera_tracks.get("x"), frame, stage_width / 2.0)
    y = evaluate_keyframes(scene.camera_tracks.get("y"), frame, stage_height / 2.0)
    zoom = evaluate_keyframes(scene.camera_tracks.get("zoom"), frame, 1.0)
    # A zero/negative zoom inverts the viewport; degenerate, not artistic.
    return CameraState(x=x, y=y, zoom=max(0.01, zoom))
