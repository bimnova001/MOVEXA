"""Cut-out rig template: structure, parenting, and joint role queries."""

import math

import pytest

from engine.character_rig import RIG_ROLES, build_human_rig, rig_joints
from engine.scene_graph import build_scene_graph, world_transform_with_snapshots
from engine.tracks import object_snapshot
from project.schema import Scene


@pytest.fixture()
def scene() -> Scene:
    return Scene(id="sc_1", name="S", duration_frames=120)


def _frame(scene, obj_id, frame=0):
    nodes = {n.object.id: n for root in build_scene_graph(scene)
             for n in root.iterate()}
    snapshots = {o.id: object_snapshot(o, frame) for o in scene.objects}
    return world_transform_with_snapshots(nodes[obj_id], snapshots)


def _map_point(frame, px, py):
    """Decomposed Transform applied to a centered local point."""
    rad = math.radians(frame.rotation)
    sx, sy = px * frame.scale_x, py * frame.scale_y
    return (frame.x + sx * math.cos(rad) - sy * math.sin(rad),
            frame.y + sx * math.sin(rad) + sy * math.cos(rad))


def test_rig_creates_six_role_parts(scene):
    root = build_human_rig(scene, "Hero", 1920, 1080)
    assert len(scene.objects) == 6
    joints = rig_joints(scene, root.extras["rig"]["id"])
    assert set(joints) == set(RIG_ROLES) | {"body"}
    assert joints["root"].id == root.id


def test_rig_parts_are_parented_to_root(scene):
    root = build_human_rig(scene, "Hero", 1920, 1080)
    rig_id = root.extras["rig"]["id"]
    for obj in scene.objects:
        if obj is not root:
            assert obj.parent_id == root.id
            assert obj.extras["rig"]["id"] == rig_id


def test_limb_pivots_at_shoulder_and_hip(scene):
    build_human_rig(scene, "Hero", 1920, 1080)
    for o in scene.objects:
        role = o.extras["rig"]["role"]
        if role in ("arm_l", "arm_r", "leg_l", "leg_r"):
            assert o.pivot_y < 0  # joint anchored above the limb


def test_arm_rotation_pins_pivot(scene):
    """Rotating a limb keeps its pivot anchored while rotation changes."""
    root = build_human_rig(scene, "Hero", 1920, 1080)
    joints = rig_joints(scene, root.extras["rig"]["id"])
    arm = joints["arm_l"]
    px, py = arm.pivot_x, arm.pivot_y

    pivot_world = _map_point(_frame(scene, arm.id), px, py)
    arm.rotation = 90.0
    pivot_rotated = _map_point(_frame(scene, arm.id), px, py)

    assert pivot_world == (pytest.approx(pivot_rotated[0]),
                           pytest.approx(pivot_rotated[1]))


def test_children_follow_parent_rotation_rigidly(scene):
    """Rotating the body rotates the head with it, around the body pivot."""
    root = build_human_rig(scene, "Hero", 1920, 1080)
    head = next(o for o in scene.objects if o.extras["rig"]["role"] == "head")
    # Child x/y ARE the offset from the parent's center (parenting semantics).
    head_local = (head.x, head.y)

    root.rotation = 90.0
    total = _frame(scene, head.id)  # root + head composed
    hx, hy = _map_point(total, 0.0, 0.0)
    # Head center = body position + rotated local offset (body pivot is 0,0).
    rad = math.radians(root.rotation)
    assert hx == pytest.approx(root.x + head_local[0] * math.cos(rad) - head_local[1] * math.sin(rad))
    assert hy == pytest.approx(root.y + head_local[0] * math.sin(rad) + head_local[1] * math.cos(rad))


def test_joints_empty_for_plain_objects(scene):
    from project.schema import SceneObject
    scene.objects.append(SceneObject(id="o1", name="box", type="rect"))
    assert rig_joints(scene, "rig_nope") == {}

