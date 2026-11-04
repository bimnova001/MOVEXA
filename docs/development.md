# Development Guide

## Running

```pwsh
pip install -r requirements.txt
python main.py            # desktop app
python -m pytest tests   # GUI-free test suite
python scripts/smoke_gui.py  # headless render smoke test
```

## Startup flow

`main.py` opens `app/loading_screen.py` first; `app/envcheck.py`
(Qt-free) runs machine/library checks — Python 3.10+, PySide6, Pillow, numpy,
FFmpeg on PATH, writable user storage — on a worker thread while the
checklist streams results.
Only when every required check passes does the menu (`app/dashboard.py`,
an editor-style home screen with recent-project cards) open automatically.

## GUI smoke outputs

`scripts/smoke_gui.py` captures PNGs into `scripts/_smoke_out/`:
`loading.png`, `menu.png`, `workspace.png`, keyframe comparisons and a
save/reopen render. Review these screenshots when touching the theme
(`app/theme.py`), dashboard or workspace layout.

## Conventions

- Run from the repository root; imports are top-level module names.
- Comments explain why, not what. No section divider banners, no docstrings
  that restate the name.
- Functional implementations only; no placeholders in completed features.
- Tests must be GUI-free where possible; the controller is deliberately
  Qt-free.

## Undo/redo

`app/undo.py` keeps a bounded snapshot history (project data before/after
each mutation); every `UNDOABLE_METHODS` entry in `app/controller.py` is
wrapped automatically, so adding a new mutating method to that tuple is all
it takes. Project lifecycle (new/open/close/save) and playback are outside
history by design. The Edit menu and the Ctrl+K command palette drive it.

## Adding a provider

1. Subclass the adapter in `ai/providers.py`.
2. Register it in `ProviderManager._registry`.
3. Add a settings field and storage entry in `ai/settings.py`.

## AI agent

`app/agent.py` routes editor chat (Qt-free): local intents ("add rect at
600,300", "spin 0-60") execute deterministically through the controller =
fully offline; "outline …" and "generate a scene …" go to the provider —
the Mock provider answers offline, real providers need keys in
`%APPDATA%/movexa/ai_settings.json`. Provider round-trips run on a
QThread in `app/agent_panel.py`, and returning JSON crosses
`validate_scene_output` before `apply_scene_output` mutates the project on
the GUI thread.

## Adding an action

1. Implement the handler in `engine/actions.py`.
2. Add it to `ACTIONS` and `_HANDLERS`.
3. Add a label in `app/panels.py` `ACTION_LABELS`.

## Documentation

All markdown under `docs/` and `README.md` is written in English and references
the SVG logo at `resources/branding/logo.svg`.
