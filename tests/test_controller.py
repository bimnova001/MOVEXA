"""AppController integration: the workflow INFO.md section 11 describes.

Project -> scenes -> objects -> assets -> save -> reload. Runs without Qt:
the controller is deliberately GUI-free so these tests need only pytest.
"""

import pytest
from PIL import Image

from app.controller import AppController
from project.schema import validate_project


@pytest.fixture
def controller(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return AppController()


def test_new_project_creates_first_scene_and_saves(controller, tmp_path):
    project = controller.new_project(tmp_path / "demo", "Demo")
    assert len(project.scenes) == 1
    assert controller.current_scene_id == project.scenes[0].id
    data = (tmp_path / "demo" / "project.json").read_text(encoding="utf-8")
    assert "Demo" in data


def test_scene_lifecycle(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    s1 = controller.add_scene("Attack")
    s2 = controller.add_scene("Attack")  # name must uniquify, not collide
    assert s1.name != s2.name
    controller.select_scene(s1.id)
    controller.reorder_scene(s2.id, -1)
    # Order was [Scene 1, s1, s2]; moving s2 one slot back puts it under Scene 1.
    assert controller.project.scenes[1].id == s2.id
    assert controller.project.scenes[2].id == s1.id

    clone = controller.duplicate_scene(s2.id)
    assert clone.name == f"{s2.name} copy"
    assert clone.id != s2.id

    controller.remove_scene(s2.id)
    controller.remove_scene(clone.id)
    # "Scene 1" (created by new_project) + s1 remain.
    assert len(controller.project.scenes) == 2


def test_object_crud_and_parenting(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    torso = controller.add_object(scene_id, type="rect", name="Torso",
                                  x=960, y=540)
    head = controller.add_object(scene_id, type="ellipse", name="Head",
                                 parent_id=torso.id)
    assert head.parent_id == torso.id

    controller.update_object(scene_id, torso.id, x=1000, rotation=15)
    assert torso.x == 1000 and torso.rotation == 15

    controller.update_object(scene_id, torso.id, name="Chest")
    assert torso.name == "Chest"

    # Removing the parent re-parents orphans instead of dropping them.
    controller.remove_object(scene_id, torso.id)
    assert head.parent_id is None
    # The removed object leaves; the still-alive child keeps the selection.
    assert controller.selected_object_id == head.id


def test_object_name_autoincrement(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    first = controller.add_object(scene_id, type="rect", name="Box")
    second = controller.add_object(scene_id, type="rect", name="Box")
    assert first.name == "Box" and second.name == "Box 2"


def test_image_object_from_asset(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    image = tmp_path / "pic.png"
    Image.new("RGB", (800, 400), (10, 200, 90)).save(image, "PNG")
    asset = controller.import_asset(image)
    scene_id = controller.current_scene_id
    obj = controller.add_object_from_asset(scene_id, asset.id)
    assert obj.type == "image" and obj.asset_id == asset.id
    # 800x400 fits into 1920x1080 without upscaling.
    assert obj.scale_x == 1.0
    # Centered on the stage.
    assert (obj.x, obj.y) == (960.0, 540.0)


def test_scene_graph_builds_after_edits(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    parent = controller.add_object(scene_id, type="rect", x=100, y=100)
    child = controller.add_object(scene_id, type="rect", x=50, y=0,
                                  parent_id=parent.id)
    graph = controller.scene_graph(scene_id)
    assert any(node.object.id == child.id and node.parent.object.id == parent.id
               for root in graph for node in root.iterate())


def test_asset_remove_guard_flows_through(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    image = tmp_path / "pic.png"
    Image.new("RGB", (100, 100), (0, 0, 0)).save(image, "PNG")
    asset = controller.import_asset(image)
    scene_id = controller.current_scene_id
    controller.add_object_from_asset(scene_id, asset.id)
    with pytest.raises(RuntimeError):
        controller.remove_asset(asset.id)


def test_save_reload_preserves_everything(controller, tmp_path):
    controller.new_project(tmp_path / "p2", "Persist")
    scene_id = controller.current_scene_id
    parent = controller.add_object(scene_id, type="rect", name="Body",
                                   x=500, y=300)
    controller.add_object(scene_id, type="ellipse", name="Head",
                          parent_id=parent.id)
    image = tmp_path / "b.png"
    Image.new("RGB", (256, 128), (255, 145, 0)).save(image, "PNG")
    asset = controller.import_asset(image, category="backgrounds")
    controller.set_scene_background(scene_id, asset.id)
    controller.save()

    fresh = AppController()
    reopened = fresh.open_project(tmp_path / "p2")
    assert reopened.name == "Persist"
    scene = reopened.scene_by_id(scene_id)
    assert scene.background_asset_id == asset.id
    assert [o.name for o in scene.objects] == ["Body", "Head"]
    assert scene.object_by_id(scene.objects[1].id).parent_id == \
        scene.objects[0].id
    fresh.current_scene_id = scene_id
    assert validate_project(reopened) == []
