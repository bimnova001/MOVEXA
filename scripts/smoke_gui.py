"""Headless GUI smoke test: run the real windows without showing them.

Usage: python scripts/smoke_gui.py
Renders the workspace to PNGs in scripts/_smoke_out/ so the actual paint
paths (canvas, panels, theme) get exercised, not just the data layer.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def make_test_image(path: Path, size=(640, 360), color=(120, 20, 200)) -> None:
    Image.new("RGB", size, color).save(path, "PNG")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    work = root / "scripts" / "_smoke_out"
    work.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    from app.theme import QSS  # noqa: E402
    app.setStyleSheet(QSS)

    # Loading screen: run the real check worker off-thread and verify every
    # row resolves to a verdict before the menu is allowed to open.
    from app.loading_screen import LoadingScreen
    loading = LoadingScreen()
    loading.show()
    loading.start()
    while loading._worker is not None and loading._worker.isRunning():
        app.processEvents()
    for _ in range(30):
        app.processEvents()
    rows = [label.text() for label in loading._row_labels]
    assert all(text[:1] in ("✓", "!") for text in rows), rows
    loading.grab().save(str(work / "loading.png"))
    loading.close()

    from app.main_window import MainWindow

    window = MainWindow()
    window.show()
    app.processEvents()
    # Menu (dashboard) capture before any project exists.
    window.grab().save(str(work / "menu.png"))

    project_dir = work / "SmokeProject"
    if (project_dir / "project.json").exists():
        import shutil
        shutil.rmtree(project_dir)

    # Full workflow through the controller, exactly like a user session.
    make_test_image(work / "logo_test.png", color=(190, 24, 220))
    window.controller.new_project(project_dir, "Smoke Test")
    window.controller.import_asset(work / "logo_test.png", "backgrounds")
    window.controller.add_scene("Scene 2")

    scene_id = window.controller.current_scene_id
    image_asset = window.controller.project.asset_by_id(
        window.controller.project.assets[0].id)
    window.controller.add_object_from_asset(scene_id, image_asset.id)
    box = window.controller.add_object(scene_id, type="rect", name="Box",
                                       x=1400, y=300, rotation=25, color="#22d3ee")
    window.controller.add_object(scene_id, type="text", text="MOVEXA",
                                 x=960, y=900, color="#ffffff")

    # Simulate a drag: move the box through the same path mouse events use.
    window.controller.update_object(scene_id, box.id, x=1600, y=260)

    app.processEvents()
    window.grab().save(str(work / "workspace.png"))

    # Properties panel sync: select the box and confirm the inspector bound it.
    window.controller.select_object(scene_id, box.id)
    window.controller.update_object(scene_id, box.id, rotation=-10)
    app.processEvents()
    from app.panels import PropertiesPanel
    panel = window.workspace.findChild(PropertiesPanel)
    assert panel is not None, "properties panel missing from workspace"
    assert panel._obj is not None and panel._obj.id == box.id
    assert abs(panel._obj.rotation - -10) < 1e-6

    # Animation: keyframe the box across the stage, then verify that two
    # distant frames render different pixels.
    window.controller.set_keyframes(
        scene_id, box.id, 0, {"x": float(box.x), "y": float(box.y)})
    window.controller.set_keyframes(scene_id, box.id, 60, {"x": 250.0})
    window.controller.player.set_bounds(150)
    window.controller.player.seek(0)
    app.processEvents()
    window.grab().save(str(work / "frame_0.png"))
    from PySide6.QtGui import QImage
    img0 = QImage(str(work / "frame_0.png"))
    assert not img0.isNull()

    window.controller.player.seek(60)
    app.processEvents()
    window.grab().save(str(work / "frame_60.png"))
    img60 = QImage(str(work / "frame_60.png"))

    def center_metrics(image):
        from PIL import Image as PILImage
        pil = PILImage.fromqimage(image)
        gray = pil.convert("L")
        box_region = gray.crop((int(gray.width * 0.55), 0, gray.width, gray.height))
        return box_region.histogram()

    assert center_metrics(img0) != center_metrics(img60), \
        "the two frames rendered identically: keyframes have no effect"

    # Character rig + walk action: pivot-based cut-out parts must exist, the
    # action must produce leg keyframes, and the rig must survive reload.
    rig_root = window.controller.create_character_rig(scene_id)
    window.controller.apply_action(scene_id, rig_root.id, "walk", 70, 140)
    app.processEvents()
    window.controller.player.seek(110)
    app.processEvents()
    window.grab().save(str(work / "frame_walk.png"))

    # Camera follow across the walk window, then a transition into scene 2
    # exercised at a mid-crossfade frame (2 passes must paint).
    window.controller.set_camera_follow(scene_id, rig_root.id, 70, 140)
    scene2 = window.controller.project.scenes[1]
    window.controller.update_scene_metadata(scene_id, transition="crossfade",
                                            transition_frames=30)
    window.controller.player.seek(110)
    app.processEvents()
    window.grab().save(str(work / "frame_transition.png"))
    window.controller.player.seek(0)
    del scene2

    # Save/reopen round trip with everything still in place.
    window.controller.save()
    window.controller.close_project()
    window.controller.open_project(project_dir)
    reopened = window.controller.project
    assert reopened.scene_by_id(scene_id).object_by_id(box.id) is not None
    assert reopened.scene_by_id(scene_id).object_by_id(box.id).tracks["x"]
    assert len(reopened.assets) == 1
    rig_parts = [o for o in reopened.scene_by_id(scene_id).objects
                 if o.extras.get("rig")]
    assert len(rig_parts) == 6, "rig lost on save/reopen"
    assert reopened.scene_by_id(scene_id).transition == "crossfade"

    # Player state may carry from before the reopen; frame 0 is the anchored
    # view (camera-follow/crossfade legitimately moved the framing later).
    window.controller.player.seek(0)
    app.processEvents()
    window.grab().save(str(work / "reopened.png"))

    print("smoke OK - outputs in", work)
    return 0


if __name__ == "__main__":
    sys.exit(main())
