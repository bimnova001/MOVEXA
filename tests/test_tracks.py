"""Hybrid evaluation: object snapshot + camera state at a frame."""

import pytest

from engine.tracks import CameraState, camera_state, object_snapshot
from project.schema import Keyframe, Scene, SceneObject


def test_static_object_snapshot_matches_fields():
    obj = SceneObject(id="o", x=11.0, y=22.0, rotation=33.0,
                      scale_x=0.5, scale_y=1.5, opacity=0.8)
    snap = object_snapshot(obj, 10)
    assert (snap.x, snap.y, snap.rotation) == (11.0, 22.0, 33.0)
    assert (snap.scale_x, snap.scale_y, snap.opacity) == (0.5, 1.5, 0.8)


def test_track_overrides_only_tracked_property():
    obj = SceneObject(id="o", x=0.0, y=7.0)
    obj.tracks["x"] = [Keyframe(0, 100.0), Keyframe(20, 200.0)]
    snap = object_snapshot(obj, 10)
    assert snap.x == pytest.approx(150.0)   # animated
    assert snap.y == 7.0                     # static field untouched


def test_clearing_track_restores_static_value():
    """Stripping animation data must not strand a zombie position."""
    obj = SceneObject(id="o", x=-5.0)
    obj.tracks["x"] = [Keyframe(0, 500.0)]
    assert object_snapshot(obj, 3).x == 500.0
    obj.tracks.clear()
    assert object_snapshot(obj, 3).x == -5.0


def test_visibility_is_static_not_animated():
    obj = SceneObject(id="o", visible=False)
    assert object_snapshot(obj, 5).visible is False


def test_camera_defaults_center_the_stage():
    scene = Scene(id="s")
    state = camera_state(scene, 0, 1920, 1080)
    assert state == CameraState(x=960.0, y=540.0, zoom=1.0)


def test_camera_track_evaluation():
    scene = Scene(id="s")
    scene.camera_tracks["zoom"] = [Keyframe(0, 1.0), Keyframe(30, 2.0)]
    scene.camera_tracks["x"] = [Keyframe(0, 960.0), Keyframe(30, 800.0)]
    mid = camera_state(scene, 15, 1920, 1080)
    assert mid.zoom == pytest.approx(1.5)
    assert mid.x == pytest.approx(880.0)
    assert mid.y == 540.0


def test_camera_zoom_never_reaches_zero():
    scene = Scene(id="s")
    scene.camera_tracks["zoom"] = [Keyframe(0, 0.0)]
    assert camera_state(scene, 0, 1920, 1080).zoom == 0.01
