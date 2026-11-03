"""Playback controller (architecture doc 8.2).

Qt-free by design: the GUI calls tick() from its timer and reads .frame.
Holding the clock here keeps preview timing in one place; the renderer never
touches it, so exports stay deterministic regardless of preview speed.
"""

from __future__ import annotations

import time


class PlaybackController:
    def __init__(self, fps: int = 30) -> None:
        self.fps = fps
        self.duration = 1          # frames; bound to the current scene
        self.speed = 1.0
        self.loop = True
        self._position = 0.0       # float accumulator; .frame is the integer view
        self._playing = False
        self._last_tick: float | None = None

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def frame(self) -> int:
        return int(self._position)

    def set_bounds(self, duration: int) -> None:
        """Clamp all state into [0, duration-1]. Guarded against scaling to zero."""
        self.duration = max(1, int(duration))
        self.seek(self.frame)

    def play(self) -> bool:
        was_playing = self._playing
        self._last_tick = None
        self._playing = True
        return not was_playing

    def pause(self) -> bool:
        was = self._playing
        self._playing = False
        return was

    def toggle(self) -> bool:
        return self.pause() if self._playing else self.play()

    def stop(self) -> None:
        self._playing = False
        self.seek(0)

    def seek(self, frame: int) -> None:
        self._position = float(min(max(0, int(frame)), self.duration - 1))

    def step(self, delta: int) -> None:
        self.pause()
        self.seek(self.frame + delta)

    def tick(self) -> bool:
        """Advance if playing; returns True when the integer frame changed.

        Dropped-frame handling: elapsed time converts to fractional frames, so
        a slow timer still lands on the correct wall-clock position instead of
        drifting behind real time.
        """
        if not self._playing:
            self._last_tick = None
            return False
        now = time.monotonic()
        if self._last_tick is None:
            self._last_tick = now
            return False
        elapsed = now - self._last_tick
        self._last_tick = now
        previous = self.frame
        self._position += elapsed * self.fps * self.speed
        if self._position >= self.duration:
            if self.loop:
                self._position %= self.duration
                return True
            # Non-loop playback parks on the last frame and releases control.
            self._position = self.duration - 1
            self._playing = False
        return self.frame != previous
