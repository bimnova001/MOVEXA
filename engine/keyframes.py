"""Keyframe interpolation (architecture doc 7.4).

Pure functions of (keyframes, frame). Same data + same frame always yields
the same value - the renderer and the preview share this file, so a frame
evaluated live must match the frame the exporter renders.
"""

from __future__ import annotations

import math
from typing import Callable

from project.schema import Keyframe

# t is the normalized position in [0, 1] within one keyframe interval.
EASINGS: dict[str, Callable[[float], float]] = {
    "step": lambda t: 1.0 if t >= 1.0 else 0.0,
    "linear": lambda t: t,
    "ease_in": lambda t: t * t,
    "ease_out": lambda t: t * (2.0 - t),
    "ease_in_out": lambda t: t * t * (3.0 - 2.0 * t),
}


def evaluate_keyframes(
    keyframes: list[Keyframe], frame: int, fallback: float
) -> float:
    """Value at *frame*; outside the range the edge keyframe value holds.

    An empty track yields *fallback* so callers can always evaluate without
    probing for track existence first.
    """
    if not keyframes:
        return fallback
    if frame <= keyframes[0].frame:
        return keyframes[0].value
    if frame >= keyframes[-1].frame:
        return keyframes[-1].value

    lower, upper = keyframes[0], keyframes[0]
    for kf in keyframes:
        if kf.frame > frame:
            upper = kf
            break
        lower = kf
    span = upper.frame - lower.frame
    t = (frame - lower.frame) / span
    easing = EASINGS.get(lower.easing, EASINGS["linear"])
    value = lower.value + (upper.value - lower.value) * easing(t)
    # Interpolation must never produce NaN/inf: downstream consumers (camera
    # zoom, opacity) can clamp but cannot recover from a poisoned float.
    return 0.0 if not math.isfinite(value) else value
