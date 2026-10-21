import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gesture_control.config import load_config, DEFAULT_CONFIG


def test_missing_file_creates_default_and_returns_defaults():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "nope.json")
        cfg = load_config(path)
        assert os.path.exists(path)
        assert cfg["smoothing_factor"] == DEFAULT_CONFIG["smoothing_factor"]


def test_partial_user_config_merges_over_defaults():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "cfg.json")
        with open(path, "w") as f:
            json.dump({"smoothing_factor": 0.9, "toggle_key": "h"}, f)
        cfg = load_config(path)
        assert cfg["smoothing_factor"] == 0.9
        assert cfg["toggle_key"] == "h"
        # untouched keys still fall back to defaults
        assert cfg["pinch_threshold"] == DEFAULT_CONFIG["pinch_threshold"]


def test_nested_mediapipe_dict_merges_not_replaces():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "cfg.json")
        with open(path, "w") as f:
            json.dump({"mediapipe": {"min_detection_confidence": 0.9}}, f)
        cfg = load_config(path)
        assert cfg["mediapipe"]["min_detection_confidence"] == 0.9
        assert cfg["mediapipe"]["min_tracking_confidence"] == DEFAULT_CONFIG["mediapipe"]["min_tracking_confidence"]
