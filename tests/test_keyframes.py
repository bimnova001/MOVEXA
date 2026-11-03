"""Keyframe interpolation contract tests (architecture doc 7.4)."""

import pytest

from engine.keyframes import EASINGS, evaluate_keyframes
from project.schema import Keyframe


def track(*pairs):
    return [Keyframe(frame=f, value=v, easing=e) for f, v, e in pairs]


class TestEdges:
    def test_empty_track_yields_fallback(self):
        assert evaluate_keyframes([], 10, 7.5) == 7.5

    def test_before_first_holds_first_value(self):
        kfs = track((30, 4.0, "linear"))
        assert evaluate_keyframes(kfs, 0, 99) == 4.0
        assert evaluate_keyframes(kfs, 29, 99) == 4.0

    def test_after_last_holds_last_value(self):
        kfs = track((0, 1.0, "linear"), (30, 5.0, "linear"))
        assert evaluate_keyframes(kfs, 31, 99) == 5.0
        assert evaluate_keyframes(kfs, 999, 99) == 5.0

    def test_exact_keyframe_frames_return_key_values(self):
        kfs = track((0, 1.0, "linear"), (30, 5.0, "linear"))
        assert evaluate_keyframes(kfs, 0, 99) == 1.0
        assert evaluate_keyframes(kfs, 30, 99) == 5.0


class TestLinear:
    def test_midpoint(self):
        kfs = track((0, 0.0, "linear"), (60, 10.0, "linear"))
        assert evaluate_keyframes(kfs, 30, 0) == pytest.approx(5.0)

    def test_quarter(self):
        kfs = track((0, 0.0, "linear"), (60, 10.0, "linear"))
        assert evaluate_keyframes(kfs, 15, 0) == pytest.approx(2.5)

    def test_backward_interpolation_plays_in_reverse(self):
        kfs = track((0, 100.0, "linear"), (60, 0.0, "linear"))
        assert evaluate_keyframes(kfs, 45, 0) == pytest.approx(25.0)


class TestEasings:
    def test_step_jumps_only_at_end(self):
        kfs = track((0, 0.0, "step"), (30, 1.0, "step"))
        assert evaluate_keyframes(kfs, 29, 0) == 0.0
        assert evaluate_keyframes(kfs, 30, 0) == 1.0

    def test_ease_in_starts_slower_than_linear(self):
        kfs = track((0, 0.0, "ease_in"), (60, 10.0, "ease_in"))
        # At t=0.5 ease_in gives 0.25 of the range, linear would give 0.5.
        assert evaluate_keyframes(kfs, 30, 0) == pytest.approx(2.5)

    def test_ease_out_arrives_faster(self):
        kfs = track((0, 0.0, "ease_out"), (60, 10.0, "ease_out"))
        assert evaluate_keyframes(kfs, 30, 0) == pytest.approx(7.5)

    def test_ease_in_out_midpoint_equals_linear_midpoint(self):
        kfs = track((0, 0.0, "ease_in_out"), (60, 10.0, "ease_in_out"))
        assert evaluate_keyframes(kfs, 30, 0) == pytest.approx(5.0)

    def test_unknown_easing_falls_back_to_linear(self):
        kfs = track((0, 0.0, "cubic-bezier"), (60, 10.0, "cubic-bezier"))
        assert evaluate_keyframes(kfs, 30, 0) == pytest.approx(5.0)

    def test_all_builtin_easings_are_monotonic(self):
        for name, easing in EASINGS.items():
            assert easing(0.0) <= easing(0.5) <= easing(1.0), name


class TestDeterminism:
    def test_same_input_same_output(self):
        """Renderer contract: evaluate is pure, no hidden state."""
        kfs = track((0, 0.0, "ease_in_out"), (90, 42.0, "ease_in_out"))
        first = [evaluate_keyframes(kfs, f, -1) for f in range(90)]
        second = [evaluate_keyframes(kfs, f, -1) for f in range(90)]
        assert first == second

    def test_nan_guard(self):
        # Values that overflow into inf/nan mid-interpolation must not leak
        # into camera zoom or opacity downstream.
        kfs = track((0, float("inf"), "linear"), (10, float("-inf"), "linear"))
        assert evaluate_keyframes(kfs, 5, 0) == 0.0
