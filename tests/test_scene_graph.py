"""Scene graph: parenting, world transforms, cycles."""

import pytest

from engine.scene_graph import build_scene_graph
from project.schema import Scene, SceneObject


class TestBuild:
    def test_flat_scene_yields_roots_in_paint_order(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="a", name="A", x=10, y=20),
            SceneObject(id="b", name="B", x=5, y=5),
        ])
        roots = build_scene_graph(scene)
        assert [n.object.id for n in roots] == ["a", "b"]

    def test_children_removed_from_roots(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="arm", name="Arm"),
            SceneObject(id="hand", name="Hand", parent_id="arm"),
        ])
        roots = build_scene_graph(scene)
        assert len(roots) == 1
        assert roots[0].children[0].object.id == "hand"

    def test_unknown_parent_raises(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="a", name="A", parent_id="ghost"),
        ])
        with pytest.raises(ValueError, match="ghost"):
            build_scene_graph(scene)

    def test_duplicate_ids_raise(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="a", name="A"), SceneObject(id="a", name="B"),
        ])
        with pytest.raises(ValueError, match="duplicate"):
            build_scene_graph(scene)

    def test_cycle_raises(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="a", name="A", parent_id="b"),
            SceneObject(id="b", name="B", parent_id="a"),
        ])
        with pytest.raises(ValueError, match="cyclic"):
            build_scene_graph(scene)


class TestTransforms:
    def test_identity_chain_is_position(self):
        scene = Scene(id="s", objects=[SceneObject(id="a", x=30, y=-10)])
        world = build_scene_graph(scene)[0].world_transform()
        assert (world.x, world.y) == (30.0, -10.0)
        assert world.rotation == 0.0
        assert (world.scale_x, world.scale_y) == (1.0, 1.0)

    def test_parent_translate_then_child_position(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="body", x=100, y=200),
            SceneObject(id="head", x=0, y=-80, parent_id="body"),
        ])
        body, = build_scene_graph(scene)
        head = body.children[0]
        world = head.world_transform()
        assert (world.x, world.y) == (100.0, 120.0)  # body pos + head offset

    def test_parent_rotation_composes(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="arm", x=0, y=0, rotation=90),
            SceneObject(id="hand", x=100, y=0, parent_id="arm"),
        ])
        arm, = build_scene_graph(scene)
        world = arm.children[0].world_transform()
        # Point (100, 0) rotated 90 degrees cw -> (0, 100).
        assert world.x == pytest.approx(0.0, abs=1e-9)
        assert world.y == pytest.approx(100.0, abs=1e-9)
        assert world.rotation == 90.0

    def test_scale_multiplies_along_chain(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="root", x=0, y=0, scale_x=2.0, scale_y=2.0),
            SceneObject(id="child", x=10, y=0, scale_x=3.0, scale_y=3.0,
                        parent_id="root"),
        ])
        root, = build_scene_graph(scene)
        world = root.children[0].world_transform()
        assert world.x == pytest.approx(20.0)
        assert (world.scale_x, world.scale_y) == (6.0, 6.0)

    def test_three_levels_walk_composition(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="root", x=100, y=100, rotation=0),
            SceneObject(id="mid", x=50, y=0, parent_id="root"),
            SceneObject(id="leaf", x=0, y=-25, parent_id="mid"),
        ])
        root, = build_scene_graph(scene)
        leaf = root.children[0].children[0]
        world = leaf.world_transform()
        assert (world.x, world.y) == (150.0, 75.0)

    def test_grandparent_rotation_rotates_child_chain(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="gp", x=0, y=0, rotation=180),
            SceneObject(id="p", x=10, y=0, parent_id="gp"),
            SceneObject(id="c", x=10, y=0, parent_id="p"),
        ])
        gp, = build_scene_graph(scene)
        c = gp.children[0].children[0]
        world = c.world_transform()
        assert world.x == pytest.approx(-20.0, abs=1e-9)
        assert world.y == pytest.approx(0.0, abs=1e-9)

    def test_local_point_to_world(self):
        scene = Scene(id="s", objects=[
            SceneObject(id="n", x=10, y=10, scale_x=2.0, scale_y=2.0),
        ])
        node, = build_scene_graph(scene)
        assert node.local_point_to_world(5, 5) == (20.0, 20.0)
