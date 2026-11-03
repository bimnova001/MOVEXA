"""Scene Graph (architecture doc 6.1).

A hierarchical node tree completely independent of the Qt widget hierarchy.
Each node holds its local transform; world transforms compose parent chains.
Objects reference built from ``project.schema.Scene`` so the same graph can
later be evaluated per-frame by the animation engine and by the renderer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterator

from project.schema import Scene, SceneObject
from engine.tracks import ObjectSnapshot, object_snapshot


@dataclass
class Transform:

    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0        # degrees
    scale_x: float = 1.0
    scale_y: float = 1.0

    def compose(self, child: "Transform") -> "Transform":
        cos_r = math.cos(math.radians(self.rotation))
        sin_r = math.sin(math.radians(self.rotation))
        sx, sy = child.x * self.scale_x, child.y * self.scale_y
        return Transform(
            x=self.x + sx * cos_r - sy * sin_r,
            y=self.y + sx * sin_r + sy * cos_r,
            rotation=self.rotation + child.rotation,
            scale_x=self.scale_x * child.scale_x,
            scale_y=self.scale_y * child.scale_y,
        )

def frame_from_values(
    x: float, y: float,
    rotation: float, scale_x: float, scale_y: float,
    pivot_x: float = 0.0, pivot_y: float = 0.0,
) -> Transform:
    """Centered drawing frame -> parent frame, honoring the pivot anchor.

    Mapping T(x,y) . T(p) . R(rot) . S . T(-p) decomposes into translation
    (x,y) + p - R(rot)*S(p) with rotation/scale unchanged, so the rest of the
    engine (parenting, painting, hit-testing) keeps using plain Transforms.
    """
    fx, fy = rotate_scale_point(rotation, scale_x, scale_y, pivot_x, pivot_y)
    return Transform(
        x=x + pivot_x - fx, y=y + pivot_y - fy,
        rotation=rotation, scale_x=scale_x, scale_y=scale_y,
    )


def rotate_scale_point(
    rotation: float, scale_x: float, scale_y: float, px: float, py: float
) -> tuple[float, float]:
    cos_r = math.cos(math.radians(rotation))
    sin_r = math.sin(math.radians(rotation))
    sxp, syp = px * scale_x, py * scale_y
    return sxp * cos_r - syp * sin_r, sxp * sin_r + syp * cos_r


def world_transform_with_snapshots(
    node: SceneNode, snapshots: dict[str, ObjectSnapshot]
) -> Transform:
    """Compose the parent chain from per-frame snapshots.

    Snapshots (not the objects' static fields) drive every level, so animated
    parents move their children; pivots stay static and are read from objects.
    """
    chain: list[SceneNode] = []
    while node is not None:
        chain.append(node)
        node = node.parent
    result = Transform()
    for node in reversed(chain):
        snap = snapshots.get(node.object.id)
        if snap is None:
            snap = object_snapshot(node.object, 0)
        result = result.compose(frame_from_values(
            x=snap.x, y=snap.y, rotation=snap.rotation,
            scale_x=snap.scale_x, scale_y=snap.scale_y,
            pivot_x=node.object.pivot_x, pivot_y=node.object.pivot_y,
        ))
    return result


@dataclass
class SceneNode:

    object: SceneObject
    parent: "SceneNode | None" = None
    children: list["SceneNode"] = field(default_factory=list)

    def add_child(self, node: "SceneNode") -> None:
        node.parent = self
        self.children.append(node)

    def world_transform(self) -> Transform:
        """Compose local transforms along the parent chain (root -> self).

        Deterministic: same input data always yields the same matrices,
        which the renderer relies on (architecture doc 13.2).
        """
        chain: list[SceneNode] = []
        node: SceneNode | None = self
        while node is not None:
            chain.append(node)
            node = node.parent
        result = Transform()
        for node in reversed(chain):
            result = result.compose(frame_from_values(
                x=node.object.x, y=node.object.y,
                rotation=node.object.rotation,
                scale_x=node.object.scale_x,
                scale_y=node.object.scale_y,
                pivot_x=node.object.pivot_x,
                pivot_y=node.object.pivot_y,
            ))
        return result

    def local_point_to_world(self, x: float, y: float) -> tuple[float, float]:
        world = self.world_transform()
        cos_r = math.cos(math.radians(world.rotation))
        sin_r = math.sin(math.radians(world.rotation))
        sx, sy = x * world.scale_x, y * world.scale_y
        return world.x + sx * cos_r - sy * sin_r, world.y + sx * sin_r + sy * cos_r

    def iterate(self) -> Iterator["SceneNode"]:
        """Depth-first iteration: self first, then children in paint order."""
        yield self
        for child in self.children:
            yield from child.iterate()

def build_scene_graph(scene: Scene) -> list[SceneNode]:
    """Build the node forest of *scene* from its objects.

    Objects with ``parent_id`` attach under their parent; the returned list
    contains only root nodes, in paint order. Raises ValueError on broken
    or cyclic parenting (validation in schema should catch it beforehand).
    """
    by_id: dict[str, SceneNode] = {}
    for obj in scene.objects:
        if obj.id in by_id:
            raise ValueError(f"duplicate object id in scene: {obj.id}")
        by_id[obj.id] = SceneNode(object=obj)

    roots: list[SceneNode] = []
    for obj in scene.objects:
        node = by_id[obj.id]
        if obj.parent_id is None:
            roots.append(node)
        else:
            parent = by_id.get(obj.parent_id)
            if parent is None:
                raise ValueError(f"object {obj.id}: unknown parent {obj.parent_id!r}")
            parent.add_child(node)

    _check_cycles(by_id)

    return roots

def _check_cycles(by_id: dict[str, SceneNode]) -> None:
    """Raise ValueError when any parent chain loops.

    Walks parent links instead of descending from roots: a graph that is one
    big cycle has no root at all, so root-only traversal would miss it.
    Iterative, not recursive, to stay independent of the interpreter
    recursion limit in deep hierarchies.
    """
    for start in by_id.values():
        seen: set[int] = {id(start)}
        node = start.parent
        while node is not None:
            if id(node) in seen:
                raise ValueError("cyclic parenting in scene graph")
            seen.add(id(node))
            node = node.parent
