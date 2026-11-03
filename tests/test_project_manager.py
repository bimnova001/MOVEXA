"""Project manager: create, atomic save, lossless reload, recents."""

import json

import pytest

from project.schema import Project, Scene, SceneObject
from project.manager import ProjectManager


def test_create_project_writes_layout(tmp_path):
    manager = ProjectManager()
    project = manager.create_project(tmp_path / "My Show", "My Show")
    root = tmp_path / "My Show"
    assert (root / "project.json").is_file()
    for sub in ("assets", "scenes", "exports", "assets/backgrounds", "assets/audio"):
        assert (root / sub).is_dir()
    data = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert data["project_id"] == project.project_id
    assert data["name"] == "My Show"
    assert data["settings"] == {"width": 1920, "height": 1080, "fps": 30}


def test_create_refuses_existing_project(tmp_path):
    manager = ProjectManager()
    manager.create_project(tmp_path, "A")
    with pytest.raises(FileExistsError):
        manager.create_project(tmp_path, "B")


def test_missing_project_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        ProjectManager().open_project(tmp_path)


def test_save_reload_round_trip(tmp_path):
    manager = ProjectManager()
    project = manager.create_project(tmp_path, "Round trip")
    scene = Scene(id="scene_x", name="First", duration_frames=90)
    scene.objects.append(SceneObject(id="obj_a", name="Dot", type="ellipse",
                                     x=100.5, y=-3.5, opacity=0.4))
    project.scenes.append(scene)
    manager.save()

    reopened = ProjectManager().open_project(tmp_path)
    obj = reopened.scene_by_id("scene_x").object_by_id("obj_a")
    assert obj.x == 100.5 and obj.y == -3.5 and obj.opacity == 0.4
    assert opened_matches_input(reopened, scenes=1, assets=0)


def opened_matches_input(project: Project, scenes: int, assets: int) -> bool:
    return len(project.scenes) == scenes and len(project.assets) == assets


def test_save_is_atomic_no_tmp_leftover(tmp_path):
    manager = ProjectManager()
    manager.create_project(tmp_path, "Atomic")
    manager.save()
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_unknown_fields_preserved_through_reload(tmp_path):
    manager = ProjectManager()
    manager.create_project(tmp_path, "Future proof")
    with open(tmp_path / "project.json", encoding="utf-8") as fh:
        data = json.load(fh)
    data["experimental_engine"] = {"quantum": True}
    data["scenes"] = [{
        "id": "scene_f1", "name": "Futuristic", "duration_frames": 60,
        "volumetric_fx": True, "objects": [],
    }]
    with open(tmp_path / "project.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh)

    reopened = ProjectManager().open_project(tmp_path)
    assert reopened.extras["experimental_engine"] == {"quantum": True}
    assert reopened.scene_by_id("scene_f1").extras["volumetric_fx"] is True
    reopened.name = "Renamed"
    manager.current, manager.current_dir = reopened, tmp_path
    manager.save()
    with open(tmp_path / "project.json", encoding="utf-8") as fh:
        saved = json.load(fh)
    assert saved["experimental_engine"] == {"quantum": True}
    assert saved["name"] == "Renamed"


def test_recents_dedupe_and_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    manager = ProjectManager()
    manager.create_project(tmp_path / "p1", "one")
    manager.create_project(tmp_path / "p2", "two")
    manager.add_recent(tmp_path / "p1")  # duplicate of create's entry
    recents = manager.add_recent(tmp_path / "p1")
    assert recents.count(str((tmp_path / "p1").resolve())) == 1
    assert len(recents) <= 10


def test_recents_drop_missing_projects(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    manager = ProjectManager()
    manager.add_recent(tmp_path / "gone1")
    manager.create_project(tmp_path / "alive", "alive")
    recents = ProjectManager().load_recent()
    assert recents == [str((tmp_path / "alive").resolve())]
