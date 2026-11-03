"""Asset manager: import, dedupe by content hash, protected removal."""

import shutil

import pytest
from PIL import Image

from project.assets import AssetManager, detect_type
from project.manager import ProjectManager
from project.schema import Scene, SceneObject

@pytest.fixture
def workspace(tmp_path):
    manager = ProjectManager()
    manager.create_project(tmp_path / "show", "show")
    return manager, AssetManager(manager), tmp_path


def _make_image(path, size=(640, 360), color=(120, 20, 200)):
    Image.new("RGB", size, color).save(path, "PNG")


def test_detect_type():
    assert detect_type(".png") == "image"
    assert detect_type(".MP3") == "audio"
    assert detect_type(".exe") is None


def test_type_detection_file_missing(workspace):
    _manager, assets, tmp_path = workspace
    with pytest.raises(FileNotFoundError):
        assets.import_file(tmp_path / "nothing.png")


def test_unsupported_extension_rejected(workspace):
    _manager, assets, tmp_path = workspace
    bad = tmp_path / "virus.exe"
    bad.write_bytes(b"MZ")
    with pytest.raises(ValueError):
        assets.import_file(bad)


def test_import_image_reads_dimensions(workspace, tmp_path):
    _manager, assets, tmp_path = workspace
    src = tmp_path / "hero.png"
    _make_image(src, size=(640, 360))
    asset = assets.import_file(src, category="characters")
    assert asset.type == "image"
    assert asset.category == "characters"
    assert (asset.width, asset.height) == (640, 360)
    assert asset.size_bytes > 0
    assert assets.exists_on_disk(asset)
    assert asset.relative_path.startswith("assets/characters/")


def test_identical_content_deduplicates(workspace, tmp_path):
    _manager, assets, tmp_path = workspace
    src = tmp_path / "hero.png"
    _make_image(src)
    first = assets.import_file(src)
    copy = tmp_path / "hero_copy.png"
    shutil.copy2(src, copy)
    second = assets.import_file(copy)
    assert first.id == second.id
    assert len(assets.assets()) == 1


def test_different_content_two_assets(workspace, tmp_path):
    _manager, assets, tmp_path = workspace
    _make_image(tmp_path / "a.png", color=(255, 0, 0))
    _make_image(tmp_path / "b.png", color=(0, 0, 255))
    assets.import_file(tmp_path / "a.png")
    assets.import_file(tmp_path / "b.png")
    assert len(assets.assets()) == 2


def test_cannot_remove_referenced_asset(workspace, tmp_path):
    manager, assets, tmp_path = workspace
    _make_image(tmp_path / "bg.png")
    asset = assets.import_file(tmp_path / "bg.png", category="backgrounds")
    project = manager.current
    # Projects start with zero scenes; create one to reference the asset from.
    project.scenes.append(Scene(id="s1", name="S"))
    project.scenes[0].objects.append(
        SceneObject(id="obj_bg", name="bg", type="image", asset_id=asset.id))
    with pytest.raises(RuntimeError):
        assets.remove(asset.id)
    # After the reference disappears removal works.
    project.scenes[0].objects.clear()
    assets.remove(asset.id)
    assert assets.get(asset.id) is None


def test_remove_never_touches_disk(workspace, tmp_path):
    """Removal unregisters the asset but keeps the file for re-add."""
    _manager, assets, tmp_path = workspace
    _make_image(tmp_path / "keep_me.png")
    asset = assets.import_file(tmp_path / "keep_me.png")
    path = assets.absolute_path(asset)
    assets.remove(asset.id)
    assert path.is_file()
