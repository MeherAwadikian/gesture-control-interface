"""
Gesture debounce / stability tracking.

The puzzle's own clue is "track gesture state across frames, not single-frame
decisions" — this module is that state machine. A raw per-frame
classification is noisy (a single bad frame can flip POINT -> UNKNOWN -> POINT).
StabilityTracker only "confirms" a gesture once it has been the raw label for
`required_frames` consecutive frames, and separately reports whether this
frame is the *first* frame of a newly confirmed gesture (an "edge"), so
discrete actions (click, volume step) fire exactly once per gesture entry
instead of once per frame while held.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional


@dataclass
class StabilityResult:
    confirmed_gesture: Optional[str]  # the currently confirmed (debounced) gesture, or None
    raw_gesture: str                  # this frame's raw, un-debounced classification
    is_new_entry: bool                # True only on the frame the confirmed gesture changed


class StabilityTracker:
    def __init__(self, required_frames: int = 5):
        if required_frames < 1:
            raise ValueError("required_frames must be >= 1")
        self.required_frames = required_frames
        self._history: Deque[str] = deque(maxlen=required_frames)
        self._confirmed: Optional[str] = None

    def update(self, raw_gesture: str) -> StabilityResult:
        self._history.append(raw_gesture)

        is_new_entry = False
        if len(self._history) == self.required_frames and all(g == raw_gesture for g in self._history):
            if self._confirmed != raw_gesture:
                self._confirmed = raw_gesture
                is_new_entry = True

        return StabilityResult(
            confirmed_gesture=self._confirmed,
            raw_gesture=raw_gesture,
            is_new_entry=is_new_entry,
        )

    def reset(self) -> None:
        self._history.clear()
        self._confirmed = None

    @property
    def confirmed(self) -> Optional[str]:
        return self._confirmed
