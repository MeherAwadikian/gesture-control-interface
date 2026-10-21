"""Load and validate the local JSON config file (gesture_config.json)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "camera_index": 0,
    "frame_width": 640,
    "frame_height": 480,
    "max_hands": 2,
    "mediapipe": {
        "min_detection_confidence": 0.7,
        "min_tracking_confidence": 0.6,
    },
    # Fraction of the frame trimmed off each edge before mapping the
    # remaining "active region" to the full screen — lets the hand reach
    # every screen corner without touching the camera frame's edges.
    "frame_margin": 0.15,
    # Exponential-moving-average smoothing factor for the cursor position.
    # Lower = smoother/laggier, higher = snappier/more jittery.
    "smoothing_factor": 0.5,
    # Consecutive identical raw-gesture frames required before a gesture
    # is "confirmed" and allowed to trigger an action (~0.2-0.4s at 20-30fps).
    "debounce_frames": 6,
    # Normalized thumb-tip/index-tip distance below which a hand counts as pinching.
    "pinch_threshold": 0.045,
    # A pinch released within this duration AND this little on-screen movement
    # is classified as a CLICK; otherwise it was a DRAG.
    "click_max_duration_sec": 0.3,
    "click_max_movement_px": 15,
    # Pixels of vertical index+middle movement per discrete scroll tick.
    "scroll_sensitivity_px_per_tick": 40,
    "scroll_ticks_per_event": 2,
    # Volume step per confirmed THUMBS_UP/THUMBS_DOWN entry (0-1 scale, pycaw backend).
    "volume_step": 0.05,
    "toggle_key": "g",
    "exit_key": "q",
}


def load_config(path: str) -> Dict[str, Any]:
    """Load JSON config from `path`, merged over DEFAULT_CONFIG.

    Missing keys fall back to defaults; unknown keys are kept as-is (forward
    compatible). If the file doesn't exist, writes DEFAULT_CONFIG there and
    returns it, so a first run always has a config file to edit.
    """
    merged = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return merged

    with open(path, "r", encoding="utf-8") as f:
        user_cfg = json.load(f)

    for key, value in user_cfg.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value

    return merged
