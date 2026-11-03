"""Application controller — the single bridge between GUI and data layer.

All project mutations happen here so widgets stay thin and every change is
announced on the EventBus (architecture doc 4.1). Runs on the GUI thread;
GUI updates are pushed through bus events that widgets subscribe to.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from core.events import EventBus
from engine.actions import apply_action, rig_targets, sample_frames
from engine.character_rig import build_human_rig
from engine.player import PlaybackController
from engine.scene_graph import (
    build_scene_graph,
    object_snapshot,
    world_transform_with_snapshots,
)
from project.assets import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    AssetManager,
    detect_type,
)
from project.manager import ProjectManager
from project.schema import (
    ANIMATABLE_PROPS,
    CAMERA_PROPS,
    OBJECT_TYPES,
    SCENE_TRANSITIONS,
    Keyframe,
    Project,
    Scene,
    SceneObject,
    validate_project,
)

log = logging.getLogger(__name__)


class AppController:
    """Coordinates project, scene, asset, object and playback operations.

    All project mutations go through this class so widgets stay thin and every
    change is announced on the EventBus (architecture doc 4.1). Runs on the
    GUI thread only; long jobs must move to workers, not call these methods.
    """

    def __init__(self, bus: EventBus | None = None, fps: int = 30) -> None:
        self.bus = bus or EventBus()
        self.manager = ProjectManager()
        self.asset_manager = AssetManager(self.manager)
        self.player = PlaybackController(fps=fps)
        self.current_scene_id: str | None = None
        self.selected_object_id: str | None = None

    @property
    def project(self) -> Project | None:
        return self.manager.current

    def has_project(self) -> bool:
        return self.project is not None

    def require_project(self) -> Project:
        if self.project is None or self.manager.current_dir is None:
            raise RuntimeError("no project open")
        return self.project

    def new_project(
        self, directory: Path | str, name: str,
        width: int = 1920, height: int = 1080, fps: int = 30,
    ) -> Project:
        project = self.manager.create_project(directory, name, width, height, fps)
        self._reset_selection()
        self.bus.publish("project.created", {
            "project": project, "directory": str(self.manager.current_dir),
        })
        first = self.add_scene(name="Scene 1", publish_event=False)
        self.select_scene(first.id)
        self.save()
        return project

    def open_project(self, directory: Path | str) -> Project:
        project = self.manager.open_project(directory)
        self._reset_selection()
        self.bus.publish("project.opened", {
            "project": project, "directory": str(self.manager.current_dir),
        })
        if project.scenes:
            # Going through select_scene rebinds the player to scene bounds.
            self.select_scene(project.scenes[0].id)
        return project

    def save(self) -> Project | None:
        project = self.require_project()
        self.manager.save()
        self.bus.publish("project.saved", {"project": project})
        return project

    def close_project(self) -> None:
        self.require_project()
        self.manager.current = None
        self.manager.current_dir = None
        self._reset_selection()
        self.bus.publish("project.closed", {})

    @staticmethod
    def validation_problems(project: Project) -> list[str]:
        return validate_project(project)

    def _scene(self, scene_id: str) -> Scene:
        scene = self.require_project().scene_by_id(scene_id)
        if scene is None:
            raise KeyError(f"unknown scene: {scene_id}")
        return scene

    @staticmethod
    def _scene_name_taken(project: Project, name: str) -> bool:
        return any(s.name == name for s in project.scenes)

    def _unique_scene_name(self, project: Project, base: str) -> str:
        if not self._scene_name_taken(project, base):
            return base
        n = 2
        while self._scene_name_taken(project, f"{base} {n}"):
            n += 1
        return f"{base} {n}"

    def add_scene(self, name: str | None = None, publish_event: bool = True) -> Scene:
        project = self.require_project()
        base = name or "Scene"
        scene = Scene(
            id=f"scene_{uuid.uuid4().hex[:8]}",
            name=self._unique_scene_name(project, base),
        )
        project.scenes.append(scene)
        if self.current_scene_id is None:
            self.current_scene_id = scene.id
        self.bus.publish("scene.created", {"scene_id": scene.id})
        if publish_event:
            self.select_scene(scene.id)
        return scene

    def remove_scene(self, scene_id: str) -> None:
        project = self.require_project()
        scene = project.scene_by_id(scene_id)
        if scene is None:
            raise KeyError(scene_id)
        project.scenes.remove(scene)
        if self.current_scene_id == scene_id:
            self.current_scene_id = project.scenes[-1].id if project.scenes else None
            self.selected_object_id = None
        self.bus.publish("scene.removed", {"scene_id": scene_id})
        if self.current_scene_id is not None:
            self.bus.publish("scene.selected", {"scene_id": self.current_scene_id})

    def duplicate_scene(self, scene_id: str) -> Scene:
        """Clone a scene with fresh ids so rig/asset references stay valid."""
        project = self.require_project()
        scene = project.scene_by_id(scene_id)
        if scene is None:
            raise KeyError(scene_id)
        id_map: dict[str, str] = {}
        clone = Scene(
            id=f"scene_{uuid.uuid4().hex[:8]}",
            name=self._unique_scene_name(project, f"{scene.name} copy"),
            duration_frames=scene.duration_frames,
            background_color=scene.background_color,
            background_asset_id=scene.background_asset_id,
        )
        for obj in scene.objects:
            new_id = f"obj_{uuid.uuid4().hex[:8]}"
            copy = SceneObject.from_data(obj.to_data())
            copy.id = new_id
            id_map[obj.id] = new_id
            clone.objects.append(copy)
        for copy in clone.objects:
            if copy.parent_id is not None:
                copy.parent_id = id_map.get(copy.parent_id, copy.parent_id)
        index = project.scenes.index(scene)
        project.scenes.insert(index + 1, clone)
        self.bus.publish("scene.created", {"scene_id": clone.id})
        return clone

    def reorder_scene(self, scene_id: str, delta: int) -> None:
        project = self.require_project()
        scene = project.scene_by_id(scene_id)
        if scene is None:
            raise KeyError(scene_id)
        index = project.scenes.index(scene)
        target = index + delta
        if 0 <= target < len(project.scenes) and target != index:
            project.scenes.remove(scene)
            project.scenes.insert(target, scene)
            self.bus.publish("scene.reordered", {"scene_id": scene_id})

    def select_scene(self, scene_id: str) -> None:
        scene = self._scene(scene_id)
        self.current_scene_id = scene_id
        self.selected_object_id = None
        # Playback always rebinding keeps frame bounds in sync with the scene
        # duration edited between selections.
        self.player.stop()
        self.player.set_bounds(scene.duration_frames)
        self.bus.publish("scene.selected", {"scene_id": scene.id})

    def update_scene_metadata(
        self, scene_id: str,
        name: str | None = None,
        background_color: str | None = None,
        duration_frames: int | None = None,
        transition: str | None = None,
        transition_frames: int | None = None,
    ) -> None:
        """Edit scene-level fields that do not live on a single object."""
        scene = self._scene(scene_id)
        if name is not None:
            scene.name = name
        if background_color is not None:
            scene.background_color = background_color
        if duration_frames is not None:
            scene.duration_frames = max(1, int(duration_frames))
            if self.current_scene_id == scene_id:
                self.player.set_bounds(scene.duration_frames)
        if transition is not None:
            if transition not in SCENE_TRANSITIONS:
                raise ValueError(f"unknown transition: {transition}")
            scene.transition = transition
        if transition_frames is not None:
            scene.transition_frames = max(0, int(transition_frames))
        self._scene_changed(scene_id)

    def set_scene_background(self, scene_id: str, asset_id: str | None) -> None:
        scene = self._scene(scene_id)
        scene.background_asset_id = asset_id
        self._scene_changed(scene_id)

    def add_object(self, scene_id: str, **kwargs: Any) -> SceneObject:
        scene = self._scene(scene_id)
        obj_type = kwargs.get("type", "rect")
        if obj_type not in OBJECT_TYPES:
            raise ValueError(f"unsupported object type: {obj_type}")
        obj = SceneObject(
            id=f"obj_{uuid.uuid4().hex[:8]}",
            name=self._unique_object_name(scene, str(kwargs.get("name", obj_type))),
            **{k: v for k, v in kwargs.items() if k in {
                "type", "asset_id", "x", "y", "rotation", "scale_x",
                "scale_y", "opacity", "color", "text", "parent_id",
            }},
        )
        scene.objects.append(obj)
        self.bus.publish("object.added", {"scene_id": scene_id, "object_id": obj.id})
        self.select_object(scene_id, obj.id)
        return obj

    def add_object_from_asset(self, scene_id: str, asset_id: str) -> SceneObject:
        """Place an image asset in the scene center, scaled to fit the stage."""
        project = self.require_project()
        asset = project.asset_by_id(asset_id)
        if asset is None or asset.type != "image":
            raise ValueError(f"not an image asset: {asset_id}")
        scale = 1.0
        if asset.width and asset.height:
            stage = (project.settings.width, project.settings.height)
            scale = min(min(stage[0] / asset.width, stage[1] / asset.height), 1.0)
        return self.add_object(
            scene_id, type="image", asset_id=asset_id,
            name=asset.name,
            x=project.settings.width / 2, y=project.settings.height / 2,
            scale_x=scale, scale_y=scale,
        )

    def _unique_object_name(self, scene: Scene, base: str) -> str:
        used = {o.name for o in scene.objects}
        if base not in used:
            return base
        n = 2
        while f"{base} {n}" in used:
            n += 1
        return f"{base} {n}"

    def update_object(self, scene_id: str, object_id: str, **changes: Any) -> None:
        scene = self._scene(scene_id)
        obj = scene.object_by_id(object_id)
        if obj is None:
            raise KeyError(object_id)
        static_fields = {
            "name", "visible", "color", "text", "parent_id",
        }
        animated = self._animated_props(obj)
        for key, value in changes.items():
            if key in static_fields:
                setattr(obj, key, value)
            elif key in animated:
                # Editing an animated property writes a keyframe at the
                # playback frame, never the static field: otherwise the next
                # evaluation would resurrect stale data over the visual edit.
                self._upsert_keyframe(obj, key, self.player.frame, value)
            elif key in ANIMATABLE_PROPS:
                setattr(obj, key, value)
        self._scene_changed(scene_id)

    @staticmethod
    def _animated_props(obj: SceneObject) -> set[str]:
        return {name for name, keyframes in obj.tracks.items() if keyframes}

    @staticmethod
    def _upsert_keyframe(obj: SceneObject, prop: str, frame: int, value: float) -> None:
        track = obj.tracks.setdefault(prop, [])
        keyframes = [kf for kf in track if kf.frame != frame]
        keyframes.append(Keyframe(frame=frame, value=float(value)))
        keyframes.sort(key=lambda kf: kf.frame)
        obj.tracks[prop] = keyframes

    def set_keyframes(
        self, scene_id: str, object_id: str, frame: int,
        values: dict[str, float],
    ) -> None:
        """Pin the given properties to *frame* with explicit values."""
        scene = self._scene(scene_id)
        obj = scene.object_by_id(object_id)
        if obj is None:
            raise KeyError(object_id)
        for prop, value in values.items():
            if prop in ANIMATABLE_PROPS:
                self._upsert_keyframe(obj, str(prop), int(frame), float(value))
        self._scene_changed(scene_id)

    def remove_keyframe_at(
        self, scene_id: str, object_id: str, frame: int,
        props: tuple[str, ...] | None = None,
    ) -> int:
        """Delete keyframes exactly at *frame*; keeps a track even if emptied."""
        scene = self._scene(scene_id)
        obj = scene.object_by_id(object_id)
        if obj is None:
            raise KeyError(object_id)
        targets = props or tuple(obj.tracks)
        removed = 0
        for prop in targets:
            track = obj.tracks.get(prop)
            if not track:
                continue
            kept = [kf for kf in track if kf.frame != int(frame)]
            removed += len(track) - len(kept)
            obj.tracks[prop] = kept
        if removed:
            self._scene_changed(scene_id)
        return removed

    def clear_object_tracks(self, scene_id: str, object_id: str) -> None:
        scene = self._scene(scene_id)
        obj = scene.object_by_id(object_id)
        if obj is None:
            raise KeyError(object_id)
        obj.tracks.clear()
        self._scene_changed(scene_id)

    def set_camera_keyframes(
        self, scene_id: str, frame: int, values: dict[str, float]
    ) -> None:
        scene = self._scene(scene_id)
        for prop, value in values.items():
            if prop in CAMERA_PROPS:
                track = scene.camera_tracks.setdefault(str(prop), [])
                keyframes = [kf for kf in track if kf.frame != int(frame)]
                keyframes.append(Keyframe(frame=int(frame), value=float(value)))
                keyframes.sort(key=lambda kf: kf.frame)
                scene.camera_tracks[str(prop)] = keyframes
        self._scene_changed(scene_id)

    def clear_camera_tracks(self, scene_id: str) -> None:
        self._scene(scene_id).camera_tracks.clear()
        self._scene_changed(scene_id)

    def preview_frame(self) -> int:
        return self.player.frame

    def remove_object(self, scene_id: str, object_id: str) -> None:
        scene = self._scene(scene_id)
        obj = scene.object_by_id(object_id)
        if obj is None:
            raise KeyError(object_id)
        for other in scene.objects:
            if other.parent_id == object_id:
                other.parent_id = obj.parent_id
        scene.objects.remove(obj)
        if self.selected_object_id == object_id:
            self.selected_object_id = None
            self.bus.publish("object.selected", {
                "scene_id": scene_id, "object_id": None,
            })
        self._scene_changed(scene_id)

    def select_object(self, scene_id: str, object_id: str | None) -> None:
        if object_id is not None and self._scene(scene_id).object_by_id(object_id) is None:
            raise KeyError(object_id)
        self.selected_object_id = object_id
        self.bus.publish("object.selected", {
            "scene_id": scene_id, "object_id": object_id,
        })

    def _scene_changed(self, scene_id: str) -> None:
        self.bus.publish("scene.updated", {"scene_id": scene_id})

    # -- Hybrid engine (rigs, procedural actions, camera follow) ---------------

    def create_character_rig(self, scene_id: str) -> SceneObject:
        """Insert a parented humanoid at the stage center and select it."""
        project = self.require_project()
        scene = self._scene(scene_id)
        root = build_human_rig(
            scene, self._unique_object_name(scene, "Character"),
            project.settings.width, project.settings.height)
        self.bus.publish("object.added", {"scene_id": scene_id, "object_id": root.id})
        self.select_object(scene_id, root.id)
        self._scene_changed(scene_id)
        return root

    def rig_roots(self, scene_id: str) -> list[tuple[str, str, str]]:
        """(object id, name, rig id) for character rigs already in the scene."""
        return rig_targets(self._scene(scene_id))

    def apply_action(
        self, scene_id: str, object_id: str, action: str,
        start: int, end: int,
    ) -> None:
        """Sample a procedural/character action into ordinary keyframes."""
        project = self.require_project()
        scene = self._scene(scene_id)
        obj = scene.object_by_id(object_id)
        if obj is None:
            raise KeyError(object_id)
        apply_action(
            scene, obj, action, int(start), int(end), project.settings.fps,
            project.settings.width, project.settings.height)
        self._scene_changed(scene_id)
        self.bus.publish("action.applied", {
            "scene_id": scene_id, "object_id": object_id, "action": action,
        })

    def set_camera_follow(
        self, scene_id: str, object_id: str, start: int, end: int,
    ) -> None:
        """Pin camera x/y to the object's world position across the window."""
        project = self.require_project()
        scene = self._scene(scene_id)
        obj = scene.object_by_id(object_id)
        if obj is None:
            raise KeyError(object_id)
        if not 0 <= start < end < scene.duration_frames:
            raise ValueError("follow window needs 0 <= start < end < duration")
        graph = {n.object.id: n for root in build_scene_graph(scene)
                 for n in root.iterate()}
        node = graph[object_id]
        for frame in sample_frames(int(start), int(end), project.settings.fps):
            snapshots = {oid: object_snapshot(o, frame)
                         for oid, o in ((n.object.id, n.object) for n in graph.values())}
            world = world_transform_with_snapshots(node, snapshots)
            self._upsert_camera_keyframes(scene, frame, world.x, world.y)
        self._scene_changed(scene_id)
        self.bus.publish("action.applied", {
            "scene_id": scene_id, "object_id": object_id, "action": "camera_follow",
        })

    def scene_graph(self, scene_id: str):
        """Build the engine scene graph for the current scene (for preview)."""
        return build_scene_graph(self._scene(scene_id))

    def add_audio_clip(self, source, name=None, start_frame=0, volume=1.0,
                       track=0) -> dict:
        from audio import AudioClip, import_clip, clip_duration_frames
        project = self.require_project()
        root = self.manager.current_dir
        if root is None:
            raise RuntimeError("no project open")
        src = Path(source)
        rel = import_clip(root, src)
        fps = project.settings.fps
        dur = clip_duration_frames(root / rel, fps)
        clip = AudioClip(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            name=name or src.stem,
            path=rel,
            start_frame=int(start_frame),
            duration_frames=int(dur),
            volume=float(volume),
            track=int(track),
        )
        project.audio_clips.append(clip.to_dict())
        self.bus.publish("audio.changed", {"clip_id": clip.id})
        return clip.to_dict()

    def remove_audio_clip(self, clip_id: str) -> None:
        project = self.require_project()
        project.audio_clips = [c for c in project.audio_clips
                               if c.get("id") != clip_id]
        self.bus.publish("audio.changed", {"clip_id": clip_id})

    def add_subtitle(self, start_frame: int, end_frame: int, text: str) -> dict:
        from audio import Subtitle
        project = self.require_project()
        sub = Subtitle(id=f"sub_{uuid.uuid4().hex[:8]}",
                       start_frame=int(start_frame),
                       end_frame=int(end_frame), text=text)
        project.subtitles.append(sub.to_dict())
        self.bus.publish("subtitle.changed", {"subtitle_id": sub.id})
        return sub.to_dict()

    def remove_subtitle(self, subtitle_id: str) -> None:
        project = self.require_project()
        project.subtitles = [s for s in project.subtitles
                             if s.get("id") != subtitle_id]
        self.bus.publish("subtitle.changed", {"subtitle_id": subtitle_id})

    def apply_lip_sync(self, scene_id: str, object_id: str,
                       audio_path, start_frame: int = 0) -> None:
        from audio import lip_sync_envelope
        project = self.require_project()
        root = self.manager.current_dir
        path = Path(audio_path)
        if not path.is_absolute() and root is not None:
            path = root / path
        scene = self._scene(scene_id)
        obj = scene.object_by_id(object_id)
        if obj is None:
            raise KeyError(object_id)
        fps = project.settings.fps
        frame_count = scene.duration_frames
        for frame, openness in lip_sync_envelope(path, fps, frame_count):
            # Mouth openness -> scale_y around 1.0, anchored on scale base.
            value = 1.0 + openness * 0.6
            self._upsert_keyframe(obj, "scale_y", start_frame + frame, value)
        self._scene_changed(scene_id)

    def export_video(self, output_path, progress=None):
        from engine.renderer import export_video as _export
        from audio import AudioClip, mix_clips
        project = self.require_project()
        root = self.manager.current_dir
        clips = [AudioClip.from_dict(c) for c in project.audio_clips]
        audio_path = None
        if clips and root is not None:
            total = sum(s.duration_frames for s in project.scenes)
            audio_path = mix_clips(root, clips, project.settings.fps, total)
        return _export(
            project, output_path, manager_root=root,
            audio_path=audio_path, progress=progress)

    @staticmethod
    def _upsert_camera_keyframes(
        scene: Scene, frame: int, x: float, y: float
    ) -> None:
        for prop, value in (("x", x), ("y", y)):
            track = scene.camera_tracks.setdefault(prop, [])
            kept = [kf for kf in track if kf.frame != frame]
            kept.append(Keyframe(frame=frame, value=value, easing="linear"))
            kept.sort(key=lambda kf: kf.frame)
            scene.camera_tracks[prop] = kept

    def import_asset(self, source: Path | str, category: str | None = None):
        asset = self.asset_manager.import_file(source, category)
        self.bus.publish("asset.imported", {"asset_id": asset.id})
        return asset

    def remove_asset(self, asset_id: str) -> None:
        self.asset_manager.remove(asset_id)
        self.bus.publish("asset.removed", {"asset_id": asset_id})

    @staticmethod
    def file_filter() -> str:
        image = " ".join(f"*{ext}" for ext in sorted(IMAGE_EXTENSIONS))
        audio = " ".join(f"*{ext}" for ext in sorted(AUDIO_EXTENSIONS))
        return (
            f"Media files ({image} {audio});;"
            f"Images ({image});;Audio ({audio});;All files (*.*)"
        )

    def is_supported_media(self, path: str) -> bool:
        return detect_type(Path(path).suffix) is not None

    def _reset_selection(self) -> None:
        self.current_scene_id = None
        self.selected_object_id = None
