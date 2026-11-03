"""AI provider adapters + scene generation pipeline (GUI-free)."""

import pytest

from ai import (
    ANIMATION_INSTRUCTION_PROMPT,
    MockProvider,
    ProviderManager,
    ProviderNotConfiguredError,
    SCENE_GENERATION_PROMPT,
    apply_scene_output,
    validate_scene_output,
)
from ai.providers import OpenAIProvider
from app.controller import AppController


@pytest.fixture
def controller(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return AppController()


def test_mock_provider_text_and_structured():
    p = MockProvider()
    r = p.generate_text("hello")
    assert r.text.startswith("[mock]")
    s = p.generate_structured("brief", {})
    assert s.structured is not None
    assert validate_scene_output(s.structured) == []


def test_provider_manager_lists_and_creates_mock():
    mgr = ProviderManager()
    assert "mock" in mgr.available()
    provider = mgr.create("mock")
    assert provider.name == "mock"


def test_unconfigured_provider_raises():
    import os
    os.environ.pop("OPENAI_API_KEY", None)
    with pytest.raises(ProviderNotConfiguredError):
        OpenAIProvider("")


def test_validate_scene_output_rejects_bad():
    assert validate_scene_output({"foo": 1})  # missing objects
    errors = validate_scene_output({
        "objects": [{"type": "rect"}],  # missing name
        "actions": [{"action": "explode", "start": 1.5, "end": 10}],
        "duration_frames": "x",
    })
    assert any("missing name" in e for e in errors)
    assert any("unknown action" in e for e in errors)
    assert any("must be an integer" in e for e in errors)
    assert any("duration_frames" in e for e in errors)


def test_apply_scene_output_creates_objects_and_actions(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    provider = MockProvider()
    result = provider.generate_structured("a brief", {})
    apply_scene_output(controller, scene_id, result.structured,
                       controller.project.settings.width,
                       controller.project.settings.height)
    scene = controller.project.scene_by_id(scene_id)
    names = {o.name for o in scene.objects}
    assert "Hero Box" in names
    assert "Title" in names
    # The bob action landed on the rect.
    box = next(o for o in scene.objects if o.name == "Hero Box")
    assert "y" in box.tracks and box.tracks["y"]
    assert scene.name == "AI Scene"


def test_apply_scene_output_rejects_invalid(controller, tmp_path):
    controller.new_project(tmp_path / "p", "P")
    scene_id = controller.current_scene_id
    with pytest.raises(ValueError):
        apply_scene_output(controller, scene_id, {"objects": "nope"},
                           1920, 1080)


def test_prompt_templates_render():
    prompt = SCENE_GENERATION_PROMPT.render(
        brief="a cat walking", width=1920, height=1080, fps=30, duration=150)
    assert "a cat walking" in prompt
    assert "1920x1080" in prompt
    instr = ANIMATION_INSTRUCTION_PROMPT.render(
        intent="wave", target="Arm", start=0, end=60)
    assert "wave" in instr and "Arm" in instr


def test_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    from ai.settings import load_settings, save_settings
    s = load_settings()
    s.openai_api_key = "sk-test"
    s.default_provider = "openai"
    save_settings(s)
    reloaded = load_settings()
    assert reloaded.openai_api_key == "sk-test"
    assert reloaded.default_provider == "openai"
