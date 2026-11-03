"""Controller-level hybrid engine ops: rigs, actions, camera follow, transitions.

GUI-free like the rest of the controller suite.
"""

import pytest

from app.controller import AppController
from engine.character_rig import rig_joints
from engine.tracks import camera_state
from project.schema import validate_project


@pytest.fixture
def controller(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return AppController()


@pytest.fixture
def proj(controller, tmp_path):
    return controller.new_project(tmp_path / "p", "P")


def test_create_character_rig_selects_and_parents(controller, proj):
    root = controller.create_character_rig(controller.current_scene_id)
    scene = controller.project.scene_by_id(controller.current_scene_id)
    assert controller.selected_object_id == root.id
    assert len(scene.objects) == 6
    assert all(o.parent_id == root.id for o in scene.objects if o is not root)


def test_apply_action_walk_via_controller(controller, proj):
    root = controller.create_character_rig(controller.current_scene_id)
    scene = controller.project.scene_by_id(controller.current_scene_id)
    controller.apply_action(controller.current_scene_id, root.id,
                            "walk", 10, 100)
    joints = rig_joints(scene, root.extras["rig"]["id"])
    leg_tracks = [joints["leg_l"].tracks["rotation"], joints["leg_r"].tracks["rotation"]]
    for track in leg_tracks:
        assert track and 10 <= track[0].frame and track[-1].frame <= 100


def test_apply_action_invalid_window_raises(controller, proj):
    box = controller.add_object(controller.current_scene_id, type="rect")
    with pytest.raises(ValueError):
        controller.apply_action(controller.current_scene_id, box.id,
                                "spin", 0, 10_000)


def test_camera_follow_pins_to_object_position(controller, proj):
    scene_id = controller.current_scene_id
    box = controller.add_object(scene_id, type="rect", x=400, y=300)
    scene = controller.project.scene_by_id(scene_id)
    # Walkssample: linear motion keys on the object so camera tracks it.
    controller.set_keyframes(scene_id, box.id, 0, {"x": 400.0})
    controller.set_keyframes(scene_id, box.id, 90, {"x": 1300.0})

    controller.set_camera_follow(scene_id, box.id, 0, 90)
    assert validate_project(controller.project) == []

    camera_0 = camera_state(scene, 0, 1920, 1080)
    camera_end = camera_state(scene, 90, 1920, 1080)
    assert camera_0.x == pytest.approx(400.0)
    assert camera_end.x == pytest.approx(1300.0)


def test_camera_follow_rejects_bad_window(controller, proj):
    box = controller.add_object(controller.current_scene_id, type="rect")
    with pytest.raises(ValueError):
        controller.set_camera_follow(controller.current_scene_id, box.id, 50, 50)


def test_scene_transition_metadata_roundtrip(controller, proj, tmp_path):
    scene_id = controller.current_scene_id
    controller.add_scene("Second")
    controller.update_scene_metadata(scene_id, transition="crossfade",
                                     transition_frames=30)
    project = controller.project
    scene = project.scene_by_id(scene_id)
    assert scene.transition == "crossfade" and scene.transition_frames == 30
    assert validate_project(project) == []


def test_scene_transition_unknown_rejected(controller, proj):
    with pytest.raises(ValueError, match="unknown transition"):
        controller.update_scene_metadata(
            controller.current_scene_id, transition="spin")


def test_rig_preserved_through_save_reload(controller, proj, tmp_path):
    controller.create_character_rig(controller.current_scene_id)
    controller.save()
    controller.open_project(tmp_path / "p")
    reloaded = controller.project
    rig_objs = [o for o in reloaded.scenes[0].objects if o.extras.get("rig")]
    assert len(rig_objs) == 6
    roles = {o.extras["rig"]["role"] for o in rig_objs}
    assert roles == {"root", "head", "arm_l", "arm_r", "leg_l", "leg_r"}
    # Pivots survive too
    arms = [o for o in rig_objs if o.extras["rig"]["role"] == "arm_l"]
    assert arms[0].pivot_y < 0
