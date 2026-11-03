# Development Guide

## Running

```pwsh
pip install -r requirements.txt
python main.py            # desktop app
python -m pytest tests   # GUI-free test suite
python scripts/smoke_gui.py  # headless render smoke test
```

## Conventions

- Run from the repository root; imports are top-level module names.
- Comments explain why, not what. No section divider banners, no docstrings
  that restate the name.
- Functional implementations only; no placeholders in completed features.
- Tests must be GUI-free where possible; the controller is deliberately
  Qt-free.

## Adding a provider

1. Subclass the adapter in `ai/providers.py`.
2. Register it in `ProviderManager._registry`.
3. Add a settings field and storage entry in `ai/settings.py`.

## Adding an action

1. Implement the handler in `engine/actions.py`.
2. Add it to `ACTIONS` and `_HANDLERS`.
3. Add a label in `app/panels.py` `ACTION_LABELS`.

## Documentation

All markdown under `docs/` and `README.md` is written in English and references
the SVG logo at `resources/branding/logo.svg`.
