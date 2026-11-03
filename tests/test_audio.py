"""Audio: clips, subtitles, mixing, and lip-sync (GUI-free)."""

from pathlib import Path

import numpy as np
import pytest
import struct
import wave

from app.controller import AppController
from audio import (
    AudioClip,
    Subtitle,
    clip_duration_frames,
    from_srt,
    import_clip,
    lip_sync_envelope,
    mix_clips,
    to_srt,
)


@pytest.fixture
def controller(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return AppController()


def _make_wav(path: Path, freq: float = 440.0, seconds: float = 0.5,
              rate: int = 22050) -> None:
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = []
        for i in range(n):
            v = int(32767 * 0.3 * np.sin(2 * np.pi * freq * i / rate))
            frames.append(struct.pack("<h", v))
        w.writeframes(b"".join(frames))


def test_clip_roundtrip():
    c = AudioClip(id="a1", name="x", path="assets/audio/x.wav",
                  start_frame=10, duration_frames=30, volume=0.5, track=2)
    assert AudioClip.from_dict(c.to_dict()) == c


def test_subtitle_roundtrip():
    s = Subtitle(id="s1", start_frame=0, end_frame=30, text="hi")
    assert Subtitle.from_dict(s.to_dict()) == s


def test_import_clip_copies_file(tmp_path):
    src = tmp_path / "in.wav"
    _make_wav(src)
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    rel = import_clip(project_dir, src)
    assert (project_dir / rel).exists()
    assert rel.startswith("assets/audio/")


def test_clip_duration_frames_wav(tmp_path):
    src = tmp_path / "d.wav"
    _make_wav(src, seconds=1.0, rate=22050)
    assert clip_duration_frames(src, 30) == 30


def test_mix_clips_produces_wav(tmp_path):
    src = tmp_path / "a.wav"
    _make_wav(src, seconds=0.5)
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    rel = import_clip(project_dir, src)
    clip = AudioClip(id="c1", name="a", path=rel,
                     start_frame=0, duration_frames=15, volume=1.0)
    out = mix_clips(project_dir, [clip], 30, 15)
    assert out is not None and out.exists()
    with wave.open(str(out), "rb") as w:
        assert w.getnframes() > 0


def test_mix_empty_returns_none(tmp_path):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    assert mix_clips(project_dir, [], 30, 15) is None


def test_lip_sync_envelope_length(tmp_path):
    src = tmp_path / "v.wav"
    _make_wav(src, seconds=0.5)
    env = lip_sync_envelope(src, 30, 15)
    assert len(env) == 15
    assert all(0.0 <= v <= 1.0 for _, v in env)


def test_srt_roundtrip():
    subs = [Subtitle(id="s1", start_frame=0, end_frame=30, text="hello"),
            Subtitle(id="s2", start_frame=30, end_frame=60, text="world")]
    text = to_srt(subs, 30)
    back = from_srt(text, 30)
    assert len(back) == 2
    assert back[0].text == "hello"
    assert back[1].start_frame == 30


def test_controller_audio_workflow(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    src = tmp_path / "v.wav"
    _make_wav(src)
    clip = controller.add_audio_clip(src, name="voice", start_frame=0)
    assert clip["name"] == "voice"
    assert controller.project.audio_clips
    sub = controller.add_subtitle(0, 30, "hi")
    assert controller.project.subtitles
    controller.remove_audio_clip(clip["id"])
    controller.remove_subtitle(sub["id"])
    assert not controller.project.audio_clips
    assert not controller.project.subtitles


def test_controller_lip_sync_writes_keys(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    box = controller.add_object(scene_id, type="rect", name="Mouth")
    src = tmp_path / "v.wav"
    _make_wav(src)
    controller.apply_lip_sync(scene_id, box.id, src, start_frame=0)
    assert "scale_y" in box.tracks and box.tracks["scale_y"]


def test_rendering_with_audio(controller, tmp_path):
    # Smoke: export with a mixed audio track does not crash.
    import shutil
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")
    controller.new_project(tmp_path / "p", "P")
    src = tmp_path / "v.wav"
    _make_wav(src)
    controller.add_audio_clip(src, name="v")
    out = controller.export_video(tmp_path / "out.mp4")
    assert Path(out).exists() and Path(out).stat().st_size > 1000
