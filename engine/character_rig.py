"""Cut-out character rig: template + joint queries (architecture doc 7.1).

A rig is plain parented SceneObjects carrying role metadata in ``extras`` -
no new schema, so rigs survive save/load losslessly and every joint remains
a normal object the user can keyframe by hand.
"""

from __future__ import annotations

import uuid

from engine.scene_graph import build_scene_graph
from project.schema import Scene, SceneObject

#: extras["rig"]["role"] values recognised by character actions (walk/wave/...).
RIG_ROLES = ("root", "head", "arm_l", "arm_r", "leg_l", "leg_r")


def build_human_rig(scene: Scene, name: str, stage_width: float,
                    stage_height: float) -> SceneObject:
    """Insert a blocky humanoid parented around (stage_width, stage_height).

    Heights are stage-relative so a rig keeps its proportions on any
    resolution: unit = stage_height / 1080.
    """
    u = stage_height / 1080.0
    cx, ground = stage_width / 2.0, stage_height * 0.82

    def rig_extra(role: str, rig_id: str) -> dict:
        return {"rig": {"id": rig_id, "role": role}}

    rig_id = f"rig_{uuid.uuid4().hex[:8]}"

    def part(role: str, obj: SceneObject) -> SceneObject:
        obj.extras = rig_extra(role, rig_id)
        return obj

    def w(wu: float) -> float:
        return wu * u

    # x/y are pivot anchors deliberately: children hang from their joints so
    # rotating a shoulder swings the whole arm, not just its middle.
    root = part("root", SceneObject(
        id=f"obj_{uuid.uuid4().hex[:8]}", name=f"{name} body", type="rect",
        x=cx, y=ground - w(120), color="#8b5cf6"))
    head = part("head", SceneObject(
        id=f"obj_{uuid.uuid4().hex[:8]}", name=f"{name} head", type="ellipse",
        x=0.0, y=-w(150), scale_x=0.75, scale_y=0.75,
        color="#c4b5fd", parent_id=root.id))
    arm_l = part("arm_l", SceneObject(
        id=f"obj_{uuid.uuid4().hex[:8]}", name=f"{name} arm L", type="rect",
        x=-w(65), y=-w(80),
        pivot_x=0.0, pivot_y=-w(30),          # shoulder joint at top of limb
        color="#a78bfa", parent_id=root.id))
    arm_r = part("arm_r", SceneObject(
        id=f"obj_{uuid.uuid4().hex[:8]}", name=f"{name} arm R", type="rect",
        x=w(65), y=-w(80),
        pivot_x=0.0, pivot_y=-w(30),
        color="#7c3aed", parent_id=root.id))
    leg_l = part("leg_l", SceneObject(
        id=f"obj_{uuid.uuid4().hex[:8]}", name=f"{name} leg L", type="rect",
        x=-w(28), y=w(86),
        pivot_x=0.0, pivot_y=-w(48),          # hip joint
        color="#6d28d9", parent_id=root.id))
    leg_r = part("leg_r", SceneObject(
        id=f"obj_{uuid.uuid4().hex[:8]}", name=f"{name} leg R", type="rect",
        x=w(28), y=w(86),
        pivot_x=0.0, pivot_y=-w(48),
        color="#5b21b6", parent_id=root.id))

    for obj in (root, head, arm_l, arm_r, leg_l, leg_r):
        scene.objects.append(obj)
    return root


def rig_joints(scene: Scene, rig_id: str) -> dict[str, SceneObject]:
    """role -> object for one rig; missing roles are simply absent."""
    rig_object_ids = {o.id for o in scene.objects
                      if o.extras.get("rig", {}).get("id") == rig_id}
    joints: dict[str, SceneObject] = {}
    for root in build_scene_graph(scene):
        for node in root.iterate():
            obj = node.object
            if obj.id not in rig_object_ids:
                continue
            role = obj.extras.get("rig", {}).get("role")
            if role == "root":
                # Body/loop animations target "root"; joint rigging "body".
                joints["root"] = joints["body"] = obj
            elif role:
                joints[role] = obj
    return joints
