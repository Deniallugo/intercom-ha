"""Per-speaker airtime: a broadcast to a busy speaker waits its turn.

Without this, a second play_media on a speaker that is still playing the first
PTT cuts it off (ESPHome replaces the running announcement; so do most
players). Each speaker gets a timeline instead: a new broadcast is booked to
start when the last booked one ends, in arrival order.

Booking is by time, not by locks: we know how long each clip is, and nothing
here is bound to an event loop. A broadcast that would start more than
MAX_WAIT seconds from now is refused ("busy"), so the queue cannot grow
without bound. Playback started outside the add-on is not tracked.
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional

# Longest a broadcast may wait for a busy speaker.
MAX_WAIT = 30.0
# Added to each clip: HA -> ffmpeg proxy -> device start-up latency and a
# short gap so consecutive messages do not run together.
TAIL = 1.5


@dataclass
class Slot:
    target: str
    start: float      # monotonic
    end: float        # monotonic
    wait: float       # seconds from booking until start


class Airtime:
    def __init__(self, now_func: Callable[[], float] = time.monotonic,
                 max_wait: float = MAX_WAIT, tail: float = TAIL):
        self._now = now_func
        self.max_wait = max_wait
        self.tail = tail
        self._busy_until: dict[str, float] = {}

    def book(self, target: str, duration: float) -> Optional[Slot]:
        """Reserve `target` for `duration` s, after whatever is booked on it.
        None if that start is more than max_wait away (the speaker is busy)."""
        now = self._now()
        start = max(now, self._busy_until.get(target, now))
        wait = start - now
        if wait > self.max_wait:
            return None
        end = start + max(0.0, duration) + self.tail
        self._busy_until[target] = end
        return Slot(target, start, end, wait)

    def cancel(self, slot: Slot) -> None:
        """Give back a slot whose playback failed — only if nothing was
        booked after it, so later bookings keep their order."""
        if self._busy_until.get(slot.target) == slot.end:
            if slot.start <= self._now():
                self._busy_until.pop(slot.target, None)
            else:
                self._busy_until[slot.target] = slot.start

    def now(self) -> float:
        return self._now()

    def busy_for(self, target: str) -> float:
        """Seconds until `target` is free (0 if free now)."""
        return max(0.0, self._busy_until.get(target, 0.0) - self._now())

    def reset(self) -> None:
        self._busy_until.clear()
