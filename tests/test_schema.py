"""Schema validation + lossless serialization tests."""

from project.schema import (
    AssetInfo,
    Project,
    ProjectSettings,
    Scene,
    SceneObject,
    validate_project,
)


def make_scene(object_id: str = "obj_1") -> Scene:
    return Scene(
        id="scene_1",
        name="Intro",
        duration_frames=150,
        objects=[SceneObject(id=object_id, name="Box", type="rect")],
    )


def make_project() -> Project:
    settings = ProjectSettings(width=1920, height=1080, fps=30)
    return Project(
        project_id="project_abc123",
        name="Demo",
        settings=settings,
        assets=[],
        scenes=[make_scene()],
    )


def test_valid_project_has_no_problems():
    assert validate_project(make_project()) == []


def test_unknown_parent_flagged():
    project = make_project()
    project.scenes[0].objects[0].parent_id = "obj_ghost"
    errors = validate_project(project)
    assert any("parent" in e for e in errors)


def test_image_without_asset_ref_flagged():
    project = make_project()
    project.scenes[0].objects[0].type = "image"
    project.scenes[0].objects[0].asset_id = None
    errors = validate_project(project)
    assert any("asset" in e.lower() for e in errors)


def test_unknown_asset_ref_flagged():
    project = make_project()
    project.scenes[0].objects[0].type = "image"
    project.scenes[0].objects[0].asset_id = "asset_missing"
    errors = validate_project(project)
    assert any("asset_missing" in e for e in errors)


def test_duplicate_ids_flagged():
    project = make_project()
    project.scenes[0].objects.append(
        SceneObject(id="obj_1", name="Also box", type="rect"))
    errors = validate_project(project)
    assert any("object" in e for e in errors)


def test_bad_values_flagged():
    project = make_project()
    project.settings.width = -1
    project.settings.fps = 0
    project.scenes[0].duration_frames = 0
    project.scenes[0].objects[0].opacity = 1.5
    project.scenes[0].objects[0].type = "star"  # not in OBJECT_TYPES
    errors = validate_project(project)
    assert len(errors) == 5


def test_round_trip_is_lossless_for_known_fields():
    project = make_project()
    obj = project.scenes[0].objects[0]
    obj.x, obj.y, obj.rotation, obj.scale_x = 150.5, -42.25, 33.0, 0.8
    data = project.to_data()
    reparsed = Project.from_data(data)
    assert reparsed.scenes[0].objects[0].x == 150.5
    assert reparsed.scenes[0].objects[0].y == -42.25
    assert reparsed.scenes[0].duration_frames == 150
    assert reparsed.settings.width == 1920
    assert len(reparsed.scenes) == len(project.scenes) == 1


def test_unknown_fields_survive_round_trip():
    """Rule: never silently discard unknown or unsupported project data."""
    data = make_project().to_data()
    data["brand_new_field"] = {"supported": "in schema 2.0"}
    data["scenes"][0]["future_scene_meta"] = [1, 2, 3]
    data["assets"] = [{"id": "asset_new", "color_space": "p3", "type": "image",
                       "category": "backgrounds", "relative_path": "a.png"}]
    project = Project.from_data(data)
    saved = project.to_data()
    assert saved["brand_new_field"] == {"supported": "in schema 2.0"}
    assert saved["scenes"][0]["future_scene_meta"] == [1, 2, 3]
    assert saved["assets"][0]["color_space"] == "p3"
    # And the translated known fields still validate.
    assert validate_project(project) == []


def test_assetinfo_round_trip():
    asset = AssetInfo(id="asset_1", name="bg", type="image",
                      category="backgrounds", relative_path="assets/backgrounds/bg.png")
    data = asset.to_data()
    assert AssetInfo.from_data(data) == asset
