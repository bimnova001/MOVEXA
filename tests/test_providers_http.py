"""HTTP provider adapters: parsing, error mapping and settings plumbing.

Network I/O is monkeypatched; the adapters themselves stay stdlib-only so
no provider SDK is required.
"""

from __future__ import annotations

import io
import json
import os
import urllib.error

import pytest

from ai._impl import (
    AnthropicProvider,
    GeminiProvider,
    MockProvider,
    OpenAIProvider,
    ProviderError,
    ProviderManager,
    ProviderNotConfiguredError,
    ProviderSettings,
    _loads_payload,
    _post,
)
from ai.settings import load_settings, save_settings, settings_path


# -- JSON payload extraction ---------------------------------------------------

def test_loads_payload_tolerates_fences_and_prose() -> None:
    fenced = "```json\n{\"a\": 1}\n```"
    prose = 'Sure! Here it is: {"a": {"b": 2}} — hope that helps.'
    assert _loads_payload(fenced) == {"a": 1}
    assert _loads_payload(prose) == {"a": {"b": 2}}


def test_loads_payload_rejects_non_json() -> None:
    with pytest.raises(ProviderError):
        _loads_payload("no object here")
    with pytest.raises(ProviderError):
        _loads_payload("{broken json")


# -- stdlib POST error mapping ---------------------------------------------------

def test_post_maps_http_error_to_provider_error(monkeypatch) -> None:
    def fake_urlopen(_request, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(
            "https://unit.test", 429, "Too Many Requests", {},
            io.BytesIO(b'{"error": "rate limited"}'))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(ProviderError, match="HTTP 429"):
        _post("https://unit.test", {}, {"any": 1})


# -- OpenAI / Anthropic / Gemini adapters -----------------------------------------

def _openai_response(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


def _anthropic_response(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def _gemini_response(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_openai_provider_defaults_and_structured(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_post(_url, _headers, payload):
        calls.append(payload)
        return _openai_response('{"scene_name": "X", "objects": [{"type": "rect"}]}')

    monkeypatch.setattr("ai._impl._post", fake_post)
    provider = OpenAIProvider("sk-unit")  # default model kicks in
    assert provider.model == "gpt-4o-mini"
    result = provider.generate_structured("brief", {"type": "object"})
    assert result.structured == {"scene_name": "X", "objects": [{"type": "rect"}]}
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_anthropic_provider_structured(monkeypatch) -> None:
    def fake_post(_url, _headers, payload):
        assert payload["system"].startswith("Respond with ONLY")
        return _anthropic_response('{"objects": [], "actions": []}')

    monkeypatch.setattr("ai._impl._post", fake_post)
    provider = AnthropicProvider("sk-ant-unit", model="claude-x")
    assert provider.model == "claude-x"
    result = provider.generate_structured("brief", {})
    assert result.structured == {"objects": [], "actions": []}


def test_gemini_provider_structured(monkeypatch) -> None:
    def fake_post(_url, _headers, payload):
        assert payload["generationConfig"]["response_mime_type"] == "application/json"
        return _gemini_response('{"objects": [{"type": "text"}]}')

    monkeypatch.setattr("ai._impl._post", fake_post)
    provider = GeminiProvider("g-unit")
    assert provider.model == "gemini-2.0-flash"
    result = provider.generate_structured("brief", {})
    assert result.structured == {"objects": [{"type": "text"}]}


def test_providers_require_keys() -> None:
    with pytest.raises(ProviderNotConfiguredError):
        OpenAIProvider("")
    with pytest.raises(ProviderNotConfiguredError):
        AnthropicProvider("")
    with pytest.raises(ProviderNotConfiguredError):
        GeminiProvider("")


def test_provider_manager_passes_model_settings() -> None:
    settings = ProviderSettings(
        openai_api_key="k1", openai_model="gpt-custom",
        anthropic_api_key="k2", anthropic_model="claude-custom",
        gemini_api_key="k3", gemini_model="gemini-custom")
    manager = ProviderManager(settings)
    assert manager.create("openai").model == "gpt-custom"
    assert manager.create("anthropic").model == "claude-custom"
    assert manager.create("gemini").model == "gemini-custom"


# -- user-level settings round trip ------------------------------------------------

def test_settings_round_trip_includes_models_and_keys() -> None:
    settings = ProviderSettings(
        openai_api_key="sk-a", anthropic_api_key="sk-b", gemini_api_key="sk-c",
        openai_model="gpt-x", anthropic_model="claude-y", gemini_model="gemini-z",
        default_provider="anthropic")
    save_settings(settings)
    loaded = load_settings()
    assert loaded == settings
    # mock provider keeps working offline after any settings change.
    assert isinstance(ProviderManager(loaded).create("mock"), MockProvider)


def test_settings_file_stays_out_of_project() -> None:
    save_settings(ProviderSettings(openai_api_key="sk-secret"))
    path = settings_path()
    # The autouse fixture points APPDATA at tmp_path; the file must follow
    # the APPDATA redirect, never the working directory.
    from pathlib import Path
    assert path == Path(os.environ["APPDATA"]) / "movexa" / "ai_settings.json"
    assert json.loads(path.read_text(encoding="utf-8"))["openai_api_key"] == "sk-secret"
