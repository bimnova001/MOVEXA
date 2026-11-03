"""Event bus contract tests."""

from core.events import EventBus


def test_dispatch_reaches_subscribers():
    bus = EventBus()
    seen = []
    bus.subscribe("project.saved", seen.append)
    bus.publish("project.saved", {"project": "p1"})
    assert seen == [{"project": "p1"}]


def test_wildcard_receives_all_events():
    bus = EventBus()
    seen = []
    bus.subscribe("*", lambda data: seen.append(data.get("event")))
    bus.publish("scene.created", {"event": "scene.created"})
    bus.publish("asset.imported", {"event": "asset.imported"})
    assert seen == ["scene.created", "asset.imported"]


def test_bad_handler_does_not_block_other_subscribers():
    bus = EventBus()
    ok = []
    bus.subscribe("scene.updated", lambda _d: 1 / 0)  # explodes
    bus.subscribe("scene.updated", ok.append)
    bus.publish("scene.updated")
    assert ok == [{}]


def test_data_is_copied_into_handler_payload():
    bus = EventBus()
    seen = []
    bus.subscribe("x", seen.append)
    payload = {"a": 1}
    bus.publish("x", payload)
    payload["a"] = 999
    assert seen[0]["a"] == 1


def test_unsubscribe():
    bus = EventBus()
    seen = []
    handler = seen.append
    bus.subscribe("y", handler)
    bus.publish("y", {"n": 1})
    bus.unsubscribe("y", handler)
    bus.publish("y", {"n": 2})
    assert seen == [{"n": 1}]
