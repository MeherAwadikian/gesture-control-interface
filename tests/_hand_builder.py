"""Synthetic 21-landmark hand builder for unit tests (no camera/MediaPipe needed)."""
from __future__ import annotations

WRIST = (0.5, 0.9)

# (mcp, pip, dip, tip) base offsets per finger when EXTENDED (straight up, away from wrist)
_EXTENDED_FINGER_COORDS = {
    "index": [(0.45, 0.75), (0.45, 0.65), (0.45, 0.55), (0.45, 0.45)],
    "middle": [(0.50, 0.75), (0.50, 0.63), (0.50, 0.52), (0.50, 0.40)],
    "ring": [(0.55, 0.75), (0.55, 0.65), (0.55, 0.56), (0.55, 0.47)],
    "pinky": [(0.60, 0.77), (0.60, 0.70), (0.60, 0.63), (0.60, 0.56)],
}

# Curled: tip folds back in close to the wrist/palm.
_CURLED_FINGER_COORDS = {
    "index": [(0.45, 0.75), (0.46, 0.80), (0.47, 0.84), (0.42, 0.86)],
    "middle": [(0.50, 0.75), (0.50, 0.80), (0.50, 0.84), (0.50, 0.87)],
    "ring": [(0.55, 0.75), (0.54, 0.80), (0.53, 0.84), (0.52, 0.87)],
    "pinky": [(0.60, 0.77), (0.59, 0.81), (0.58, 0.85), (0.57, 0.88)],
}

_FINGER_SLOTS = {"index": 5, "middle": 9, "ring": 13, "pinky": 17}

_THUMB = {
    "up": [(0.45, 0.85), (0.40, 0.80), (0.35, 0.70), (0.30, 0.50)],
    "down": [(0.45, 0.95), (0.40, 1.00), (0.38, 1.05), (0.35, 1.15)],
    "side": [(0.40, 0.88), (0.32, 0.86), (0.25, 0.85), (0.18, 0.84)],
    "curled": [(0.48, 0.88), (0.49, 0.87), (0.50, 0.89), (0.51, 0.90)],
}


def build_hand(extended=(), thumb="curled") -> list:
    """Build 21 (x, y) landmarks. `extended` is an iterable of finger names
    ('index','middle','ring','pinky') that should be extended; all others
    are curled. `thumb` is 'up' | 'down' | 'side' | 'curled'.
    """
    lm = [None] * 21
    lm[0] = WRIST
    lm[1], lm[2], lm[3], lm[4] = _THUMB[thumb]
    for finger, slot in _FINGER_SLOTS.items():
        coords = _EXTENDED_FINGER_COORDS[finger] if finger in extended else _CURLED_FINGER_COORDS[finger]
        lm[slot], lm[slot + 1], lm[slot + 2], lm[slot + 3] = coords
    return lm


def make_pinch_hand() -> list:
    """A hand where thumb tip and index tip are touching (PINCH)."""
    lm = build_hand(extended=(), thumb="curled")
    lm[4] = (0.50, 0.70)
    lm[8] = (0.505, 0.705)
    return lm
