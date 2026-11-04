# AI Providers

MOVEXA uses a provider adapter pattern: the animation engine never imports an
AI SDK. Providers implement `BaseProvider` and return plain Python data.

## Available providers

- `mock` — deterministic, offline, used for tests and authoring.
- `openai`, `anthropic`, `gemini` — require an API key. Adapters are present
  but need their SDK installed; without a key they raise
  `ProviderNotConfiguredError`.

## API keys

Keys are stored in user-level storage (`%APPDATA%/movexa/ai_settings.json`),
never in project files, so projects stay portable.

```python
from ai.settings import load_settings, save_settings
settings = load_settings()
settings.openai_api_key = "sk-..."
save_settings(settings)
```

Environment variables `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and
`GEMINI_API_KEY` are also honored.

## Scene generation pipeline

1. Build a prompt with `PromptTemplate.render`.
2. Call `provider.generate_structured(prompt, schema)`.
3. Validate with `validate_scene_output` (returns a list of errors).
4. Apply with `apply_scene_output`, which creates objects and routes actions
   through `AppController.apply_action`.

## AI agent in the editor

`app/agent.py` + `app/agent_panel.py` expose the pipeline as a chat dock:

- local intents ("add rect at 600,300", "spin 0-60") are deterministic and
  run directly through the controller — no provider needed;
- "outline: …" flows through `generate_text` (mock returns a deterministic
  outline offline);
- "generate a scene: …" flows through `generate_structured` on a worker
  thread; validated JSON is applied back on the GUI thread.

## Controlled instruction format

Only the actions defined by the engine are allowed:
`spin`, `fade_in`, `fade_out`, `bob`, `idle`, `walk`, `wave`, `jump`.
Unknown actions are rejected by validation before any keyframe is written.
