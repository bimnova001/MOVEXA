"""AI provider adapters (architecture doc: provider adapter pattern, Priority 5).

The animation engine never imports a provider SDK. Providers implement the
``BaseProvider`` protocol and return plain Python data; the prompt manager and
output validator sit between them and the scene model.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a provider needs an API key that is not set."""


class ProviderError(RuntimeError):
    """Raised when a provider call fails or returns unusable output."""


@dataclass
class ProviderResult:
    text: str
    structured: dict[str, Any] | None = None
    raw: Any = None


class BaseProvider(Protocol):
    name: str

    def generate_text(self, prompt: str) -> ProviderResult: ...

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> ProviderResult: ...


@dataclass
class ProviderSettings:
    """API keys live in user-level storage, never in project files."""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    default_provider: str = "mock"

    @classmethod
    def from_env(cls) -> "ProviderSettings":
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            default_provider=os.environ.get("MOVEXA_AI_PROVIDER", "mock"),
        )


class MockProvider:
    """Deterministic provider used for tests and offline authoring.

    It does not call any network. Given a prompt it returns a small, valid
    scene instruction set so the full pipeline can be exercised anywhere.
    """

    name = "mock"

    def generate_text(self, prompt: str) -> ProviderResult:
        return ProviderResult(text=f"[mock] {prompt.strip()[:120]}")

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> ProviderResult:
        # Minimal valid scene: one rect that bobs, one character that walks.
        payload = {
            "scene_name": "AI Scene",
            "duration_frames": 150,
            "objects": [
                {"type": "rect", "name": "Hero Box", "x": 400, "y": 300,
                 "color": "#22d3ee"},
                {"type": "text", "name": "Title", "text": "MOVEXA",
                 "x": 960, "y": 120, "color": "#ffffff"},
            ],
            "actions": [
                {"target": "Hero Box", "action": "bob", "start": 0, "end": 149},
            ],
        }
        return ProviderResult(text=json.dumps(payload), structured=payload)


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderNotConfiguredError(
                "OpenAI API key missing; set OPENAI_API_KEY or ai_settings.json")
        self.api_key = api_key

    def generate_text(self, prompt: str) -> ProviderResult:
        raise ProviderError("OpenAI adapter requires the openai SDK; not installed in this build")

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> ProviderResult:
        raise ProviderError("OpenAI adapter requires the openai SDK; not installed in this build")


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderNotConfiguredError(
                "Anthropic API key missing; set ANTHROPIC_API_KEY or ai_settings.json")
        self.api_key = api_key

    def generate_text(self, prompt: str) -> ProviderResult:
        raise ProviderError("Anthropic adapter requires the anthropic SDK; not installed in this build")

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> ProviderResult:
        raise ProviderError("Anthropic adapter requires the anthropic SDK; not installed in this build")


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderNotConfiguredError(
                "Gemini API key missing; set GEMINI_API_KEY or ai_settings.json")
        self.api_key = api_key

    def generate_text(self, prompt: str) -> ProviderResult:
        raise ProviderError("Gemini adapter requires the google-generativeai SDK; not installed in this build")

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> ProviderResult:
        raise ProviderError("Gemini adapter requires the google-generativeai SDK; not installed in this build")


class ProviderManager:
    """Registry + factory. The animation engine depends only on this facade."""

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        self.settings = settings or ProviderSettings.from_env()
        self._registry: dict[str, type] = {
            "mock": MockProvider,
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "gemini": GeminiProvider,
        }

    def available(self) -> list[str]:
        return sorted(self._registry)

    def create(self, name: str | None = None) -> BaseProvider:
        name = name or self.settings.default_provider
        if name not in self._registry:
            raise ProviderError(f"unknown provider: {name}")
        cls = self._registry[name]
        if cls is MockProvider:
            return MockProvider()
        if cls is OpenAIProvider:
            return OpenAIProvider(self.settings.openai_api_key)
        if cls is AnthropicProvider:
            return AnthropicProvider(self.settings.anthropic_api_key)
        if cls is GeminiProvider:
            return GeminiProvider(self.settings.gemini_api_key)
        raise ProviderError(f"provider not wired: {name}")

    def register(self, name: str, cls: type) -> None:
        self._registry[name] = cls


@dataclass
class PromptTemplate:
    """A controlled prompt with a version so regeneration is reproducible."""

    name: str
    version: str
    system: str
    user: str

    def render(self, **kwargs: Any) -> str:
        return self.system + "\n\n" + self.user.format(**kwargs)


SCENE_GENERATION_PROMPT = PromptTemplate(
    name="scene_generation",
    version="1.0",
    system=("You are MOVEXA's scene generator. Return ONLY JSON matching the "
            "provided schema. Use integer frames. Never invent unknown actions."),
    user=("Generate a scene for: {brief}\n"
          "Stage: {width}x{height}, {fps} fps, up to {duration} frames."),
)

ANIMATION_INSTRUCTION_PROMPT = PromptTemplate(
    name="animation_instruction",
    version="1.0",
    system=("Convert the user's intent into MOVEXA animation instructions. "
            "Return ONLY JSON with an 'actions' array. Allowed actions: "
            "spin, fade_in, fade_out, bob, idle, walk, wave, jump."),
    user=("Intent: {intent}\nTarget object: {target}\nFrame window: {start}..{end}"),
)


def validate_scene_output(data: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty == valid)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["output must be a JSON object"]
    if "objects" not in data or not isinstance(data["objects"], list):
        errors.append("objects must be a list")
    else:
        for i, obj in enumerate(data["objects"]):
            if not isinstance(obj, dict):
                errors.append(f"objects[{i}] must be an object")
                continue
            if "type" not in obj:
                errors.append(f"objects[{i}] missing type")
            if "name" not in obj:
                errors.append(f"objects[{i}] missing name")
    if "actions" in data and not isinstance(data["actions"], list):
        errors.append("actions must be a list")
    else:
        for i, act in enumerate(data.get("actions", [])):
            if not isinstance(act, dict):
                errors.append(f"actions[{i}] must be an object")
                continue
            if act.get("action") not in {
                "spin", "fade_in", "fade_out", "bob", "idle", "walk", "wave", "jump"
            }:
                errors.append(f"actions[{i}] unknown action {act.get('action')!r}")
            for key in ("start", "end"):
                if key in act and not isinstance(act[key], int):
                    errors.append(f"actions[{i}].{key} must be an integer")
    if "duration_frames" in data and not isinstance(data["duration_frames"], int):
        errors.append("duration_frames must be an integer")
    return errors


def apply_scene_output(controller, scene_id: str, data: dict[str, Any],
                      stage_width: int, stage_height: int) -> None:
    """Apply a validated AI scene output to an existing scene.

    Objects are created; actions are routed through AppController.apply_action
    so they go through the same validation as hand-authored ones.
    """
    errors = validate_scene_output(data)
    if errors:
        raise ValueError("; ".join(errors))
    name_to_id: dict[str, str] = {}
    for obj in data.get("objects", []):
        created = controller.add_object(
            scene_id, type=obj.get("type", "rect"),
            name=obj.get("name", obj.get("type", "rect")),
            x=float(obj.get("x", stage_width / 2)),
            y=float(obj.get("y", stage_height / 2)),
            color=obj.get("color", "#7c4dff"),
            text=obj.get("text", ""),
        )
        name_to_id[created.name] = created.id
        # Also map by requested name in case uniquification renamed it.
        name_to_id[obj.get("name", "")] = created.id
    for act in data.get("actions", []):
        target_name = act.get("target")
        target_id = name_to_id.get(target_name)
        if target_id is None:
            continue
        try:
            controller.apply_action(
                scene_id, target_id, act["action"],
                int(act["start"]), int(act["end"]))
        except (ValueError, KeyError):
            # Skip actions that do not apply (e.g. rig action on a plain object);
            # the rest of the scene still lands.
            continue
    if "duration_frames" in data:
        controller.update_scene_metadata(
            scene_id, duration_frames=int(data["duration_frames"]))
    if data.get("scene_name"):
        controller.update_scene_metadata(scene_id, name=str(data["scene_name"]))
