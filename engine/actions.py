"""Procedural actions: controlled instructions sampled into keyframes
(architecture doc 7.2).

Sampling writes ordinary Keyframes into schema tracks, so nothing here
executes generated code, storage stays flat JSON, and every frame evaluates
through the same deterministic path as hand-set keys.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from engine.character_rig import rig_joints
from engine.scene_graph import build_scene_graph
from engine.tracks import ObjectSnapshot, object_snapshot
from project.schema import Keyframe, Scene, SceneObject

# (label, needs a character rig) - the UI reads this tuple as the single
# source of truth for what is offered, so UI never drifts from the engine.
ACTIONS: tuple[tuple[str, bool], ...] = (
    ("spin", False),
    ("fade_in", False),
    ("fade_out", False),
    ("bob", False),
    ("idle", True),
    ("walk", True),
    ("wave", True),
    ("jump", True),
)

_INTERVALS_PER_SECOND = 12  # keyframe density for organic curves


def sample_frames(start: int, end: int, fps: int) -> list[int]:
    """Inclusive integer frames at a fixed sampling cadence."""
    step = max(1, fps // _INTERVALS_PER_SECOND)
    frames = list(range(start, end + 1, step))
    if frames[-1] != end:
        frames.append(end)
    return frames


def _pin(track: list[Keyframe], frame: int, value: float,
         easing: str = "linear") -> None:
    kept = [kf for kf in track if kf.frame != frame]
    kept.append(Keyframe(frame=frame, value=value, easing=easing))
    kept.sort(key=lambda kf: kf.frame)
    track[:] = kept


def _pin_track(obj: SceneObject, prop: str, frame: int, value: float,
               easing: str = "linear") -> None:
    _pin(obj.tracks.setdefault(prop, []), frame, value, easing)


def _sine_track(obj: SceneObject, prop: str, start: int, end: int,
                fps: int, base: float, amplitude: float,
                period_frames: float) -> None:
    """base + amp*sin sampled over the window; deterministic per frame."""
    track = obj.tracks.setdefault(prop, [])
    for frame in sample_frames(start, end, fps):
        phase = 2.0 * math.pi * (frame - start) / period_frames
        _pin(track, frame, base + amplitude * math.sin(phase))


@dataclass(frozen=True)
class ActionContext:
    """Everything a handler is allowed to touch - no globals, no state."""

    scene: Scene
    target: SceneObject          # object the action applies to (rig root for rigs)
    joints: dict[str, SceneObject]
    start: int
    end: int
    fps: int
    base: ObjectSnapshot         # target's evaluated state at frame `start`

    # Stage metrics for proportional sizes (e.g. jump height).
    stage_width: float = 1920.0
    stage_height: float = 1080.0

    def scale_unit(self) -> float:
        return self.stage_height / 1080.0


def _do_spin(ctx: ActionContext) -> None:
    _pin_track(ctx.target, "rotation", ctx.start, ctx.base.rotation, "ease_in_out")
    _pin_track(ctx.target, "rotation", ctx.end, ctx.base.rotation + 360.0)


def _do_fade_in(ctx: ActionContext) -> None:
    _pin_track(ctx.target, "opacity", ctx.start, 0.0, "ease_out")
    _pin_track(ctx.target, "opacity", ctx.end, ctx.base.opacity)


def _do_fade_out(ctx: ActionContext) -> None:
    _pin_track(ctx.target, "opacity", ctx.start, ctx.base.opacity, "ease_in")
    _pin_track(ctx.target, "opacity", ctx.end, 0.0)


def _do_bob(ctx: ActionContext) -> None:
    _sine_track(ctx.target, "y", ctx.start, ctx.end, ctx.fps,
                ctx.base.y, 90.0 * ctx.scale_unit(), max(2.0, ctx.fps * 2.0))


def _do_idle(ctx: ActionContext) -> None:
    # Breathing body + slight arm sway around each arm's anchor.
    _sine_track(ctx.target, "y", ctx.start, ctx.end, ctx.fps,
                ctx.base.y, 6.0 * ctx.scale_unit(), max(2.0, ctx.fps * 4.0))
    for role, offset in (("arm_l", 6.0), ("arm_r", -6.0)):
        arm = ctx.joints.get(role)
        if arm is None:
            continue
        base = object_snapshot(arm, ctx.start).rotation + offset
        _sine_track(arm, "rotation", ctx.start, ctx.end, ctx.fps,
                    base, 6.0 * ctx.scale_unit(), max(2.0, ctx.fps * 4.0))


def _do_walk(ctx: ActionContext) -> None:
    """Alternating stride; body bobs twice per cycle, drifts forward.

    One stride = 2 s. Joint bases are captured at the action start so walk
    can be stacked after any prior pose without teleporting limbs.
    """
    period = ctx.fps * 2.0
    swing = {
        "leg_l": 24.0, "leg_r": -24.0,
        "arm_l": -14.0, "arm_r": 14.0,
    }
    for role, amplitude in swing.items():
        joint = ctx.joints.get(role)
        if joint is None:
            continue
        base = object_snapshot(joint, ctx.start).rotation + amplitude
        _sine_track(joint, "rotation", ctx.start, ctx.end, ctx.fps,
                    base, amplitude, max(2.0, period))
    body = ctx.joints.get("body")
    if body is not None:
        _sine_track(body, "y", ctx.start, ctx.end, ctx.fps,
                    ctx.base.y, 5.0 * ctx.scale_unit(), max(2.0, period / 2.0))


def _do_wave(ctx: ActionContext) -> None:
    arm = ctx.joints.get("arm_r")
    if arm is None:
        return
    lift = object_snapshot(arm, ctx.start).rotation + 110.0
    _sine_track(arm, "rotation", ctx.start, ctx.end, ctx.fps,
                lift, 18.0 * ctx.scale_unit(), max(2.0, ctx.fps * 1.5))


def _do_jump(ctx: ActionContext) -> None:
    """Crouch -> leap -> land; legs tuck mid-air."""
    half = (ctx.start + ctx.end) // 2
    unit = ctx.scale_unit()
    _pin_track(ctx.target, "y", ctx.start, ctx.base.y, "ease_out")
    _pin_track(ctx.target, "y", half, ctx.base.y - 180.0 * unit, "ease_out")
    _pin_track(ctx.target, "y", ctx.end, ctx.base.y, "ease_in")
    for role in ("leg_l", "leg_r"):
        leg = ctx.joints.get(role)
        if leg is None:
            continue
        base = object_snapshot(leg, ctx.start).rotation
        _pin_track(leg, "rotation", ctx.start, base, "ease_out")
        _pin_track(leg, "rotation", half, base + 30.0)
        _pin_track(leg, "rotation", ctx.end, base, "ease_in")


_HANDLERS: dict[str, Callable[[ActionContext], None]] = {
    "spin": _do_spin,
    "fade_in": _do_fade_in,
    "fade_out": _do_fade_out,
    "bob": _do_bob,
    "idle": _do_idle,
    "walk": _do_walk,
    "wave": _do_wave,
    "jump": _do_jump,
}

_RIG_ONLY = {"idle", "walk", "wave", "jump"}


def apply_action(
    scene: Scene, target: SceneObject, action: str,
    start: int, end: int, fps: int,
    stage_width: float = 1920.0, stage_height: float = 1080.0,
) -> None:
    """Validate then execute *action*; ValueError carries UI-facing reasons."""
    if action not in _HANDLERS:
        raise ValueError(f"unsupported action: {action}")
    if start >= end:
        raise ValueError("action needs start < end (frames)")
    if start < 0 or end >= scene.duration_frames:
        raise ValueError("action frames outside the scene duration")

    joints: dict[str, SceneObject] = {}
    if action in _RIG_ONLY:
        rig_id = target.extras.get("rig", {}).get("id", "")
        joints = rig_joints(scene, rig_id)
        if not joints:
            raise ValueError(f"action {action!r} needs a character rig")

    ctx = ActionContext(
        scene=scene, target=target, joints=joints,
        start=int(start), end=int(end), fps=int(fps),
        base=object_snapshot(target, int(start)),
        stage_width=stage_width, stage_height=stage_height,
    )
    _HANDLERS[action](ctx)


def rig_targets(scene: Scene) -> list[tuple[str, str, str]]:
    """(object id, object name, rig id) for every rig root in the scene."""
    found: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    try:
        roots = build_scene_graph(scene)
    except ValueError:
        return found
    for root in roots:
        for node in root.iterate():
            info = node.object.extras.get("rig")
            if info and info.get("id") not in seen:
                seen.add(info["id"])
                found.append((node.object.id, node.object.name, info["id"]))
    return found
