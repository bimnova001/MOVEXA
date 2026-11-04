"""AI agent routing + local execution (Qt-free)."""

from app import agent


def test_local_shape_intents():
    route, intent = agent.route("add rect at 600,300 #22d3ee")
    assert route == "local"
    assert intent.kind == "add_rect"
    assert intent.payload["x"] == 600 and intent.payload["y"] == 300
    assert intent.payload["color"] == "#22d3ee"

    route, intent = agent.route("สร้าง circle")
    assert route == "local" and intent.kind == "add_ellipse"

    route, intent = agent.route('add text "HELLO" at 200,400')
    assert route == "local" and intent.kind == "add_text"
    assert intent.payload["text"] == "HELLO"


def test_animate_intent_frames():
    _route, intent = agent.route("spin 10-40")
    assert intent.kind == "animate"
    assert intent.payload == {"action": "spin", "start": 10, "end": 40}
    _route, fallback = agent.route("bob")
    assert fallback.payload == {"action": "bob", "start": 0, "end": 90}


def test_outline_routes_to_provider_path():
    for text in ("outline: a cat chase", "บท: แมวตามลูกบอล",
                 "storyboard for sunrise"):
        route, brief = agent.route(text)
        assert route == "outline", text
        assert brief, text


def test_scene_route_passes_full_brief():
    route, brief = agent.route("generate a scene: rain over city")
    assert route == "scene" and "rain" in brief


def test_help_for_unknown_and_empty():
    assert agent.route("")[0] == "help"
    assert agent.route("what color is the sky?")[0] == "help"


def test_execute_local_adds_shape(controller):
    scene_id = controller.current_scene_id
    route, intent = agent.route("add rect at 600,300 #22d3ee")
    reply = agent.execute_local(intent, controller)
    obj = controller.project.scene_by_id(scene_id).objects[0]
    assert obj.type == "rect" and obj.x == 600 and obj.color == "#22d3ee"
    assert obj.name in reply


def test_execute_local_animate_uses_selection(controller):
    scene_id = controller.current_scene_id
    box = controller.add_object(scene_id, type="rect")
    controller.select_object(scene_id, box.id)
    _route, intent = agent.route("spin 5-35")
    reply = agent.execute_local(intent, controller)
    assert "spin applied" in reply
    assert controller.project.scene_by_id(scene_id).object_by_id(box.id).tracks


def test_execute_local_needs_selection_for_animate(controller):
    _route, intent = agent.route("wave 0-30")
    reply = agent.execute_local(intent, controller)
    assert "Select an object" in reply
