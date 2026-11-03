"""Audio: clips, subtitles, mixing, and basic lip-sync (Priority 6)."""

from __future__ import annotations

import shutil
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class AudioClip:
    id: str
    name: str
    path: str            # relative to project dir
    start_frame: int = 0
    duration_frames: int = 0
    volume: float = 1.0
    track: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "path": self.path,
            "start_frame": self.start_frame, "duration_frames": self.duration_frames,
            "volume": self.volume, "track": self.track,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioClip":
        return cls(
            id=data["id"], name=data.get("name", ""), path=data.get("path", ""),
            start_frame=int(data.get("start_frame", 0)),
            duration_frames=int(data.get("duration_frames", 0)),
            volume=float(data.get("volume", 1.0)),
            track=int(data.get("track", 0)),
        )


@dataclass
class Subtitle:
    id: str
    start_frame: int
    end_frame: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "start_frame": self.start_frame,
                "end_frame": self.end_frame, "text": self.text}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Subtitle":
        return cls(id=data["id"], start_frame=int(data["start_frame"]),
                   end_frame=int(data["end_frame"]), text=data.get("text", ""))


def import_clip(project_dir: Path, source: Path, category: str = "audio") -> str:
    """Copy an audio file into the project and return its relative path."""
    target_dir = project_dir / "assets" / category
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / source.name
    if not dest.exists() or dest.stat().st_size != source.stat().st_size:
        shutil.copy2(source, dest)
    return str(dest.relative_to(project_dir)).replace("\\", "/")


def clip_duration_frames(path: Path, fps: int) -> int:
    """Best-effort duration in frames using wave (WAV) or ffprobe."""
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w:
                frames = w.getnframes()
                rate = w.getframerate()
                return max(1, int(frames / rate * fps))
        except (wave.Error, OSError):
            pass
    # Fallback to ffprobe.
    try:
        import subprocess
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return max(1, int(float(out.stdout.strip()) * fps))
    except (OSError, ValueError):
        pass
    return 0


def mix_clips(project_dir: Path, clips: list[AudioClip], fps: int,
              total_frames: int, sample_rate: int = 44100) -> Path | None:
    """Mix all clips into one WAV file. Returns path or None if no clips."""
    if not clips:
        return None
    n_samples = int(total_frames / fps * sample_rate)
    mix = np.zeros(n_samples, dtype=np.float32)
    for clip in clips:
        path = project_dir / clip.path
        if not path.exists():
            continue
        if path.suffix.lower() != ".wav":
            continue
        try:
            with wave.open(str(path), "rb") as w:
                rate = w.getframerate()
                n = w.getnframes()
                raw = w.readframes(n)
                channels = w.getnchannels()
                sampwidth = w.getsampwidth()
        except (wave.Error, OSError):
            continue
        if sampwidth != 2:
            continue
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        if channels > 1:
            data = data.reshape(-1, channels).mean(axis=1)
        if rate != sample_rate:
            # Nearest-neighbour resample (good enough for preview/mix).
            idx = (np.arange(len(data)) * sample_rate / rate).astype(int)
            idx = np.clip(idx, 0, len(data) - 1)
            data = data[idx]
        start = int(clip.start_frame / fps * sample_rate)
        end = min(n_samples, start + len(data))
        seg = data[: end - start] * clip.volume
        mix[start:end] += seg
    # Normalize to int16.
    peak = np.max(np.abs(mix)) if mix.size else 0.0
    if peak > 0:
        mix = mix / peak * 0.9
    pcm = (mix * 32767).astype(np.int16)
    out = project_dir / "exports" / "mixed.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return out


def lip_sync_envelope(path: Path, fps: int,
                      frame_count: int) -> list[tuple[int, float]]:
    """Return (frame, mouth_open 0..1) samples from an audio file's energy."""
    if not path.exists() or path.suffix.lower() != ".wav":
        return []
    try:
        with wave.open(str(path), "rb") as w:
            rate = w.getframerate()
            n = w.getnframes()
            raw = w.readframes(n)
            channels = w.getnchannels()
            sampwidth = w.getsampwidth()
    except (wave.Error, OSError):
        return []
    if sampwidth != 2:
        return []
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    samples_per_frame = max(1, rate // fps)
    result: list[tuple[int, float]] = []
    for f in range(frame_count):
        chunk = data[f * samples_per_frame:(f + 1) * samples_per_frame]
        if chunk.size == 0:
            result.append((f, 0.0))
            continue
        rms = float(np.sqrt(np.mean(chunk ** 2))) / 32768.0
        # Map RMS to a 0..1 mouth-open value with a soft knee.
        open_val = min(1.0, rms * 4.0)
        result.append((f, open_val))
    return result


def to_srt(subtitles: list[Subtitle], fps: int) -> str:
    def fmt(frame: int) -> str:
        total_ms = int(frame / fps * 1000)
        h = total_ms // 3600000
        m = (total_ms // 60000) % 60
        s = (total_ms // 1000) % 60
        ms = total_ms % 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, sub in enumerate(subtitles, 1):
        lines.append(str(i))
        lines.append(f"{fmt(sub.start_frame)} --> {fmt(sub.end_frame)}")
        lines.append(sub.text)
        lines.append("")
    return "\n".join(lines)


def from_srt(text: str, fps: int) -> list[Subtitle]:
    import re
    subs: list[Subtitle] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)",
                     lines[1].strip())
        if not m:
            continue
        def to_frame(h, m, s, ms):
            return int((int(h) * 3600 + int(m) * 60 + int(s) +
                        int(ms) / 1000.0) * fps)
        sf = to_frame(*m.groups()[:4])
        ef = to_frame(*m.groups()[4:])
        subs.append(Subtitle(id=f"sub_{uuid.uuid4().hex[:8]}",
                            start_frame=sf, end_frame=ef,
                            text="\n".join(lines[2:])))
    return subs
