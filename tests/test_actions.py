"""Procedural actions sampled into keyframes; validation and window bounds."""

import pytest

from engine.actions import ACTIONS, apply_action, sample_frames
from engine.character_rig import build_human_rig
from project.schema import Scene, SceneObject


@pytest.fixture()
def scene() -> Scene:
    return Scene(id="sc_1", name="S", duration_frames=120)


@pytest.fixture()
def box(scene) -> SceneObject:
    obj = SceneObject(id="o1", name="box", type="rect", x=100, y=200,
                      opacity=0.8, rotation=10)
    scene.objects.append(obj)
    return obj


def test_sample_frames_includes_endpoints():
    frames = sample_frames(0, 60, 30)
    assert frames[0] == 0 and frames[-1] == 60
    assert frames == sorted(frames)


def test_spin_writes_rotation_keys_inside_window(scene, box):
    apply_action(scene, box, "spin", 10, 70, 30)
    keys = box.tracks["rotation"]
    assert [kf.frame for kf in keys] == [10, 70]
    assert keys[-1].value == pytest.approx(10.0 + 360.0)  # base + full turn


def test_fade_out_bounds_opacity(scene, box):
    apply_action(scene, box, "fade_out", 0, 60, 30)
    keys = box.tracks["opacity"]
    assert keys[0].frame == 0 and keys[0].value == pytest.approx(0.8)
    assert keys[-1].frame == 60 and keys[-1].value == pytest.approx(0.0)


def test_fade_in_starts_transparent_ends_at_prior_opacity(scene, box):
    apply_action(scene, box, "fade_in", 5, 55, 30)
    keys = box.tracks["opacity"]
    assert keys[0].value == pytest.approx(0.0)
    assert keys[-1].value == pytest.approx(0.8)


def test_bob_keeps_phase_deterministic(scene, box):
    apply_action(scene, box, "bob", 0, 60, 30)
    ys = {kf.frame: kf.value for kf in box.tracks["y"]}
    # Sine centered on the base y: the start frame sits exactly mid-range.
    assert ys[0] == pytest.approx(200.0)
    # Sampled extrema land within a step of the true sine bounds.
    assert 110.0 < min(ys.values()) <= 113.0
    assert 287.0 <= max(ys.values()) < 290.0


def test_unknown_action_rejected(scene, box):
    with pytest.raises(ValueError, match="unsupported action"):
        apply_action(scene, box, "explode", 0, 50, 30)


def test_bad_window_rejected(scene, box):
    with pytest.raises(ValueError, match="start < end"):
        apply_action(scene, box, "spin", 50, 50, 30)
    with pytest.raises(ValueError, match="outside the scene"):
        apply_action(scene, box, "spin", 100, 130, 30)


def test_rig_action_on_plain_object_rejected(scene, box):
    with pytest.raises(ValueError, match="needs a character rig"):
        apply_action(scene, box, "walk", 0, 60, 30)


def test_walk_cycles_legs_in_antiphase(scene):
    build_human_rig(scene, "Hero", 1920, 1080)
    root = next(o for o in scene.objects if o.extras["rig"]["role"] == "root")
    apply_action(scene, root, "walk", 10, 100, 30)
    from engine.character_rig import rig_joints
    joints = rig_joints(scene, root.extras["rig"]["id"])
    l_vals = {kf.frame: kf.value for kf in joints["leg_l"].tracks["rotation"]}
    r_vals = {kf.frame: kf.value for kf in joints["leg_r"].tracks["rotation"]}
    assert set(l_vals) == set(r_vals)
    # Same sine sampled for both legs with reversed amplitude: strictly
    # antiphase at every frame.
    assert all(l_vals[f] == -r_vals[f] for f in l_vals)
    assert all(10 <= f <= 100 for f in l_vals)  # confined to the window


def test_keys_stay_outside_window_untouched(scene, box):
    apply_action(scene, box, "spin", 10, 70, 30)
    assert max(kf.frame for kf in box.tracks["rotation"]) == 70


def test_actions_catalog_matches_ui_expectations():
    assert dict(ACTIONS)["walk"] is True
    assert dict(ACTIONS)["spin"] is False


def test_snapshot_base_after_prior_keys(scene, box):
    """fade_out stacks on whatever opacity is evaluated at the start frame."""
    apply_action(scene, box, "fade_in", 0, 30, 30)
    apply_action(scene, box, "fade_out", 60, 90, 30)
    keys = box.tracks["opacity"]
    start_val = next(kf.value for kf in keys if kf.frame == 60)
    assert start_val == pytest.approx(0.8)  # unaffected by earlier fade keys
