"""Asset Manager (architecture doc 11).

Imports media files into the open project:
- copies files into ``assets/<category>/`` with collision-safe names
- computes sha1 so identical imports deduplicate to one asset id
- reads image dimensions with Pillow
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import uuid
from pathlib import Path

from PIL import Image

from project.manager import ProjectManager
from project.schema import ASSET_CATEGORIES, AssetInfo, Project

log = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aac", ".m4a", ".ogg", ".flac"}

def detect_type(suffix: str) -> str | None:
    s = suffix.lower()
    if s in IMAGE_EXTENSIONS:
        return "image"
    if s in AUDIO_EXTENSIONS:
        return "audio"
    return None

def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _image_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        with Image.open(path) as img:
            return img.width, img.height
    except Exception:  # noqa: BLE001 - unknown dims must not block import
        log.warning("could not read image dimensions: %s", path)
        return None, None

class AssetManager:

    def __init__(self, manager: ProjectManager) -> None:
        self.manager = manager

    @property
    def project(self) -> Project:
        if self.manager.current is None:
            raise RuntimeError("no project open")
        return self.manager.current

    def assets(self) -> list[AssetInfo]:
        return self.project.assets

    def get(self, asset_id: str) -> AssetInfo | None:
        return self.project.asset_by_id(asset_id)

    def absolute_path(self, asset: AssetInfo) -> Path:
        if self.manager.current_dir is None:
            raise RuntimeError("no project open")
        return self.manager.current_dir / asset.relative_path

    def exists_on_disk(self, asset: AssetInfo) -> bool:
        return self.absolute_path(asset).is_file()

    def import_file(self, source: Path | str, category: str | None = None) -> AssetInfo:
        """Copy *source* into the project and register it. Returns the asset.

        Raises ValueError for unsupported file types, FileNotFoundError when
        the source is missing. Duplicate content (same sha1) returns the
        existing asset instead of storing a second copy.
        """
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        asset_type = detect_type(source.suffix)
        if asset_type is None:
            raise ValueError(f"unsupported asset type: {source.suffix}")
        if category is None:
            category = "audio" if asset_type == "audio" else "other"
        if category not in ASSET_CATEGORIES:
            raise ValueError(f"unknown category: {category}")

        digest = _sha1(source)
        existing = next((a for a in self.project.assets
                         if a.extras.get("sha1") == digest), None)
        if existing is not None:
            log.info("asset import deduplicated to %s", existing.id)
            return existing

        target_dir = self.manager.asset_subdir(category)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        stem, suffix = source.stem, source.suffix
        counter = 1
        while target.exists():
            counter += 1
            target = target_dir / f"{stem}_{counter}{suffix}"

        shutil.copy2(source, target)
        rel_path = target.relative_to(self.manager.current_dir).as_posix()

        width = height = None
        if asset_type == "image":
            width, height = _image_dimensions(target)

        asset = AssetInfo(
            id=f"asset_{uuid.uuid4().hex[:8]}",
            name=stem,
            type=asset_type,
            category=category,
            relative_path=rel_path,
            size_bytes=target.stat().st_size,
            width=width,
            height=height,
        )
        asset.extras["sha1"] = digest
        self.project.assets.append(asset)
        log.info("imported asset %s from %s", asset.id, source)
        return asset

    def remove(self, asset_id: str) -> None:
        """Remove an asset entry when no scene references it.

        Raises RuntimeError while the asset is referenced; the on-disk file is
        kept because the user may re-add it.
        """
        project = self.project
        referenced = [
            (scene.id, scene.background_asset_id)
            for scene in project.scenes
        ] + [
            (scene.id, obj.asset_id)
            for scene in project.scenes
            for obj in scene.objects
        ]
        users = [scene_id for scene_id, ref in referenced if ref == asset_id]
        if users:
            raise RuntimeError(f"asset {asset_id} used by scenes: {', '.join(users)}")

        asset = project.asset_by_id(asset_id)
        if asset is None:
            raise KeyError(asset_id)
        project.assets.remove(asset)
