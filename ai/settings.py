"""User-level AI settings storage (API keys never go into project files)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from ai._impl import ProviderSettings


def settings_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home())) / "movexa"
    base.mkdir(parents=True, exist_ok=True)
    return base / "ai_settings.json"


def load_settings() -> ProviderSettings:
    path = settings_path()
    if not path.exists():
        return ProviderSettings.from_env()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ProviderSettings.from_env()
    settings = ProviderSettings.from_env()
    for key in ("openai_api_key", "anthropic_api_key", "gemini_api_key",
                "openai_model", "anthropic_model", "gemini_model",
                "default_provider"):
        if key in data:
            setattr(settings, key, data[key])
    return settings


def save_settings(settings: ProviderSettings) -> None:
    data = {
        "openai_api_key": settings.openai_api_key,
        "anthropic_api_key": settings.anthropic_api_key,
        "gemini_api_key": settings.gemini_api_key,
        "openai_model": settings.openai_model,
        "anthropic_model": settings.anthropic_model,
        "gemini_model": settings.gemini_model,
        "default_provider": settings.default_provider,
    }
    settings_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
