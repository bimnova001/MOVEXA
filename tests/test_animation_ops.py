"""Keyframe edits through AppController + schema-level track validation."""

import pytest

from app.controller import AppController
from project.schema import (
    EASING_NAMES,
    Keyframe,
    Project,
    ProjectSettings,
    Scene,
    SceneObject,
    validate_project,
)


@pytest.fixture
def controller(tmp_path):
    return AppController()


def test_set_keyframe_creates_sorted_track(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    obj = controller.add_object(scene_id, type="rect", name="Box", x=100, y=100)
    controller.set_keyframes(scene_id, obj.id, 0, {"x": 100.0})
    controller.set_keyframes(scene_id, obj.id, 30, {"x": 500.0})
    controller.set_keyframes(scene_id, obj.id, 15, {"x": 250.0})
    frames = [kf.frame for kf in obj.tracks["x"]]
    assert frames == sorted(frames) == [0, 15, 30]


def test_set_same_frame_twice_replaces(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    obj = controller.add_object(scene_id, type="rect")
    controller.set_keyframes(scene_id, obj.id, 10, {"x": 1.0})
    controller.set_keyframes(scene_id, obj.id, 10, {"x": 2.0})
    assert len(obj.tracks["x"]) == 1 and obj.tracks["x"][0].value == 2.0


def test_remove_keyframe_at(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    obj = controller.add_object(scene_id, type="rect")
    controller.set_keyframes(scene_id, obj.id, 10, {"x": 1.0, "y": 2.0})
    controller.set_keyframes(scene_id, obj.id, 20, {"x": 5.0})
    removed = controller.remove_keyframe_at(scene_id, obj.id, 10)
    assert removed == 2
    assert [kf.frame for kf in obj.tracks["x"]] == [20]
    # Deleting at a frame without keys removes nothing and stays quiet.
    assert controller.remove_keyframe_at(scene_id, obj.id, 99) == 0


def test_update_animated_property_routes_to_keyframe(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    obj = controller.add_object(scene_id, type="rect", x=10)
    controller.set_keyframes(scene_id, obj.id, 0, {"x": 10.0})
    controller.player.seek(20)
    controller.update_object(scene_id, obj.id, x=77.0)
    # Static field untouched by the edit; the keyframe carries the value.
    assert obj.x == 10.0
    assert [kf.frame for kf in obj.tracks["x"]] == [0, 20]
    assert obj.tracks["x"][1].value == 77.0


def test_clear_tracks(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    obj = controller.add_object(scene_id, type="rect")
    controller.set_keyframes(scene_id, obj.id, 5, {"x": 1.0})
    controller.clear_object_tracks(scene_id, obj.id)
    assert obj.tracks == {}


def test_camera_keyframes(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    controller.set_camera_keyframes(scene_id, 0, {"zoom": 1.0})
    controller.set_camera_keyframes(scene_id, 30, {"zoom": 3.0})
    scene = controller.project.scene_by_id(scene_id)
    assert scene.camera_tracks["zoom"][1].value == 3.0
    controller.clear_camera_tracks(scene_id)
    assert scene.camera_tracks == {}


def test_camera_spin_drops_invalid_props_silently(controller, tmp_path):
    """Only CAMERA_PROPS reach tracks; others are caller errors."""
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    controller.set_camera_keyframes(scene_id, 0, {"opacity": 0.5})
    assert controller.project.scene_by_id(scene_id).camera_tracks == {}


def test_keyframe_ops_publish_scene_updated(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    events = []
    controller.bus.subscribe("scene.updated", events.append)
    scene_id = controller.current_scene_id
    obj = controller.add_object(scene_id, type="rect")
    events.clear()
    controller.set_keyframes(scene_id, obj.id, 0, {"x": 5.0})
    assert events


def test_keyframes_survive_save_reload(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    obj = controller.add_object(scene_id, type="rect", name="Box")
    controller.set_keyframes(scene_id, obj.id, 0, {"x": 100.0})
    controller.set_keyframes(scene_id, obj.id, 30, {"x": 400.0, "opacity": 1.0})
    controller.set_camera_keyframes(scene_id, 30, {"zoom": 2.0})
    controller.save()

    fresh = AppController()
    reopened = fresh.open_project(tmp_path / "p")
    scene = reopened.scene_by_id(scene_id)
    box = scene.object_by_id(obj.id)
    assert [kf.frame for kf in box.tracks["x"]] == [0, 30]
    assert box.tracks["x"][1].value == 400.0
    assert scene.camera_tracks["zoom"][0].value == 2.0
    assert validate_project(reopened) == []


class TestSchemaValidation:
    @staticmethod
    def project_with(track_map) -> list[str]:
        scene = Scene(id="s1")
        scene.objects.append(
            SceneObject(id="o1", **{"tracks": track_map}))
        return validate_project(Project(
            project_id="p1", settings=ProjectSettings(), scenes=[scene]))

    def test_valid_track_passes(self):
        assert self.project_with({
            "x": [Keyframe(0, 1.0), Keyframe(15, 2.0)]}) == []

    def test_unknown_prop_flagged(self):
        assert any("track" in e for e in self.project_with(
            {"warp": [Keyframe(0, 1.0)]}))

    def test_unknown_easing_flagged(self):
        assert any("easing" in e for e in self.project_with(
            {"x": [Keyframe(0, 1.0, easing="sine")]}))

    def test_negative_frame_flagged(self):
        assert any("keyframe" in e for e in self.project_with(
            {"x": [Keyframe(-3, 1.0)]}))

    def test_unsorted_flagged(self):
        assert any("ordered" in e for e in self.project_with(
            {"x": [Keyframe(30, 1.0), Keyframe(10, 2.0)]}))

    def test_duplicate_frames_indexed_out(self):
        same_frame = {"x": ([Keyframe(5, 1.0), Keyframe(5, 2.0)])}
        # Parser dedupes at load; raw duplicates here are separate keys in a
        # list tie: validation only rejects non-increasing pairs.
        assert any("ordered" in e for e in self.project_with(same_frame))


class TestLosslessTracks:
    def test_unknown_track_props_survive_round_trip(self):
        obj = SceneObject(id="o1")
        obj.tracks = {"x": [Keyframe(0, 1.0)]}
        data = obj.to_data()
        data["tracks"]["gravity"] = [
            {"frame": 0, "value": 9.8, "strength": 2.0}]
        reparsed = SceneObject.from_data(data)
        assert reparsed.tracks["x"] == [Keyframe(0, 1.0)]
        pulled = reparsed.extras["tracks"]["gravity"]
        assert pulled[0].extras["strength"] == 2.0
        # Unknown props must be the only complaint the validator has.
        errors = _wrap(reparsed)
        assert [e for e in errors if "gravity" not in e] == []

    def test_wrapped_track_form_round_trips(self):
        obj = SceneObject(id="o1")
        obj.tracks = {"y": [Keyframe(10, 3.0)]}
        data = obj.to_data()
        data["tracks"]["y"] = {"keyframes": data["tracks"]["y"],
                               "loop": "pingpong"}
        reparsed = SceneObject.from_data(data)
        assert reparsed.tracks["y"] == [Keyframe(10, 3.0)]
        assert reparsed.extras.get("tracks", {}).get("y", {}).get("loop") == "pingpong"


def _wrap(obj: SceneObject) -> list[str]:
    scene = Scene(id="s1", objects=[obj])
    return validate_project(
        Project(project_id="p1", settings=ProjectSettings(), scenes=[scene]))


def test_constants_align_with_engine():
    from engine.keyframes import EASINGS
    assert set(EASINGS) == set(EASING_NAMES)
