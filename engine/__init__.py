"""Animation system internals: scene graph, evaluation, camera."""

from engine.scene_graph import (
    SceneNode,
    Transform,
    build_scene_graph,
    frame_from_values,
)
from engine.keyframes import EASINGS, evaluate_keyframes
from engine.tracks import CameraState, camera_state, object_snapshot
from engine.player import PlaybackController
from engine.actions import ACTIONS, apply_action, rig_targets
from engine.character_rig import RIG_ROLES, build_human_rig, rig_joints
from engine.transitions import TransitionPlan, transition_plan

__all__ = [
    "ACTIONS",
    "EASINGS",
    "RIG_ROLES",
    "TransitionPlan",
    "CameraState",
    "PlaybackController",
    "SceneNode",
    "Transform",
    "apply_action",
    "build_human_rig",
    "build_scene_graph",
    "camera_state",
    "evaluate_keyframes",
    "frame_from_values",
    "object_snapshot",
    "rig_joints",
    "rig_targets",
    "transition_plan",
]
