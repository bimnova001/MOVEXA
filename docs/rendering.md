# Rendering and Export

## Frame renderer

`engine/renderer.py` exposes `render_frame(project, global_frame)` which maps a
global frame index to the correct scene and local frame, applies camera,
evaluates every object through the scene graph, and composites transitions.

Rendering does not depend on preview playback speed. Frame 0, 30, and 300 always
produce the same state, which is what makes exports reproducible.

## MP4 export

`export_video` pipes raw RGB frames into an `ffmpeg` subprocess (libx264,
yuv420p). FFmpeg must be available on `PATH`; otherwise
`FFmpegUnavailableError` is raised with a clear message.

When the project contains audio clips, the clips are mixed into
`exports/mixed.wav` first, then muxed into the final MP4 as an AAC track
(video is encoded first to avoid piping raw frames together with a file
input, which deadlocks some ffmpeg builds).

```pwsh
# verify ffmpeg is available
ffmpeg -version
```

From the UI: Workspace -> "Export MP4". From code:

```python
controller.export_video("out.mp4")  # audio mixed automatically
```

## Determinism checklist

- Integer frames only.
- No wall-clock timing in evaluation.
- Assets are resolved by relative path under the project directory.
- Camera state is evaluated from keyframes, never from UI state.
