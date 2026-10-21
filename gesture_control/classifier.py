"""
Pure hand-gesture classification logic.

Operates on plain landmark lists so it can be unit-tested with synthetic
coordinates and has zero dependency on OpenCV, MediaPipe, or a live camera.

Landmark convention (matches MediaPipe Hands):
    A "landmarks" argument is a sequence of 21 (x, y) or (x, y, z) tuples,
    normalized to [0, 1] relative to the frame, indexed 0-20 per the
    standard MediaPipe hand model:
      0=WRIST
      1-4   = THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP
      5-8   = INDEX_FINGER_MCP, PIP, DIP, TIP
      9-12  = MIDDLE_FINGER_MCP, PIP, DIP, TIP
      13-16 = RING_FINGER_MCP, PIP, DIP, TIP
      17-20 = PINKY_MCP, PIP, DIP, TIP

Known simplification (documented, not hidden): finger-extension is decided
by comparing each fingertip's distance from the wrist against its proximal
joint's distance from the wrist. This is a standard, cheap heuristic used
in most hand-gesture demos. It works well when the palm roughly faces the
camera, but can misclassify at extreme hand rotations/tilts. A production
system would add a palm-normal-based 3D angle check; out of scope here.
"""
from __future__ import annotations

import math
from typing import Sequence, Tuple, Dict

Point = Tuple[float, float]

WRIST = 0
THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP = 4, 8, 12, 16, 20

_FINGER_JOINTS = {
    "thumb": (2, 4),    # (proximal joint, tip) — MCP vs TIP
    "index": (6, 8),    # PIP vs TIP
    "middle": (10, 12),
    "ring": (14, 16),
    "pinky": (18, 20),
}

# Gesture labels
POINT = "POINT"
PINCH = "PINCH"
TWO_FINGER = "TWO_FINGER"
OPEN_PALM = "OPEN_PALM"
FIST = "FIST"
THUMBS_UP = "THUMBS_UP"
THUMBS_DOWN = "THUMBS_DOWN"
UNKNOWN = "UNKNOWN"

ALL_GESTURES = [POINT, PINCH, TWO_FINGER, OPEN_PALM, FIST, THUMBS_UP, THUMBS_DOWN, UNKNOWN]


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def fingers_extended(landmarks: Sequence[Point], extension_ratio: float = 1.1) -> Dict[str, bool]:
    """Return {finger_name: is_extended} for the 5 fingers."""
    wrist = landmarks[WRIST]
    result: Dict[str, bool] = {}
    for name, (joint_idx, tip_idx) in _FINGER_JOINTS.items():
        d_joint = _dist(wrist, landmarks[joint_idx])
        d_tip = _dist(wrist, landmarks[tip_idx])
        result[name] = d_tip > d_joint * extension_ratio
    return result


def pinch_distance(landmarks: Sequence[Point]) -> float:
    """Euclidean distance between thumb tip and index tip (normalized coords)."""
    return _dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP])


def classify_gesture(
    landmarks: Sequence[Point],
    pinch_threshold: float = 0.045,
    extension_ratio: float = 1.1,
    thumb_vertical_margin: float = 0.03,
) -> str:
    """Classify a single hand's landmarks into one of the ALL_GESTURES labels.

    Priority order: PINCH is checked first (proximity overrides finger-count
    shape, since a pinch naturally also curls the index tip toward the thumb
    and could otherwise be misread as a part-closed fist).
    """
    if len(landmarks) < 21:
        return UNKNOWN

    if pinch_distance(landmarks) < pinch_threshold:
        return PINCH

    ext = fingers_extended(landmarks, extension_ratio)
    n_extended = sum(ext.values())

    if ext["index"] and not ext["middle"] and not ext["ring"] and not ext["pinky"] and not ext["thumb"]:
        return POINT

    if ext["index"] and ext["middle"] and not ext["ring"] and not ext["pinky"]:
        return TWO_FINGER

    if n_extended == 5:
        return OPEN_PALM

    if n_extended == 0:
        return FIST

    if ext["thumb"] and not ext["index"] and not ext["middle"] and not ext["ring"] and not ext["pinky"]:
        wrist_y = landmarks[WRIST][1]
        thumb_tip_y = landmarks[THUMB_TIP][1]
        # Image/normalized coords: y grows downward, so "up" means smaller y.
        if thumb_tip_y < wrist_y - thumb_vertical_margin:
            return THUMBS_UP
        if thumb_tip_y > wrist_y + thumb_vertical_margin:
            return THUMBS_DOWN

    return UNKNOWN
