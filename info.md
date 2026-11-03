# MOVEXA — AI-Powered 2D Animation & Video Production Studio

> **Project Type:** Desktop Application  
> **Platform:** Windows 11  
> **Primary Focus:** AI-Assisted 2D Cut-out Animation  
> **Project Status:** Planning & Architecture  
> **Project Vision:** Make professional 2D animation accessible to everyone.

---

# 1. Project Overview

MOVEXA is an AI-powered desktop application designed to simplify and improve the 2D animation and video production workflow.

The application aims to allow users to create animated explainer videos, educational content, storytelling videos, presentations, and other animated media without requiring advanced animation skills.

MOVEXA combines AI-assisted content generation with a dedicated animation production environment.

Unlike workflows that depend on generating animations inside external AI chat interfaces or temporary artifacts, MOVEXA provides its own workspace, animation engine, timeline, character system, scene editor, audio synchronization, and video rendering pipeline.

The application should give users control over the entire production process.

# 2. Problem Statement

Current AI animation workflows often depend on multiple external services and tools.

A typical workflow might involve:

1. Using ChatGPT to generate a script and storyboard.
2. Sending the script and shot list to Claude.
3. Asking Claude to generate HTML5 Canvas animation inside an Artifact.
4. Using the Artifact to preview the animation.
5. Extracting or reconstructing the generated animation.
6. Combining scenes, voiceovers, subtitles, and sound effects.
7. Exporting the final video using another application.

However, this approach has several limitations:

- Limited context and output length.
- Restricted animation complexity.
- Difficulties generating complete 60-second or longer animations.
- Limited timeline editing capabilities.
- Limited character rigging and animation control.
- Difficulties maintaining consistent characters across scenes.
- Limited audio and lip-sync synchronization.
- Generated artifacts may not provide a reusable project structure.
- Users have limited control over rendering and export.
- Repeated prompting is required to fix small animation problems.

MOVEXA aims to solve these problems by providing an integrated animation production environment.

# 3. Main Vision

MOVEXA should become a standalone AI-assisted animation studio.

The core principle is:

**AI creates the assets and assists with production. MOVEXA controls the animation, timeline, editing, and rendering.**

The application must not depend on Claude Artifacts, ChatGPT Artifacts, or another external chat interface as its animation runtime.

External AI providers should only be used for specific tasks through configurable integrations.

# 4. Target Users

MOVEXA is designed for:

- Beginners who want to create animated videos.
- Students creating educational projects.
- Teachers creating learning materials.
- Content creators producing explainer videos.
- Small businesses creating promotional videos.
- Independent animators.
- Developers and advanced users who want AI-assisted animation workflows.

The application should be approachable for beginners while remaining flexible enough for advanced users.

# 5. Core Design Principles

## 5.1 Standalone Desktop Application

MOVEXA must operate as an independent Windows desktop application.

Users should be able to:

- Create projects.
- Save and reopen projects.
- Manage animation assets.
- Edit scenes.
- Control animation timelines.
- Preview animations.
- Import audio.
- Export completed videos.

## 5.2 AI-Assisted, Not AI-Locked

Users must be able to choose which AI provider handles each task.

The application should support:

- Manual AI provider selection.
- Automatic provider selection.
- Custom API endpoints where supported.
- User-provided API keys.
- Model selection.
- Provider-specific configuration.

Users should not be locked into one AI provider.

## 5.3 Native Animation Engine

MOVEXA must implement its own animation playback and rendering system.

The animation engine should support:

- Timeline-based animation.
- Keyframes.
- Character rigging.
- Scene transitions.
- Camera movement.
- Animation layers.
- Audio tracks.
- Subtitle tracks.
- Frame-based playback.
- Video rendering.

The animation engine must work independently of the AI provider.

# 6. Core Features

## 6.1 AI Script Generator

Generate or improve video scripts using AI.

Features:

- Generate scripts from user topics.
- Support Thai and English.
- Define video duration.
- Define target audience.
- Define storytelling style.
- Generate narration.
- Generate scene descriptions.
- Generate shot lists.
- Generate timestamps.
- Allow manual editing.

Output should use a structured format such as JSON.

## 6.2 Storyboard & Scene Generator

Convert scripts into individual scenes.

Each scene should contain:

- Scene ID.
- Scene duration.
- Narration.
- Visual description.
- Character references.
- Background description.
- Camera instructions.
- Animation instructions.
- Subtitle content.
- Sound effect instructions.

Users must be able to add, remove, reorder, duplicate, and edit scenes.

Scene generation should be independent, allowing users to regenerate only the selected scene instead of the entire video.

## 6.3 AI Asset Generator

Generate visual assets required for animation.

Supported assets:

- Characters.
- Character expressions.
- Character poses.
- Backgrounds.
- Props.
- Objects.
- Icons.
- Infographics.
- Diagrams.

The system should prioritize visual consistency across scenes.

Assets should be reusable across different projects.

## 6.4 Character Rigging System

Implement a 2D cut-out character system.

Character components may include:

- Head.
- Body.
- Upper arms.
- Lower arms.
- Hands.
- Upper legs.
- Lower legs.
- Feet.
- Eyes.
- Eyebrows.
- Mouth.

Required capabilities:

- Bone-based or hierarchical rigging.
- Parent-child relationships.
- Pivot point configuration.
- Rotation and translation.
- Keyframe animation.
- Expression switching.
- Eye blinking.
- Mouth movement.
- Walking.
- Running.
- Idle animation.
- Emotional expressions.

The system should support reusable character rigs.

Users should be able to reuse the same character across multiple scenes.

## 6.5 Animation Timeline

The timeline is one of the most important components of MOVEXA.

It should provide centralized control over the entire animation.

Required timeline tracks:

1. Scene Track.
2. Character Track.
3. Background Track.
4. Object / Prop Track.
5. Camera Track.
6. Subtitle Track.
7. Voiceover Track.
8. Sound Effects Track.
9. Music Track.

Required controls:

- Play.
- Pause.
- Stop.
- Replay.
- Frame stepping.
- Seek bar.
- Playback speed.
- Keyframe editing.
- Track visibility.
- Track locking.
- Track arrangement.
- Timeline zoom.
- Timeline scrolling.

The timeline must support accurate synchronization between animation, narration, subtitles, and sound effects.

## 6.6 Scene Composer

Provide an editor for arranging visual elements.

Features:

- Canvas preview.
- Character positioning.
- Object positioning.
- Background selection.
- Layer management.
- Camera framing.
- Camera pan.
- Camera zoom.
- Scene transitions.
- Element scaling and rotation.

Users should be able to adjust scenes manually after AI generation.

## 6.7 Camera System

Support cinematic camera movements:

- Wide Shot.
- Medium Shot.
- Close-up.
- Pan.
- Zoom In.
- Zoom Out.
- Follow Camera.
- Static Camera.

Camera movements should be controlled through keyframes.

## 6.8 Audio System

Support importing and managing audio files.

Supported audio types should include common formats such as:

- WAV.
- MP3.
- AAC.
- M4A.

Features:

- Thai voiceover support.
- English voiceover support.
- Multiple audio tracks.
- Voiceover timeline.
- Sound effects timeline.
- Background music.
- Audio trimming.
- Volume adjustment.
- Fade in / Fade out.
- Audio synchronization.

### Voice and Lip Sync

The application must distinguish between narration and sound effects.

Sound effects must never be treated as voiceover.

Lip-sync should support:

- Audio waveform analysis.
- Speech timing.
- Phoneme or viseme mapping where available.
- Mouth shape switching.
- Timeline-based manual correction.

If no voiceover exists, MOVEXA should generate a voice script with timestamps for later recording or TTS generation.

## 6.9 Subtitle System

Features:

- Automatic subtitle generation.
- Thai subtitle support.
- English subtitle support.
- Manual subtitle editing.
- Subtitle timing.
- Subtitle styling.
- Keyword highlighting.
- Subtitle animation.
- Timeline synchronization.

## 6.10 Video Rendering & Export

MOVEXA must have its own rendering pipeline.

Use FFmpeg or another suitable rendering backend.

Required export options:

- MP4.
- H.264.
- 1080p.
- 720p.
- 30 FPS.
- 60 FPS.
- 16:9.
- 9:16.
- 1:1.

Rendering should support:

- Multiple scenes.
- Character animation.
- Camera animation.
- Subtitles.
- Voiceover.
- Sound effects.
- Background music.
- Scene transitions.

Export should not require opening an external AI chat interface.

# 7. AI Provider Architecture

MOVEXA should use a modular provider architecture.

Potential integrations:

- OpenAI.
- Google Gemini.
- Anthropic Claude.
- OpenRouter.
- Other compatible providers.
- Local AI models.
- Custom API endpoints.

Provider responsibilities may include:

| Task | AI Responsibility |
|---|---|
| Script | Generate narration and dialogue |
| Storyboard | Create scene descriptions |
| Shot Planning | Suggest camera and shot composition |
| Image Generation | Generate characters and assets |
| Animation Planning | Generate structured animation instructions |
| Voice Generation | Generate narration |
| Speech Analysis | Assist with lip-sync timing |

Not every provider needs to support every task.

The system should detect provider capabilities and allow users to select alternatives.

## 7.1 API Key Management

Users provide their own API keys.

Requirements:

- Secure local storage.
- Never hardcode API keys.
- Never expose API keys in project files.
- Allow users to update or remove keys.
- Validate API connections.
- Support multiple providers.
- Support multiple models per provider.

# 8. Structured Animation Data

AI-generated instructions must be converted into structured data before being executed by the animation engine.

Do not rely on large blocks of generated HTML or JavaScript as the primary project format.

Example project structure:

    project/
    ├── project.json
    ├── assets/
    │   ├── characters/
    │   ├── backgrounds/
    │   ├── props/
    │   └── audio/
    ├── scenes/
    │   ├── scene_001.json
    │   ├── scene_002.json
    │   └── scene_003.json
    ├── subtitles/
    ├── audio/
    └── exports/

Example animation instruction:

    {
      "scene_id": "scene_001",
      "duration": 15,
      "fps": 30,
      "characters": [
        {
          "id": "character_001",
          "actions": [
            {
              "type": "walk",
              "start": 0,
              "end": 3,
              "position": {
                "x": 300,
                "y": 900
              }
            },
            {
              "type": "wave",
              "start": 3,
              "end": 5
            }
          ]
        }
      ]
    }

This is an illustrative format. The final schema should be versioned and validated.

# 9. Recommended Technology Stack

The technology stack should prioritize Windows desktop compatibility, maintainability, and rendering performance.

Potential technologies:

| Component | Suggested Technology |
|---|---|
| Desktop GUI | Python + PySide6 |
| Animation Engine | Custom 2D Engine |
| Animation Preview | Qt Graphics / OpenGL |
| Data Format | JSON |
| Project Database | SQLite |
| Video Rendering | FFmpeg |
| AI Integration | Python API Adapters |
| Image Processing | Pillow / OpenCV |
| Audio Processing | FFmpeg / librosa |
| Configuration | JSON / SQLite |

Technology choices may be revised during architecture development.

Avoid unnecessary dependencies and oversized frameworks.

# 10. Application Interface

The application should have a modern desktop interface.

Main workspace:

1. Project Dashboard.
2. Script Editor.
3. Storyboard Editor.
4. Asset Library.
5. Character Editor.
6. Scene Editor.
7. Animation Timeline.
8. Audio Editor.
9. Export Manager.
10. AI Provider Settings.

The main editing workspace should prioritize:

- Scene preview in the center.
- Timeline at the bottom.
- Asset and layer panels.
- Properties and animation controls.
- AI assistant panel.

The interface should remain understandable for beginners.

# 11. Workflow

Expected production workflow:

1. Create a new project.
2. Enter a video topic or import a script.
3. Generate or edit the script.
4. Generate storyboard and shot list.
5. Generate or import visual assets.
6. Create or select character rigs.
7. Generate animation instructions.
8. Build scene animations.
9. Edit keyframes and camera movements.
10. Add narration and sound effects.
11. Synchronize subtitles and lip movements.
12. Preview the complete video.
13. Render and export the final video.

Users must be able to manually edit every important production stage.

# 12. Development Roadmap

Development should be incremental.

## Phase 1 — Foundation

- Establish project structure.
- Create desktop application.
- Build main interface.
- Implement project management.
- Implement JSON-based project format.
- Implement asset management.

## Phase 2 — Animation Engine

- Create canvas renderer.
- Implement scene system.
- Implement animation timeline.
- Implement keyframes.
- Implement camera controls.
- Implement basic transitions.

## Phase 3 — Character Animation

- Character hierarchy.
- Basic bone rigging.
- Character movement.
- Facial expressions.
- Eye blinking.
- Mouth animation.
- Reusable character rigs.

## Phase 4 — AI Integration

- AI provider manager.
- API key management.
- Script generation.
- Storyboard generation.
- Asset generation integration.
- Structured animation generation.
- Automatic provider selection.

## Phase 5 — Audio and Subtitles

- Audio import.
- Voiceover timeline.
- Sound effects timeline.
- Subtitle editor.
- Speech timing.
- Lip-sync integration.

## Phase 6 — Rendering

- FFmpeg integration.
- Frame rendering.
- Scene composition.
- Audio mixing.
- Subtitle rendering.
- MP4 export.

## Phase 7 — Optimization

- Rendering performance.
- Memory management.
- Background processing.
- Project recovery.
- Error handling.
- UI improvements.

# 13. Important Development Rules

All AI coding agents working on MOVEXA must follow these rules:

1. Read this document before modifying the project.
2. Understand the existing architecture before implementing features.
3. Do not replace the core animation engine with external AI artifacts.
4. Do not build the entire application as a single HTML page.
5. Keep AI integrations modular.
6. Keep the animation engine independent of AI providers.
7. Use structured data instead of unvalidated AI-generated code.
8. Support reusable scenes and character assets.
9. Avoid hardcoding API keys.
10. Implement real functionality rather than placeholder buttons.
11. Keep the project modular and maintainable.
12. Test each major subsystem independently.
13. Preserve existing functionality when adding new features.
14. Document important architectural decisions.
15. Prioritize a working MVP before implementing advanced features.

# 14. Minimum Viable Product (MVP)

The first working version should demonstrate the complete production concept.

MVP requirements:

- Desktop application launches successfully.
- Users can create and save projects.
- Users can create multiple scenes.
- Users can import or generate visual assets.
- Users can place and animate characters.
- Users can edit basic keyframes.
- Users can preview animations.
- Users can import voiceover audio.
- Users can add subtitles.
- Users can export an MP4 video.

Advanced AI features can be introduced incrementally.

The MVP should prioritize a functional end-to-end workflow over an extensive collection of incomplete features.

# 15. Long-Term Vision

MOVEXA aims to become a complete AI-assisted 2D animation production studio.

The long-term goal is to allow a user to transform a simple idea into a complete animated video through one application.

Users should not need to manually coordinate multiple AI chat platforms, copy prompts between services, or reconstruct animations from temporary generated artifacts.

**MOVEXA is not simply an AI video generator. It is an AI-assisted animation production environment with its own animation engine and rendering pipeline.**

---

**Project Name:** MOVEXA  
**Tagline:** Create Motion. Tell Stories.  
**Core Vision:** Animation Without Limits.