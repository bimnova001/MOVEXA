"""Deterministic frame rendering + MP4 export (architecture doc 13, Priority 4)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont

from engine.scene_graph import world_transform_with_snapshots
from engine.tracks import camera_state, object_snapshot
from engine.transitions import transition_plan
from project.schema import AssetInfo, Project, Scene, SceneObject


class FFmpegUnavailableError(RuntimeError):
    """Raised when the ffmpeg binary cannot be located on PATH."""


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def _stage_size(project: Project) -> tuple[int, int]:
    return int(project.settings.width), int(project.settings.height)


def _load_asset_image(project: Project, asset: AssetInfo | None,
                      manager_root: Path | None) -> Image.Image | None:
    if asset is None or asset.type != "image":
        return None
    if manager_root is None:
        return None
    path = manager_root / "assets" / (asset.category or "misc") / asset.filename
    if not path.exists():
        for candidate in manager_root.rglob(asset.filename):
            path = candidate
            break
    if not path.exists():
        return None
    try:
        return Image.open(path).convert("RGBA")
    except OSError:
        return None


def _cover_fit(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return resized.crop((left, top, left + w, top + h))


def _shape_image(obj: SceneObject, asset: AssetInfo | None,
                 project: Project, manager_root: Path | None,
                 stage_w: int, stage_h: int) -> Image.Image:
    if obj.type == "image":
        img = _load_asset_image(project, asset, manager_root)
        if img is None:
            out = Image.new("RGBA", (260, 120), (0, 0, 0, 0))
            d = ImageDraw.Draw(out)
            d.rectangle((0, 0, 259, 119), outline=(244, 63, 94, 255), width=3)
            d.text((130, 60), "missing", fill=(244, 63, 94, 255), anchor="mm")
            return out
        return img

    if obj.type == "ellipse":
        w, h = 180, 180
    elif obj.type == "text":
        w, h = 64 * 8, int(64 * 1.6)
    else:
        w, h = 240, 160
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    color = obj.color or "#7c4dff"
    if obj.type == "ellipse":
        d.ellipse((0, 0, w - 1, h - 1), fill=color, outline="#0a0a14", width=2)
    elif obj.type == "text":
        try:
            font = ImageFont.truetype("arial.ttf", 64)
        except OSError:
            font = ImageFont.load_default()
        text = obj.text or ""
        d.text((w // 2, h // 2), text, fill=color, font=font, anchor="mm")
    else:
        d.rectangle((0, 0, w - 1, h - 1), fill=color, outline="#0a0a14", width=2)
    return out


def _paint_scene(project: Project, scene: Scene, frame: int,
                 stage_w: int, stage_h: int,
                 manager_root: Path | None, alpha: float = 1.0) -> Image.Image:
    canvas = Image.new("RGBA", (stage_w, stage_h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (stage_w, stage_h), scene.background_color)
    if alpha < 1.0:
        bg.putalpha(int(255 * alpha))
    canvas.alpha_composite(bg)

    if scene.background_asset_id:
        asset = project.asset_by_id(scene.background_asset_id)
        img = _load_asset_image(project, asset, manager_root)
        if img is not None:
            fitted = _cover_fit(img, stage_w, stage_h)
            if alpha < 1.0:
                fitted.putalpha(int(255 * alpha))
            canvas.alpha_composite(fitted)

    camera = camera_state(scene, frame, stage_w, stage_h)
    zoom = max(0.01, camera.zoom)
    snapshots = {obj.id: object_snapshot(obj, frame) for obj in scene.objects}
    graph = {}
    try:
        from engine.scene_graph import build_scene_graph
        graph = {n.object.id: n for root in build_scene_graph(scene)
                 for n in root.iterate()}
    except ValueError:
        graph = {}

    for obj in scene.objects:
        snap = snapshots[obj.id]
        if not snap.visible:
            continue
        node = graph.get(obj.id)
        if node is None:
            continue
        world = world_transform_with_snapshots(node, snapshots)
        sx = (world.x - camera.x) / zoom + stage_w / 2.0
        sy = (world.y - camera.y) / zoom + stage_h / 2.0
        srot = world.rotation
        sscale = (world.scale_x / zoom, world.scale_y / zoom)

        asset = project.asset_by_id(obj.asset_id) if obj.asset_id else None
        shape = _shape_image(obj, asset, project, manager_root, stage_w, stage_h)
        ow, oh = shape.size
        nw = max(1, int(ow * sscale[0]))
        nh = max(1, int(oh * sscale[1]))
        shape = shape.resize((nw, nh), Image.LANCZOS)
        if srot:
            shape = shape.rotate(-srot, expand=True, resample=Image.BICUBIC)
        opacity = max(0.0, min(1.0, snap.opacity * alpha))
        if opacity < 1.0:
            r, g, b, a = shape.split()
            a = a.point(lambda v: int(v * opacity))
            shape = Image.merge("RGBA", (r, g, b, a))
        pw, ph = shape.size
        px = int(sx - pw / 2)
        py = int(sy - ph / 2)
        canvas.alpha_composite(shape, (px, py))

    return canvas


def render_frame(project: Project, global_frame: int,
                 manager_root: Path | None = None) -> Image.Image:
    stage_w, stage_h = _stage_size(project)
    scenes = project.scenes
    if not scenes:
        return Image.new("RGB", (stage_w, stage_h), "#141420")

    cumulative = 0
    scene_index = 0
    local_frame = global_frame
    for i, sc in enumerate(scenes):
        if global_frame < cumulative + sc.duration_frames:
            scene_index = i
            local_frame = global_frame - cumulative
            break
        cumulative += sc.duration_frames
    else:
        scene_index = len(scenes) - 1
        cumulative = sum(s.duration_frames for s in scenes[:-1])
        local_frame = min(scenes[-1].duration_frames - 1,
                          global_frame - cumulative)

    scene = scenes[scene_index]
    plan = transition_plan(project, scene, local_frame)
    result = Image.new("RGBA", (stage_w, stage_h), (0, 0, 0, 0))
    for index, pas in enumerate(plan.passes):
        if pas.alpha <= 0.0:
            continue
        pass_img = _paint_scene(project, pas.scene, pas.frame, stage_w, stage_h,
                                manager_root, alpha=pas.alpha)
        result.alpha_composite(pass_img)
        if index == 0 and plan.black_overlay > 0.0:
            dip = Image.new("RGBA", (stage_w, stage_h),
                            "#ffffff" if scene.transition == "dip_white"
                            else "#000000")
            dip.putalpha(int(255 * plan.black_overlay))
            result.alpha_composite(dip)
    flat = Image.new("RGB", (stage_w, stage_h), scene.background_color)
    flat.paste(result, mask=result.split()[3])
    return flat


def total_frames(project: Project) -> int:
    return sum(s.duration_frames for s in project.scenes)


def export_video(project: Project, output_path: Path | str,
                 manager_root: Path | None = None,
                 fps: Optional[int] = None,
                 audio_path: Path | str | None = None,
                 progress: Optional[Callable[[int, int], None]] = None) -> Path:
    binary = ffmpeg_path()
    if binary is None:
        raise FFmpegUnavailableError(
            "ffmpeg not found on PATH; install it to export video")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fps = fps or project.settings.fps
    stage_w, stage_h = _stage_size(project)
    n = total_frames(project)
    if n < 1:
        raise ValueError("project has no frames to render")

    has_audio = audio_path is not None and Path(audio_path).exists()
    video_target = out.with_suffix(".video.mp4") if has_audio else out

    cmd = [
        binary, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{stage_w}x{stage_h}", "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(video_target),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            frame = render_frame(project, i, manager_root=manager_root)
            if frame.size != (stage_w, stage_h):
                frame = frame.resize((stage_w, stage_h))
            proc.stdin.write(frame.convert("RGB").tobytes())
            if progress is not None:
                progress(i + 1, n)
        proc.stdin.close()
        stderr = proc.stderr.read()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg failed (rc={rc}): {stderr.decode(errors='replace')}")
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise

    if has_audio:
        mux_cmd = [
            binary, "-y", "-i", str(video_target), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out),
        ]
        mux = subprocess.run(mux_cmd, capture_output=True)
        try:
            video_target.unlink(missing_ok=True)
        except Exception:
            pass
        if mux.returncode != 0:
            raise RuntimeError(
                f"ffmpeg mux failed (rc={mux.returncode}): "
                f"{mux.stderr.decode(errors='replace')}")
    return out
