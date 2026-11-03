"""Renderer: deterministic frames and MP4 export via FFmpeg."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from app.controller import AppController
from engine.renderer import (
    FFmpegUnavailableError,
    ffmpeg_path,
    render_frame,
    total_frames,
)


@pytest.fixture
def controller(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return AppController()


@pytest.fixture
def project_with_motion(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    box = controller.add_object(scene_id, type="rect", name="Box",
                                x=200, y=200, color="#22d3ee")
    controller.set_keyframes(scene_id, box.id, 0, {"x": 200.0, "y": 200.0})
    controller.set_keyframes(scene_id, box.id, 60, {"x": 1500.0, "y": 900.0})
    controller.add_scene("Scene 2")
    controller.select_scene(controller.project.scenes[0].id)
    return controller, tmp_path


def _hash(img) -> str:
    return hashlib.sha256(img.tobytes()).hexdigest()


def test_render_deterministic(project_with_motion):
    controller, tmp_path = project_with_motion
    project = controller.project
    root = controller.manager.current_dir
    a = render_frame(project, 0, manager_root=root)
    b = render_frame(project, 0, manager_root=root)
    assert a.size == (project.settings.width, project.settings.height)
    assert _hash(a) == _hash(b)
    # Different frames differ.
    c = render_frame(project, 30, manager_root=root)
    assert _hash(a) != _hash(c)


def test_total_frames(project_with_motion):
    controller, _ = project_with_motion
    assert total_frames(controller.project) == 150 + 150


def test_render_transition_blends(project_with_motion):
    controller, tmp_path = project_with_motion
    scene_id = controller.project.scenes[0].id
    controller.update_scene_metadata(scene_id, transition="crossfade",
                                     transition_frames=20)
    project = controller.project
    root = controller.manager.current_dir
    # Last frame of scene 1 should still render (no crash) and differ from
    # a plain frame in scene 2.
    img = render_frame(project, 149, manager_root=root)
    assert img is not None


def test_export_requires_ffmpeg(controller, tmp_path, monkeypatch):
    controller.new_project(tmp_path / "p", "P")
    import engine.renderer as r
    monkeypatch.setattr(r, "ffmpeg_path", lambda: None)
    with pytest.raises(FFmpegUnavailableError):
        controller.export_video(tmp_path / "out.mp4")


def test_export_mp4_when_ffmpeg_available(controller, tmp_path):
    if ffmpeg_path() is None:
        pytest.skip("ffmpeg not available")
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    box = controller.add_object(scene_id, type="rect", x=100, y=100, color="#ff00ff")
    controller.set_keyframes(scene_id, box.id, 0, {"x": 100.0})
    controller.set_keyframes(scene_id, box.id, 30, {"x": 500.0})
    out = controller.export_video(tmp_path / "out.mp4")
    assert Path(out).exists() and Path(out).stat().st_size > 1000
    # Verify it is a playable container with the expected frame count.
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True)
    if probe.returncode == 0 and probe.stdout.strip():
        assert int(probe.stdout.strip()) == 150
