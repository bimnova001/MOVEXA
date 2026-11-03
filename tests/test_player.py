"""Playback controller: wall-clock stepping, bounds, loop, non-loop stop."""

import pytest

from engine.player import PlaybackController


@pytest.fixture
def clock(monkeypatch):
    """Replace the module's monotonic clock with a controllable counter."""
    state = {"now": 0.0}
    monkeypatch.setattr("engine.player.time.monotonic", lambda: state["now"])
    return state


def advance(clock, seconds: float) -> None:
    clock["now"] += seconds


@pytest.fixture
def player(clock) -> PlaybackController:
    controller = PlaybackController(fps=30)
    controller.set_bounds(120)
    controller.play()
    controller.tick()  # anchor the clock at frame 0
    return controller


class TestBounds:
    def test_initial_state_stopped_at_zero(self):
        fresh = PlaybackController()
        fresh.set_bounds(60)
        assert fresh.frame == 0 and not fresh.playing

    def test_seek_clamps_to_bounds(self):
        fresh = PlaybackController()
        fresh.set_bounds(60)
        fresh.seek(100)
        assert fresh.frame == 59
        fresh.seek(-5)
        assert fresh.frame == 0

    def test_bounds_clamp_current_position(self):
        controller = PlaybackController(fps=30)
        controller.set_bounds(60)
        controller.seek(55)
        controller.set_bounds(20)
        assert controller.frame <= 19


class TestSteps:
    def test_step_pauses_and_moves(self, player):
        player.step(3)
        assert not player.playing and player.frame == 3
        player.step(-1)
        assert player.frame == 2

    def test_step_back_at_zero_stays(self, player):
        player.seek(0)
        player.step(-1)
        assert player.frame == 0

    def test_stop_resets_to_zero(self, player):
        player.seek(40)
        player.stop()
        assert player.frame == 0 and not player.playing


class TestTicks:
    def test_one_second_advances_fps_frames(self, clock, player):
        advance(clock, 1.0)
        assert player.tick() is True
        assert player.frame == 30

    def test_subframe_movement_not_reported(self, clock, player):
        advance(clock, 1 / 60)  # 0.5 frame at 30 fps
        assert player.tick() is False
        advance(clock, 1 / 30)  # crosses the next integer frame
        assert player.tick() is True
        assert player.frame == 1

    def test_loop_wraps(self, clock):
        controller = PlaybackController(fps=30)
        controller.set_bounds(30)  # exactly one second
        controller.loop = True
        controller.play()
        controller.tick()
        advance(clock, 2.5)
        controller.tick()
        # 2.5 s of wall time modulo the 1 s scene.
        assert controller.frame == 15

    def test_non_loop_parks_and_stops(self, clock):
        controller = PlaybackController(fps=30)
        controller.set_bounds(30)
        controller.loop = False
        controller.play()
        controller.tick()
        advance(clock, 5.0)
        controller.tick()
        assert controller.frame == 29
        assert not controller.playing

    def test_speed_multiplies_advance(self, clock, player):
        player.speed = 2.0
        advance(clock, 1.0)
        player.tick()
        assert player.frame == 60

    def test_half_speed(self, clock, player):
        player.speed = 0.5
        advance(clock, 1.0)
        player.tick()
        assert player.frame == 15

    def test_idle_tick_is_noop(self, clock):
        controller = PlaybackController(fps=30)
        controller.set_bounds(60)
        advance(clock, 1.0)
        assert controller.tick() is False
        assert controller.frame == 0
