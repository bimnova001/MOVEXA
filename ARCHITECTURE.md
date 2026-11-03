# MOVEXA — Software Architecture & MVP Development Guide

> **Document:** Architecture Specification  
> **Project:** MOVEXA  
> **Platform:** Windows 11 Desktop  
> **Language:** Python  
> **GUI Framework:** PySide6  
> **Architecture:** Modular Hybrid Animation Engine  
> **Development Stage:** MVP

---

# 1. Purpose of This Document

This document defines the internal software architecture, system responsibilities, component interactions, development strategy, and implementation requirements for MOVEXA.

It complements `INFO.md`.

While `INFO.md` explains the project vision and expected features, this document explains how those features should be implemented.

AI coding agents and developers must read both documents before making significant architectural changes.

The main objective is to build a maintainable desktop application with an independent animation engine.

MOVEXA must not depend on an external AI chat interface to execute or preview animations.

# 2. Architecture Overview

MOVEXA uses a modular architecture consisting of several independent subsystems.

The application is divided into:

1. Desktop UI Layer
2. Application Core
3. Project Management System
4. Asset Management System
5. AI Integration Layer
6. Scene Management System
7. Timeline System
8. Hybrid Animation Engine
9. Audio and Subtitle System
10. Rendering and Export Pipeline

Each subsystem must have a clearly defined responsibility.

Subsystems should communicate through well-defined interfaces instead of accessing each other's internal implementation directly.

## 2.1 High-Level Architecture

    MOVEXA
    │
    ├── Application Layer
    │   ├── Main Window
    │   ├── Dashboard
    │   ├── Workspace
    │   ├── Scene Editor
    │   ├── Timeline Editor
    │   └── Properties Panel
    │
    ├── Application Core
    │   ├── Event Bus
    │   ├── Task Manager
    │   ├── Undo / Redo
    │   └── Project Controller
    │
    ├── Data Layer
    │   ├── Project Manager
    │   ├── Project Schema
    │   ├── Asset Manager
    │   └── Database
    │
    ├── AI Integration
    │   ├── Provider Manager
    │   ├── Provider Adapters
    │   ├── Prompt Manager
    │   └── Output Validator
    │
    ├── Animation System
    │   ├── Scene Graph
    │   ├── Timeline
    │   ├── Keyframe System
    │   ├── Rigging Engine
    │   ├── Procedural Engine
    │   └── Camera System
    │
    ├── Media System
    │   ├── Audio Manager
    │   ├── Lip Sync
    │   └── Subtitle Manager
    │
    └── Rendering System
        ├── Frame Renderer
        ├── Compositor
        ├── Audio Mixer
        └── FFmpeg Exporter

# 3. Desktop Application Architecture

## 3.1 GUI Framework

Use Python and PySide6.

PySide6 is responsible for the desktop interface and user interaction.

The GUI should not directly implement animation calculations or rendering logic.

Recommended interface components:

- MainWindow
- Dashboard
- ProjectWorkspace
- SceneEditor
- TimelineEditor
- CharacterEditor
- AssetBrowser
- PropertiesPanel
- AI Assistant Panel
- ExportDialog

## 3.2 Main Workspace Layout

The primary workspace should contain:

    +------------------------------------------------------+
    | Menu Bar / Toolbar                                   |
    +-------------+---------------------------+------------+
    |             |                           |            |
    | Asset       |                           | Properties |
    | Browser     |       Preview Canvas      | Panel      |
    |             |                           |            |
    |             |                           |            |
    +-------------+---------------------------+------------+
    |                                                      |
    |              Animation Timeline                     |
    |                                                      |
    +------------------------------------------------------+
    | Playback Controls / Status Bar                       |
    +------------------------------------------------------+

The layout should be modular.

Users should eventually be able to resize panels and customize their workspace.

# 4. Application Core

The Application Core coordinates the entire application.

It should not contain the implementation of every subsystem.

Its responsibilities include:

- Managing application state.
- Coordinating project operations.
- Dispatching application events.
- Managing background tasks.
- Handling undo and redo.
- Coordinating save operations.
- Handling errors.

## 4.1 Event Bus

Use an event-driven communication system.

Example events:

- project.created
- project.loaded
- project.saved
- scene.created
- scene.updated
- scene.selected
- timeline.play
- timeline.pause
- timeline.seek
- keyframe.updated
- asset.imported
- render.started
- render.completed
- render.failed

Events allow different subsystems to communicate without creating unnecessary dependencies.

## 4.2 Task Manager

Long-running operations must not block the GUI.

Examples:

- AI API requests.
- Image processing.
- Asset generation.
- Video rendering.
- Audio analysis.
- Project loading.

Use QThread, QRunnable, or an appropriate worker abstraction.

All GUI updates must be delivered safely through Qt signals and slots.

# 5. Project Management System

The Project Manager handles project creation, loading, saving, and validation.

## 5.1 Project Format

Use JSON as the primary project data format.

Use SQLite for application-level metadata where appropriate.

Example:

    MyProject/
    ├── project.json
    ├── assets/
    │   ├── characters/
    │   ├── backgrounds/
    │   ├── props/
    │   └── audio/
    ├── scenes/
    │   ├── scene_001.json
    │   └── scene_002.json
    ├── cache/
    └── exports/

## 5.2 Project Schema

Each project must include:

- Project ID.
- Project name.
- Schema version.
- Resolution.
- Frame rate.
- Duration.
- Scene references.
- Asset references.
- Global settings.

Example:

    {
      "schema_version": "1.0",
      "project_id": "project_001",
      "name": "Demo Animation",
      "settings": {
        "width": 1080,
        "height": 1920,
        "fps": 30
      },
      "scenes": []
    }

The schema must support future migration.

Never silently discard unknown or unsupported project data during loading.

## 5.3 Data Validation

All project data must be validated before execution.

Validation should check:

- Required fields.
- Valid IDs.
- Valid asset references.
- Valid frame ranges.
- Valid animation properties.
- Supported object types.
- Schema compatibility.

# 6. Scene Management System

The Scene Manager controls individual scenes.

A project can contain multiple scenes.

Each scene contains:

- Scene metadata.
- Background.
- Objects.
- Characters.
- Camera.
- Effects.
- Animation tracks.
- Audio tracks.
- Subtitle tracks.

## 6.1 Scene Graph

Use a hierarchical Scene Graph.

Example:

    Scene
    ├── Background
    ├── Character Group
    │   ├── Character A
    │   │   ├── Head
    │   │   ├── Body
    │   │   ├── Left Arm
    │   │   └── Right Arm
    │   └── Character B
    ├── Props
    ├── Graphics
    ├── Text
    └── Camera

Objects should support:

- Position.
- Rotation.
- Scale.
- Opacity.
- Visibility.
- Parent relationships.
- Local transformations.
- Global transformations.

The Scene Graph must be independent of the GUI widget hierarchy.

# 7. Hybrid Animation Engine

The Hybrid Animation Engine is the central technical component of MOVEXA.

It consists of two animation subsystems that operate through a shared scene representation.

## 7.1 Cut-out Animation Engine

The Cut-out Engine handles articulated character animation.

It should support:

- Bone hierarchy.
- Joint transforms.
- Character parts.
- Pivot points.
- Pose management.
- Keyframe animation.
- Expression switching.
- Animation blending.

Example:

    Character
    ├── Root
    ├── Torso
    │   ├── Head
    │   ├── Left Arm
    │   ├── Right Arm
    │   ├── Left Leg
    │   └── Right Leg

A character should be reusable across different scenes.

Character assets and animation definitions should be stored separately.

This allows users to change a character's appearance without recreating all animation data.

## 7.2 Procedural Animation Engine

The Procedural Engine handles animation that does not require a character skeleton.

Examples:

- Animated shapes.
- Infographics.
- Graphs.
- Particles.
- Motion graphics.
- Text animation.
- Decorative effects.
- Custom motion behaviors.

Use a controlled animation instruction format.

Example:

    {
      "type": "move",
      "target": "object_001",
      "start_frame": 0,
      "end_frame": 30,
      "from": {
        "x": 0,
        "y": 300
      },
      "to": {
        "x": 500,
        "y": 300
      },
      "easing": "ease_out"
    }

The initial implementation should support a predefined set of operations.

Do not execute arbitrary AI-generated Python or JavaScript code.

## 7.3 Shared Animation Interface

Both animation engines must use the same timeline and frame evaluation model.

Suggested interface:

    class AnimationTrack:
        def evaluate(self, frame: int):
            raise NotImplementedError

    class AnimationEngine:
        def evaluate_scene(self, scene, frame: int):
            raise NotImplementedError

The actual implementation may use more specialized classes.

The important requirement is that both Cut-out and Procedural animation can be evaluated at the same frame.

## 7.4 Keyframe System

Keyframes represent property values at specific frames.

Supported properties:

- Position X.
- Position Y.
- Rotation.
- Scale X.
- Scale Y.
- Opacity.
- Bone Rotation.
- Camera Position.
- Camera Zoom.

Interpolation methods:

- Step.
- Linear.
- Ease In.
- Ease Out.
- Ease In Out.

Keyframe calculations must be deterministic.

Given the same project data and frame number, the animation engine should produce the same visual state.

# 8. Timeline Architecture

The Timeline System controls the entire animation.

It must use integer frame indices as the primary time representation.

For a project running at 30 FPS:

    frame = time_in_seconds * 30

Example:

    0 seconds  = frame 0
    1 second   = frame 30
    5 seconds  = frame 150
    15 seconds = frame 450

Avoid using floating-point seconds as the authoritative storage format for keyframe positions.

## 8.1 Timeline Tracks

Supported track types:

- Scene Track.
- Character Track.
- Object Track.
- Camera Track.
- Audio Track.
- Subtitle Track.
- Effects Track.

Each track contains one or more timeline clips or animation segments.

## 8.2 Playback Controller

The Playback Controller should support:

- Play.
- Pause.
- Stop.
- Replay.
- Seek.
- Frame Step Forward.
- Frame Step Backward.
- Playback Speed.

The preview should evaluate the animation at the requested frame.

Playback timing should use a monotonic clock and account for dropped frames.

Rendering/export must not depend on real-time preview timing.

This distinction is important for reliable video output.

# 9. Camera System

The Camera System controls the viewport used during rendering.

Supported camera properties:

- Position X.
- Position Y.
- Zoom.
- Rotation.
- Anchor Point.

Camera movements should be keyframe-based.

Supported movements:

- Static.
- Pan.
- Zoom In.
- Zoom Out.
- Follow Target.

The camera must operate independently of object transformations.

# 10. AI Integration Architecture

AI integration must use a provider adapter pattern.

The animation engine must never depend directly on a particular AI SDK.

Suggested interface:

    class BaseProvider:

        def generate_text(self, prompt):
            raise NotImplementedError

        def generate_structured_output(self, prompt, schema):
            raise NotImplementedError

Provider-specific features should be implemented in separate adapters.

Examples:

- OpenAIProvider.
- GeminiProvider.
- ClaudeProvider.
- OpenRouterProvider.
- LocalProvider.

Not every provider must implement image or audio generation.

The application should maintain a capability registry.

## 10.1 AI Task Pipeline

AI-generated content should follow this pipeline:

    User Request
        |
        v
    Prompt Builder
        |
        v
    AI Provider
        |
        v
    Structured Output
        |
        v
    Schema Validation
        |
        v
    Semantic Validation
        |
        v
    Preview / User Approval
        |
        v
    Project Data
        |
        v
    Animation Engine

AI output must never be inserted directly into the running engine without validation.

## 10.2 Two Generation Workflows

MOVEXA must support two workflows.

### Workflow A — Scene-by-Scene Generation

Users create or import a project and generate one scene at a time.

Process:

1. Select a scene.
2. Provide instructions.
3. Select an AI provider.
4. Generate scene instructions.
5. Validate the output.
6. Preview the scene.
7. Accept or edit the result.
8. Save the scene.

Users should be able to regenerate individual scenes without modifying other scenes.

### Workflow B — Full Project Generation

Users provide a topic or script.

AI generates a project plan.

Process:

1. Generate script.
2. Generate storyboard.
3. Generate shot list.
4. Define scene durations.
5. Generate scene descriptions.
6. Generate asset requirements.
7. Generate animation instructions.
8. Validate all scene data.
9. Create the project structure.
10. Generate scenes.
11. Allow user review and modification.

Full project generation should be a managed sequence of tasks, not one enormous AI request.

Long projects should support checkpoints and resume functionality.

# 11. Asset Management

The Asset Manager manages all imported and generated media.

Supported asset categories:

- Characters.
- Character Parts.
- Backgrounds.
- Props.
- Images.
- SVG Graphics.
- Audio.
- Fonts.

Each asset should have:

- Unique ID.
- Asset Type.
- File Path.
- Metadata.
- Dimensions where applicable.
- Import Source.
- Optional Tags.

Assets should be referenced by ID instead of duplicating media data inside Scene JSON.

Use relative paths where practical.

The system should detect missing files and provide recovery options.

# 12. Audio Architecture

The Audio System manages voiceover, music, and sound effects.

These must be represented as separate audio clips or tracks.

Required components:

- Audio Importer.
- Audio Timeline.
- Audio Preview.
- Volume Control.
- Audio Trimming.
- Audio Mixer.
- Voiceover Manager.
- Sound Effects Manager.
- Lip Sync Processor.

## 12.1 Lip Sync

Lip Sync should be a separate subsystem.

Its input is a voiceover audio clip and its output is a series of mouth poses or viseme events.

The initial MVP can support manually timed mouth keyframes.

Automatic speech analysis and phoneme recognition can be implemented later.

Sound effects must not be interpreted as speech input.

# 13. Rendering Architecture

Rendering must be separated from real-time GUI playback.

The Renderer should accept:

- Project Data.
- Scene Data.
- Target Frame.
- Render Settings.

It should return a deterministic rendered frame.

## 13.1 Rendering Pipeline

    Project Data
        |
        v
    Scene Loader
        |
        v
    Frame Evaluator
        |
        v
    Scene Graph
        |
        v
    Camera Transform
        |
        v
    Hybrid Animation Evaluation
        |
        v
    Frame Compositor
        |
        v
    Frame Output
        |
        v
    FFmpeg Encoder
        |
        v
    MP4 Video

## 13.2 Deterministic Rendering

The renderer must not rely on the speed of the preview playback.

For example:

- Frame 0 must always produce the same state.
- Frame 30 must always produce the same state.
- Frame 300 must always produce the same state.

This allows accurate seeking, scene regeneration, and repeatable exports.

## 13.3 Scene-Based Rendering

Scenes should be renderable independently.

This allows:

- Rendering only changed scenes.
- Reusing previously rendered scenes.
- Resuming interrupted exports.
- Reducing unnecessary rendering time.

A render cache should use dependency information or content hashes to avoid reusing outdated frames.

# 14. Undo / Redo System

Editing operations should support undo and redo.

Examples:

- Move Object.
- Rotate Character.
- Delete Keyframe.
- Change Object Scale.
- Modify Scene Duration.
- Edit Subtitle.

Use a command-based architecture.

Each command should provide:

- Execute.
- Undo.
- Optional Redo Validation.

This avoids implementing undo logic separately in every UI component.

# 15. Error Handling

Every subsystem must provide clear errors.

Examples:

- Invalid project file.
- Unsupported asset format.
- Missing asset.
- Invalid animation instruction.
- AI API error.
- Network timeout.
- Render failure.
- FFmpeg unavailable.
- Audio decoding error.

Errors should be logged with enough context to diagnose problems.

The application should avoid silent failures.

# 16. Testing Strategy

Testing must be introduced alongside development.

## Unit Tests

Test:

- Project Schema.
- Scene Graph.
- Keyframe Interpolation.
- Animation Evaluation.
- Asset References.
- Timeline Frame Conversion.
- AI Output Validation.

## Integration Tests

Test:

- Project Save / Load.
- Scene Loading.
- Character Animation.
- Procedural Animation.
- Hybrid Scene Evaluation.
- Frame Rendering.
- Audio and Video Export.

## MVP End-to-End Test

Create a project containing:

1. One background.
2. One character.
3. One procedural animated graphic.
4. At least two scenes.
5. Basic keyframe animation.
6. A voiceover track.
7. A subtitle track.

Then:

- Preview the animation.
- Save the project.
- Close and reopen it.
- Render the complete project.
- Verify the exported MP4.

# 17. Development Priorities

Development should follow this order.

## Priority 1 — Foundation

- Application startup.
- Main Window.
- Project Manager.
- Project Schema.
- Asset Import.
- Scene Graph.

## Priority 2 — Animation Core

- Frame-based Timeline.
- Keyframe System.
- Interpolation.
- Playback Controller.
- Canvas Preview.

## Priority 3 — Hybrid Engine

- Basic Character Hierarchy.
- Cut-out Animation.
- Procedural Animation.
- Camera Movement.
- Scene Transitions.

## Priority 4 — Rendering

- Frame Renderer.
- Compositor.
- FFmpeg Integration.
- MP4 Export.

## Priority 5 — AI

- Provider Manager.
- API Key Settings.
- Script Generator.
- Storyboard Generator.
- Scene Generation.
- Animation Instruction Generation.

## Priority 6 — Audio

- Voiceover.
- Sound Effects.
- Subtitles.
- Lip Sync.
- Audio Mixing.

# 18. Technical Constraints and Guidelines

1. Use modular Python packages.
2. Keep GUI code separate from engine code.
3. Avoid circular imports.
4. Use type hints where practical.
5. Use dataclasses or validated models for structured data.
6. Version project schemas.
7. Use integer frames for animation timing.
8. Use background workers for expensive operations.
9. Never hardcode API credentials.
10. Validate all AI-generated data.
11. Do not execute arbitrary generated code.
12. Keep the renderer deterministic.
13. Keep animation logic independent of AI providers.
14. Make project files portable where practical.
15. Write tests for important engine behavior.
16. Do not implement advanced features before the core engine works.
17. Do not use placeholder functionality in features marked as complete.

# 19. Instructions for AI Coding Agents

Before writing code:

1. Read `INFO.md`.
2. Read `ARCHITECTURE.md`.
3. Inspect the current repository.
4. Identify existing implementations.
5. Check dependencies and runtime environment.
6. Prepare an implementation plan.
7. Implement one subsystem at a time.
8. Run tests after implementation.
9. Update documentation when architecture changes.

When modifying existing code:

- Preserve existing functionality.
- Avoid unnecessary rewrites.
- Explain important architectural decisions.
- Do not create duplicate implementations.
- Do not silently change project formats.
- Keep interfaces consistent.

When a feature cannot be fully implemented, clearly identify what works and what remains incomplete.

# 20. Definition of a Successful MVP

The MVP is successful when MOVEXA can:

- Launch as a Windows desktop application.
- Create and save projects.
- Import and manage assets.
- Create multiple scenes.
- Display a working preview canvas.
- Animate objects with keyframes.
- Animate characters with a basic rig.
- Run procedural animations.
- Combine both animation systems in one scene.
- Play, pause, and seek the timeline.
- Import voiceover and subtitles.
- Render frames independently of preview playback.
- Export a playable MP4.

AI integration is not a prerequisite for proving the animation engine works.

The engine must be functional before advanced AI automation is introduced.

---

**MOVEXA Architecture Principle**

AI generates instructions and assets.

The Animation Engine interprets and executes them.

The Timeline controls when they happen.

The Renderer turns the result into video.

**MOVEXA — Create Motion. Tell Stories.**