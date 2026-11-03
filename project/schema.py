"""MOVEXA project schema — versioned, validated, lossless (architecture doc 5).

Storage format is JSON (project.json) with integer frame timing. Every model
keeps an ``extras`` dict so unknown keys from newer/other schemas survive a
load -> save round trip instead of being silently discarded (5.2 rule).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

SCHEMA_VERSION = "1.0"

_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")

#: Object types renderable by the canvas.
OBJECT_TYPES: ClassVar[tuple[str, ...]] = ("image", "rect", "ellipse", "text")

ASSET_TYPES: ClassVar[tuple[str, ...]] = ("image", "audio")

#: Asset categories (mirror the project directory layout, INFO.md 8).
ASSET_CATEGORIES: ClassVar[tuple[str, ...]] = (
    "characters", "backgrounds", "props", "audio", "other",
)

ERROR_SCHEMA_VERSION = "unsupported schema version"
ERROR_EMPTY_ID = "empty identifier"
ERROR_BAD_ID = f"identifier must match {_ID_RE.pattern}"
ERROR_EMPTY_NAME = "empty name"
ERROR_BAD_RESOLUTION = "settings.width/height must be positive integers"
ERROR_BAD_FPS = "settings.fps must be a positive integer"
ERROR_BAD_DURATION = "scene.duration_frames must be a positive integer"
ERROR_BAD_EASING = "unknown object type"
ERROR_BAD_ASSET_TYPE = "unknown asset type"
ERROR_BAD_CATEGORY = "unknown asset category"
ERROR_UNKNOWN_ASSET_REF = "references an unknown asset id"
ERROR_DUPLICATE_SCENE = "duplicate scene id"
ERROR_DUPLICATE_OBJECT = "duplicate object id"
ERROR_DUPLICATE_ASSET = "duplicate asset id"
ERROR_UNKNOWN_PARENT = "parent_id points to a missing object in the same scene"

# Properties an object camera/animation track may animate (schema contract).
ANIMATABLE_PROPS: ClassVar[tuple[str, ...]] = (
    "x", "y", "rotation", "scale_x", "scale_y", "opacity",
)
CAMERA_PROPS: ClassVar[tuple[str, ...]] = ("x", "y", "zoom")
EASING_NAMES: ClassVar[tuple[str, ...]] = (
    "step", "linear", "ease_in", "ease_out", "ease_in_out",
)

ERROR_UNKNOWN_TRACK_PROP = "unknown animation track property"
ERROR_UNKNOWN_EASING = "unknown easing name"
ERROR_BAD_KEYFRAME = "keyframe frame must be an integer >= 0"
ERROR_BAD_TRACK_ORDER = "keyframes must be ordered by frame"
ERROR_UNKNOWN_TRANSITION = "unknown scene transition type"
ERROR_BAD_TRANSITION_FRAMES = "transition_frames must be 1..duration-1 when a transition is set"

SCENE_TRANSITIONS: ClassVar[tuple[str, ...]] = ("none", "crossfade", "dip_black", "dip_white")

def _valid_id(value: str) -> bool:
    return bool(value) and _ID_RE.match(value) is not None

def _merge_extras(into: dict[str, Any], extras: dict[str, Any]) -> None:
    """Recursively merge unknown *extras* into *into* without overwriting known keys."""
    for key, value in extras.items():
        if key not in into:
            into[key] = value
        elif isinstance(into[key], dict) and isinstance(value, dict):
            _merge_extras(into[key], value)

def _split_extras(data: dict[str, Any], known: frozenset[str]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k not in known}

@dataclass
class ProjectSettings:

    width: int = 1920
    height: int = 1080
    fps: int = 30

    KNOWN: ClassVar[frozenset[str]] = frozenset({"width", "height", "fps"})

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {"width": self.width, "height": self.height, "fps": self.fps}
        _merge_extras(data, self.extras)
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "ProjectSettings":
        extras = _split_extras(data, cls.KNOWN)
        return cls(
            width=data.get("width", 1920),
            height=data.get("height", 1080),
            fps=data.get("fps", 30),
            extras=extras,
        )

    extras: dict[str, Any] = field(default_factory=dict)

@dataclass
class Keyframe:
    """One value pinned to one integer frame.

    Integer frames are the only time unit (architecture doc 8); seconds are
    always derived downstream as frame / fps, never stored here.
    """

    frame: int
    value: float
    easing: str = "linear"
    extras: dict[str, Any] = field(default_factory=dict)

    KNOWN: ClassVar[frozenset[str]] = frozenset({"frame", "value", "easing"})

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "frame": self.frame, "value": self.value, "easing": self.easing,
        }
        _merge_extras(data, self.extras)
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "Keyframe":
        extras = _split_extras(data, cls.KNOWN)
        return cls(
            frame=int(data.get("frame", 0)),
            value=float(data.get("value", 0.0)),
            easing=data.get("easing", "linear"),
            extras=extras,
        )


def _tracks_from_data(
    data: Any, allowed: tuple[str, ...]
) -> tuple[dict[str, list[Keyframe]], dict[str, Any]]:
    """Parse a ``tracks`` dict; returns (tracks, extras_for_unknown_names).

    Unknown property names land in extras instead of being dropped, so
    projects written by a newer schema still round-trip losslessly.
    """
    tracks: dict[str, list[Keyframe]] = {}
    extras: dict[str, Any] = {}
    if not isinstance(data, dict):
        return tracks, extras
    for name, kfs in data.items():
        if isinstance(kfs, dict):
            # Wrapped form {"keyframes": [...], "meta": ...} keeps meta intact.
            keyframes: Any = kfs.get("keyframes", [])
            wrapped: dict[str, Any] = {k: v for k, v in kfs.items() if k != "keyframes"}
        else:
            keyframes = kfs
            wrapped = {}
        parsed = sorted(
            (Keyframe.from_data(kf) for kf in keyframes),
            key=lambda kf: kf.frame,
        )
        seen: dict[int, Keyframe] = {}
        for kf in parsed:
            seen[kf.frame] = kf  # same frame twice: later definition wins
        ordered = [seen[f] for f in sorted(seen)]
        if name in allowed:
            tracks[name] = ordered
            if wrapped:
                extras.setdefault(name, {}).update(wrapped)
        else:
            extras[name] = ordered if not wrapped else {"keyframes": ordered, **wrapped}
    return tracks, extras


def _tracks_to_data(
    tracks: dict[str, list[Keyframe]],
    allowed: tuple[str, ...],
    extras: dict[str, Any],
) -> dict[str, Any]:
    """Inverse of :func:`_tracks_from_data`.

    Extras never mutate: wrapper dicts are rebuilt as copies with the
    current keyframes injected, so saving cannot corrupt in-memory state.
    """
    data: dict[str, Any] = {name: [kf.to_data() for kf in kfs] for name, kfs in tracks.items()}
    merged: dict[str, Any] = {}
    for name, value in extras.items():
        if name in tracks and isinstance(value, dict):
            value = {**value, "keyframes": [kf.to_data() for kf in tracks[name]]}
        merged[name] = value
    _merge_extras(data, merged)
    return data


@dataclass
class AssetInfo:

    id: str
    name: str
    type: str            # "image" | "audio"
    category: str        # characters | backgrounds | props | audio | other
    relative_path: str   # path relative to the project directory
    size_bytes: int = 0
    width: int | None = None
    height: int | None = None
    tags: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    KNOWN: ClassVar[frozenset[str]] = frozenset(
        {"id", "name", "type", "category", "relative_path", "size_bytes",
         "width", "height", "tags"}
    )

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id, "name": self.name, "type": self.type,
            "category": self.category, "relative_path": self.relative_path,
            "size_bytes": self.size_bytes, "width": self.width,
            "height": self.height, "tags": list(self.tags),
        }
        _merge_extras(data, self.extras)
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "AssetInfo":
        extras = _split_extras(data, cls.KNOWN)
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", "image"),
            category=data.get("category", "other"),
            relative_path=data.get("relative_path", ""),
            size_bytes=data.get("size_bytes", 0),
            width=data.get("width"),
            height=data.get("height"),
            tags=[str(t) for t in data.get("tags", [])],
            extras=extras,
        )

@dataclass
class SceneObject:

    id: str
    name: str = ""
    type: str = "rect"               # image | rect | ellipse | text
    asset_id: str | None = None      # required for type == "image"
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0            # degrees, clockwise
    scale_x: float = 1.0
    scale_y: float = 1.0
    opacity: float = 1.0             # 0..1
    visible: bool = True
    parent_id: str | None = None     # scene-graph parenting
    pivot_x: float = 0.0             # rotation/scale anchor, from center outwards (stage units)
    pivot_y: float = 0.0
    color: str = "#7c4dff"           # fill color for procedural shapes
    text: str = ""                   # content for type == "text"
    tracks: dict[str, list[Keyframe]] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    KNOWN: ClassVar[frozenset[str]] = frozenset(
        {"id", "name", "type", "asset_id", "x", "y", "rotation", "scale_x",
         "scale_y", "opacity", "visible", "parent_id", "pivot_x", "pivot_y",
         "color", "text", "tracks"}
    )

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id, "name": self.name, "type": self.type,
            "asset_id": self.asset_id, "x": self.x, "y": self.y,
            "rotation": self.rotation, "scale_x": self.scale_x,
            "scale_y": self.scale_y, "opacity": self.opacity,
            "visible": self.visible, "parent_id": self.parent_id,
            "pivot_x": self.pivot_x, "pivot_y": self.pivot_y,
            "color": self.color, "text": self.text,
            "tracks": _tracks_to_data(self.tracks, ANIMATABLE_PROPS,
                                      self.extras.get("tracks", {})),
        }
        _merge_extras(data, self.extras)
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "SceneObject":
        extras = _split_extras(data, cls.KNOWN)
        tracks, track_extras = _tracks_from_data(data.get("tracks"), ANIMATABLE_PROPS)
        if track_extras:
            extras["tracks"] = track_extras
        return cls(
            id=data.get("id", ""), name=data.get("name", ""),
            type=data.get("type", "rect"), asset_id=data.get("asset_id"),
            x=data.get("x", 0.0), y=data.get("y", 0.0),
            rotation=data.get("rotation", 0.0),
            scale_x=data.get("scale_x", 1.0), scale_y=data.get("scale_y", 1.0),
            opacity=data.get("opacity", 1.0), visible=data.get("visible", True),
            parent_id=data.get("parent_id"),
            pivot_x=data.get("pivot_x", 0.0), pivot_y=data.get("pivot_y", 0.0),
            color=data.get("color", "#7c4dff"),
            text=data.get("text", ""), tracks=tracks, extras=extras,
        )

@dataclass
class Scene:
    """A single scene: background + ordered list of objects.

    Object order defines paint order: first element paints first (bottom).
    """

    id: str
    name: str = "Scene"
    duration_frames: int = 150                    # 5 s @ 30 fps
    background_color: str = "#141420"
    background_asset_id: str | None = None
    transition: str = "none"        # handoff style into the NEXT scene in order
    transition_frames: int = 0      # window at the end of THIS scene
    objects: list[SceneObject] = field(default_factory=list)
    camera_tracks: dict[str, list[Keyframe]] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    KNOWN: ClassVar[frozenset[str]] = frozenset(
        {"id", "name", "duration_frames", "background_color",
         "background_asset_id", "transition", "transition_frames",
         "objects", "camera_tracks"}
    )

    def object_by_id(self, object_id: str) -> SceneObject | None:
        return next((o for o in self.objects if o.id == object_id), None)

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id, "name": self.name,
            "duration_frames": self.duration_frames,
            "background_color": self.background_color,
            "background_asset_id": self.background_asset_id,
            "transition": self.transition,
            "transition_frames": self.transition_frames,
            "objects": [o.to_data() for o in self.objects],
            "camera_tracks": _tracks_to_data(self.camera_tracks, CAMERA_PROPS,
                                             self.extras.get("camera_tracks", {})),
        }
        _merge_extras(data, self.extras)
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "Scene":
        extras = _split_extras(data, cls.KNOWN)
        camera_tracks, camera_extras = _tracks_from_data(
            data.get("camera_tracks"), CAMERA_PROPS)
        if camera_extras:
            extras["camera_tracks"] = camera_extras
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Scene"),
            duration_frames=data.get("duration_frames", 150),
            background_color=data.get("background_color", "#141420"),
            background_asset_id=data.get("background_asset_id"),
            transition=data.get("transition", "none"),
            transition_frames=data.get("transition_frames", 0),
            objects=[SceneObject.from_data(o) for o in data.get("objects", [])],
            camera_tracks=camera_tracks,
            extras=extras,
        )

@dataclass
class Project:

    project_id: str
    name: str = "Untitled Project"
    schema_version: str = SCHEMA_VERSION
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    created_at: str = ""
    modified_at: str = ""
    assets: list[AssetInfo] = field(default_factory=list)
    audio_clips: list[dict[str, Any]] = field(default_factory=list)
    subtitles: list[dict[str, Any]] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    KNOWN: ClassVar[frozenset[str]] = frozenset(
        {"schema_version", "project_id", "name", "settings", "created_at",
         "modified_at", "assets", "scenes", "audio_clips", "subtitles"}
    )

    def scene_by_id(self, scene_id: str) -> Scene | None:
        return next((s for s in self.scenes if s.id == scene_id), None)

    def asset_by_id(self, asset_id: str) -> AssetInfo | None:
        return next((a for a in self.assets if a.id == asset_id), None)

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "name": self.name,
            "settings": self.settings.to_data(),
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "assets": [a.to_data() for a in self.assets],
            "scenes": [s.to_data() for s in self.scenes],
            "audio_clips": [dict(c) for c in self.audio_clips],
            "subtitles": [dict(s) for s in self.subtitles],
        }
        _merge_extras(data, self.extras)
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "Project":
        extras = _split_extras(data, cls.KNOWN)
        return cls(
            project_id=data.get("project_id", ""),
            name=data.get("name", "Untitled Project"),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            settings=ProjectSettings.from_data(data.get("settings", {})),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            assets=[AssetInfo.from_data(a) for a in data.get("assets", [])],
            scenes=[Scene.from_data(s) for s in data.get("scenes", [])],
            audio_clips=[dict(c) for c in data.get("audio_clips", [])],
            subtitles=[dict(s) for s in data.get("subtitles", [])],
            extras=extras,
        )

def validate_project(project: Project) -> list[str]:
    """Return a list of human-readable problems. Empty list means valid.

    Structural checks only: ids, references, ranges, enum membership
    (architecture doc 5.3). Loader code decides whether problems are fatal.
    """
    errors: list[str] = []

    if not _valid_id(project.project_id):
        errors.append(f"project_id: {ERROR_BAD_ID}")

    asset_ids = {a.id for a in project.assets}
    for asset in project.assets:
        if not _valid_id(asset.id) or asset.id == "":
            errors.append(f"asset {asset.id!r}: {ERROR_BAD_ID}")
        if asset.type not in ASSET_TYPES:
            errors.append(f"asset {asset.id!r}: {ERROR_BAD_ASSET_TYPE} ({asset.type!r})")
        if asset.category not in ASSET_CATEGORIES:
            errors.append(f"asset {asset.id!r}: {ERROR_BAD_CATEGORY} ({asset.category!r})")
        if not asset.relative_path:
            errors.append(f"asset {asset.id!r}: missing relative_path")
    if len(asset_ids) != len(project.assets):
        errors.append(ERROR_DUPLICATE_ASSET)

    if project.settings.width <= 0 or project.settings.height <= 0:
        errors.append(ERROR_BAD_RESOLUTION)
    if project.settings.fps <= 0:
        errors.append(ERROR_BAD_FPS)

    scene_ids = {s.id for s in project.scenes}
    if len(scene_ids) != len(project.scenes):
        errors.append(ERROR_DUPLICATE_SCENE)

    for scene in project.scenes:
        prefix = f"scene {scene.id!r}"
        if not _valid_id(scene.id):
            errors.append(f"{prefix}: {ERROR_BAD_ID}")
        if scene.duration_frames < 1:
            errors.append(f"{prefix}: {ERROR_BAD_DURATION}")
        if scene.transition not in SCENE_TRANSITIONS:
            errors.append(f"{prefix}: {ERROR_UNKNOWN_TRANSITION} ({scene.transition!r})")
        if scene.transition != "none":
            if not 1 <= scene.transition_frames < scene.duration_frames:
                errors.append(f"{prefix}: {ERROR_BAD_TRANSITION_FRAMES}")
        if scene.background_asset_id and scene.background_asset_id not in asset_ids:
            errors.append(f"{prefix}: background {ERROR_UNKNOWN_ASSET_REF} {scene.background_asset_id!r}")

        object_ids = {o.id for o in scene.objects}
        for obj in scene.objects:
            where = f"{prefix} object {obj.id!r}"
            if not _valid_id(obj.id):
                errors.append(f"{where}: {ERROR_BAD_ID}")
            if obj.type not in OBJECT_TYPES:
                errors.append(f"{where}: {ERROR_BAD_EASING} ({obj.type!r})")
            if obj.type == "image":
                if not obj.asset_id or obj.asset_id not in asset_ids:
                    errors.append(f"{where}: {ERROR_UNKNOWN_ASSET_REF} ({obj.asset_id!r})")
            if obj.parent_id is not None and obj.parent_id not in object_ids:
                errors.append(f"{where}: {ERROR_UNKNOWN_PARENT} ({obj.parent_id!r})")
            if not 0.0 <= obj.opacity <= 1.0:
                errors.append(f"{where}: opacity must be 0..1")
            _validate_track(obj.tracks, ANIMATABLE_PROPS, where, errors)
        _validate_track(scene.camera_tracks, CAMERA_PROPS, prefix, errors)
        if len(object_ids) != len(scene.objects):
            errors.append(f"{prefix}: {ERROR_DUPLICATE_OBJECT}")

    return errors


def _validate_track(
    tracks: dict[str, list[Keyframe]],
    allowed: tuple[str, ...],
    where: str,
    errors: list[str],
) -> None:
    for name, keyframes in tracks.items():
        if name not in allowed:
            errors.append(f"{where}: track {name!r}: {ERROR_UNKNOWN_TRACK_PROP}")
        pairs = list(zip(keyframes, keyframes[1:]))
        if any(a.frame >= b.frame for a, b in pairs):
            errors.append(f"{where}: track {name!r}: {ERROR_BAD_TRACK_ORDER}")
        for kf in keyframes:
            if kf.frame < 0 or int(kf.frame) != kf.frame:
                errors.append(f"{where}: track {name!r}: {ERROR_BAD_KEYFRAME}")
            if kf.easing not in EASING_NAMES:
                errors.append(f"{where}: track {name!r}: {ERROR_UNKNOWN_EASING} ({kf.easing!r})")
