# Architecture Overview

MOVEXA keeps three layers strictly separated: data, engine, and UI.

## Layers

- `project/` — pure data model (schema, manager, assets). No Qt, no rendering.
- `engine/` — deterministic animation evaluation: scene graph, keyframes,
  tracks, playback, rigs, actions, transitions, renderer.
- `app/` — PySide6 widgets and the `AppController` bridge. Widgets stay thin;
  every mutation goes through the controller and is announced on the event bus.
- `ai/` — provider adapters and prompt management. The engine never imports
  an AI SDK.
- `core/` — event bus.

## Determinism

- Time is stored as integer frames only. There is no floating-point time.
- `engine/keyframes.py` evaluates keyframes with pure functions.
- `render_frame(project, global_frame)` produces identical bytes for the same
  inputs, which is what makes exports reproducible.

## Lossless schema

`project/schema.py` v1.0 keeps unknown fields at every level in `extras`
dicts and preserves unknown track property names. A project saved by a newer
version can be opened by an older one without losing data.

## Cut-out rigs

A rig is plain parented `SceneObject`s carrying role metadata in
`extras["rig"]`. Pivot points (`pivot_x`, `pivot_y`) make a limb rotate
around its joint while children follow rigidly. Actions (`walk`, `wave`, ...)
are sampled into ordinary keyframes, so storage stays flat JSON and the
evaluator never executes generated code.

## Scene transitions

`Scene.transition` plus `transition_frames` describe the handoff into the next
scene. Both the canvas preview and the frame renderer consume the same
`transition_plan`, so preview and export agree.
