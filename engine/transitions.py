"""Scene transitions (architecture doc: basic transitions, Priority 3).

Pure planning only: given the playing scene and frame, return the ordered
list of (scene, frame, alpha) passes to paint plus an optional black overlay.
The canvas and (later) the frame renderer consume the same plan, so preview
and export stay identical by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

from project.schema import Project, Scene


@dataclass(frozen=True)
class TransitionPass:
    scene: Scene
    frame: int          # frame at which the NEXT scene is evaluated
    alpha: float


@dataclass(frozen=True)
class TransitionPlan:
    passes: tuple[TransitionPass, ...]   # paint order: bottom first
    black_overlay: float = 0.0           # painted after passes[0] if > 0


def transition_plan(
    project: Project, scene: Scene, frame: int
) -> TransitionPlan:
    """Layers for *frame* of *scene*, honoring its transition setting.

    Outside the window the plan is a single fully-opaque pass of the scene
    itself - the common case stays zero-cost.
    """
    next_scene = _next_scene(project, scene)
    if (scene.transition == "none" or scene.transition_frames < 1
            or next_scene is None):
        return TransitionPlan(
            passes=(TransitionPass(scene, frame, 1.0),))

    window = scene.transition_frames
    start = scene.duration_frames - window
    if frame < start:
        return TransitionPlan(passes=(TransitionPass(scene, frame, 1.0),))

    progress = min(1.0, (frame - start) / window)
    reach = min(int(frame - start), next_scene.duration_frames - 1)
    incoming = TransitionPass(next_scene, frame=reach, alpha=progress)
    if scene.transition == "crossfade":
        return TransitionPlan(passes=(
            TransitionPass(scene, frame, 1.0 - progress), incoming))
    # dip_black / dip_white: fade the current scene to the dip color in the
    # first half, then reveal the next scene in the second half.
    if progress <= 0.5:
        return TransitionPlan(passes=(TransitionPass(scene, frame, 1.0),),
                              black_overlay=progress * 2.0)
    return TransitionPlan(
        passes=(TransitionPass(scene, frame, 1.0),
                TransitionPass(next_scene, frame=reach, alpha=(progress - 0.5) * 2.0)),
        black_overlay=1.0)


def _next_scene(project: Project, scene: Scene) -> Scene | None:
    try:
        index = project.scenes.index(scene)
    except ValueError:
        return None
    if index + 1 >= len(project.scenes):
        return None
    return project.scenes[index + 1]
