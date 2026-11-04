"""Undo/redo snapshot history through the controller (Qt-free)."""

import pytest

from app.controller import AppController


@pytest.fixture()
def controller(tmp_path):
    controller = AppController()
    controller.new_project(tmp_path / "UndoProject", "Undo")
    return controller


def test_snapshot_history_round_trips(controller):
    scene_id = controller.current_scene_id
    box = controller.add_object(scene_id, type="rect", x=500, y=400)
    controller.update_object(scene_id, box.id, x=800)
    assert controller.project.scene_by_id(scene_id).object_by_id(box.id).x == 800

    assert controller.undo() == "Update object"
    assert controller.project.scene_by_id(scene_id).object_by_id(box.id).x == 500

    assert controller.redo() == "Update object"
    assert controller.project.scene_by_id(scene_id).object_by_id(box.id).x == 800


def test_add_then_undo_removes_object(controller):
    scene_id = controller.current_scene_id
    box = controller.add_object(scene_id, type="rect")
    assert len(controller.project.scene_by_id(scene_id).objects) == 1
    controller.undo()
    assert controller.project.scene_by_id(scene_id).objects == []
    assert controller.selected_object_id is None
    controller.redo()
    assert controller.project.scene_by_id(scene_id).object_by_id(box.id)


def test_undo_stacks_multiple_steps(controller):
    scene_id = controller.current_scene_id
    controller.add_object(scene_id, type="rect")
    controller.add_object(scene_id, type="text")
    controller.update_scene_metadata(scene_id, name="Renamed")
    assert controller.project.scene_by_id(scene_id).name == "Renamed"
    controller.undo()
    assert controller.project.scene_by_id(scene_id).name == "Scene 1"
    controller.undo()
    assert len(controller.project.scene_by_id(scene_id).objects) == 1
    controller.undo()
    assert controller.project.scene_by_id(scene_id).objects == []


def test_new_mutation_discards_redo_branch(controller):
    scene_id = controller.current_scene_id
    controller.add_object(scene_id, type="rect")
    controller.undo()
    assert controller.undo_stack.can_redo()
    controller.add_object(scene_id, type="text")
    assert not controller.undo_stack.can_redo()


def test_nested_call_counts_as_one_step(controller, tmp_path):
    from PIL import Image
    image_path = tmp_path / "NestedProject" / "pic.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), (10, 90, 200)).save(image_path)
    asset = controller.import_asset(image_path)
    controller.add_object_from_asset(controller.current_scene_id, asset.id)
    scene_id = controller.current_scene_id
    scene = controller.project.scene_by_id(scene_id)
    assert any(o.type == "image" for o in scene.objects)

    # One user action (asset -> object) must be exactly one undo step.
    controller.undo()
    assert controller.project.scene_by_id(scene_id).objects == []


def test_project_lifecycle_clears_history(controller, tmp_path):
    controller.add_object(controller.current_scene_id, type="rect")
    controller.close_project()
    assert not controller.undo_stack.can_undo()
    other = AppController()
    other.new_project(tmp_path / "SecondProject", "Second")
    other.add_object(other.current_scene_id, type="rect")
    assert other.undo_stack.can_undo()
    other.undo_stack.clear()
    assert not other.undo_stack.can_undo()


def test_undo_is_noop_without_project(controller):
    controller.close_project()
    assert controller.undo() is None
    assert controller.redo() is None
