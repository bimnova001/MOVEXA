"""Transition planning: crossfade / dip windows produce stable pass data."""

import pytest

from engine.transitions import transition_plan
from project.schema import Project, Scene, SceneObject, validate_project


def _two_scene_project(a_kwargs: dict, transition: dict) -> Project:
    scene_a = Scene(id="sc_a", name="A", duration_frames=120,
                    objects=[SceneObject(id="o_a", name="a", type="rect")],
                    **a_kwargs)
    scene_b = Scene(id="sc_b", name="B", duration_frames=100,
                    objects=[SceneObject(id="o_b", name="b", type="rect")])
    return (Project(project_id="prj_test", scenes=[scene_a, scene_b]),
            scene_a, scene_b)


def test_no_transition_single_pass():
    project, scene_a, _ = _two_scene_project({}, {"type": "none"})
    plan = transition_plan(project, scene_a, 100)
    assert len(plan.passes) == 1
    assert plan.passes[0].scene is scene_a
    assert plan.passes[0].alpha == pytest.approx(1.0)
    assert plan.black_overlay == 0.0


def test_before_window_single_pass():
    project, scene_a, _ = _two_scene_project(
        {"transition": "crossfade", "transition_frames": 30}, {})
    plan = transition_plan(project, scene_a, 89)
    assert len(plan.passes) == 1
    assert plan.passes[0].scene is scene_a


def test_crossfade_two_passes_alphas_ramp():
    project, scene_a, scene_b = _two_scene_project(
        {"transition": "crossfade", "transition_frames": 30}, {})
    frame = 90 + 15  # half-way through the 90..119 window
    plan = transition_plan(project, scene_a, frame)
    assert [p.scene for p in plan.passes] == [scene_a, scene_b]
    alphas = [p.alpha for p in plan.passes]
    assert alphas[0] == pytest.approx(0.5)
    assert alphas[1] == pytest.approx(0.5)
    # Incoming scene is evaluated at its own local time.
    assert plan.passes[1].frame == 15


def test_crossfade_incoming_frame_clamped():
    project, scene_a, scene_b = _two_scene_project(
        {"transition": "crossfade", "transition_frames": 40}, {})
    plan = transition_plan(project, scene_a, 110)
    assert plan.passes[1].frame == 30  # elapsed frames into the next scene


def test_crossfade_incoming_frame_never_exceeds_short_scene():
    scene_a = Scene(id="sc_a", name="A", duration_frames=120,
                    transition="crossfade", transition_frames=40)
    scene_b = Scene(id="sc_b", name="B", duration_frames=10)
    project = Project(project_id="prj_t", scenes=[scene_a, scene_b])
    # 30 frames elapsed in a 10-frame scene clamps to its last frame.
    plan = transition_plan(project, scene_a, 110)
    assert plan.passes[1].frame == 9


def test_dip_second_half_overlay_full_and_reveal():
    project, scene_a, scene_b = _two_scene_project(
        {"transition": "dip_black", "transition_frames": 20}, {})
    plan = transition_plan(project, scene_a, 115)  # 75% through the window
    assert plan.black_overlay == pytest.approx(1.0)
    assert plan.passes[1].alpha == pytest.approx(0.5)


def test_dip_overlay_zero_at_window_start():
    project, scene_a, _ = _two_scene_project(
        {"transition": "dip_black", "transition_frames": 20}, {})
    plan = transition_plan(project, scene_a, 100)
    assert plan.black_overlay == pytest.approx(0.0)
    assert len(plan.passes) == 1


def test_dip_last_frame_nearly_revealed():
    project, scene_a, _ = _two_scene_project(
        {"transition": "dip_black", "transition_frames": 20}, {})
    plan = transition_plan(project, scene_a, 119)
    assert plan.black_overlay == pytest.approx(1.0)
    assert plan.passes[-1].alpha == pytest.approx(0.9)


def test_transition_metadata_validates():
    project, scene_a, scene_b = _two_scene_project(
        {"transition": "crossfade", "transition_frames": 30}, {})
    assert validate_project(project) == []
    scene_a.transition_frames = scene_a.duration_frames  # must be < duration
    errors = validate_project(project)
    assert any("transition" in e for e in errors)
    scene_a.transition_frames = 30
    scene_a.transition = "spin"
    assert any("unknown scene transition" in e for e in validate_project(project))


def test_last_scene_transition_ignored_in_plan():
    project, _, scene_b = _two_scene_project({}, {})
    scene_b.transition, scene_b.transition_frames = "crossfade", 30
    plan = transition_plan(project, scene_b, 99)
    assert len(plan.passes) == 1 and plan.passes[0].scene is scene_b
