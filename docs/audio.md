# Audio and Subtitles

## Clips

Audio clips (voiceover, music, sound effects) are imported with
`AppController.add_audio_clip`, which copies the file into
`assets/audio/` under the project directory and records its path in the
project file (`Project.audio_clips`). Each clip carries `start_frame`,
`duration_frames`, `volume`, and a mixer `track`. Paths are stored relative
to the project directory so projects stay portable.

## Subtitles

Subtitles are frame-based entries in `Project.subtitles` with
`start_frame`, `end_frame`, and `text`. They round-trip through the schema
and can be converted to/from `.srt` with `audio.to_srt` / `audio.from_srt`.

## Mixing

`audio.mix_clips` blends every clip into a single WAV (`exports/mixed.wav`)
at the project fps/total duration, volumes applied, peak-normalized. WAV is
read with the stdlib `wave` module; other formats only need ffprobe for the
duration right now.

## Export integration

`AppController.export_video` automatically mixes the project's clips and
muxes the result into the exported MP4 as AAC. Projects without clips
export unchanged.

## Lip sync

`audio.lip_sync_envelope` derives a per-frame "mouth open" value (0..1) from
the audio energy; `AppController.apply_lip_sync` samples that envelope into
`scale_y` keyframes on any chosen object, so a simple talking-jaw rig can be
keyed automatically.
