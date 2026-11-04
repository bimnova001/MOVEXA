"""Timeline drag math: edge resize hit-testing and duration mapping."""

from __future__ import annotations

from app.timeline import MAX_DURATION, block_hit, edge_hit, resize_duration

EDGES = [(100.0, 200.0), (200.0, 320.0)]
TINY = [(100.0, 200.0), (320.0, 326.0)]


# -- hit-testing -----------------------------------------------------------------

def test_edge_hit_near_right_edge() -> None:
    # Tolerance straddles the boundary; the grab belongs to the clip on the
    # LEFT of the cut (CapCut semantics: drag a cut to trim that clip).
    assert edge_hit(EDGES, 203.0) == 0
    assert edge_hit(EDGES, 197.0) == 0


def test_edge_hit_ignores_tiny_clips_and_whitespace() -> None:
    assert edge_hit(EDGES, 50.0) is None      # whitespace before first clip
    assert edge_hit(EDGES, 210.0) is None     # inside the span, not the edge
    assert edge_hit(TINY, 325.9) is None      # tiny clip: edge not grabbable


def test_block_hit_covers_spans() -> None:
    assert block_hit(EDGES, 150.0) == 0
    assert block_hit(EDGES, 300.0) == 1
    assert block_hit(EDGES, 99.999) is None
    assert block_hit(TINY, 324.0) == 1


# -- duration resize math ----------------------------------------------------------

def test_resize_duration_maps_pixels_to_frames() -> None:
    # total 180 frames over 360 px -> 0.5 frames per px
    assert resize_duration(90, 60.0, 180, 360.0) == 120
    assert resize_duration(90, -60.0, 180, 360.0) == 60


def test_resize_duration_clamps() -> None:
    assert resize_duration(10, -999.0, 180, 360.0) == 1
    assert resize_duration(10, 10_000_000.0, 180, 360.0) == MAX_DURATION


def test_resize_duration_survives_degenerate_viewport() -> None:
    assert resize_duration(45, 25.0, 0, 0.0) == 45
