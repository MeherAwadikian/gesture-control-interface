import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gesture_control.stability import StabilityTracker


def test_no_confirmation_before_required_frames():
    t = StabilityTracker(required_frames=5)
    for _ in range(4):
        r = t.update("POINT")
        assert r.confirmed_gesture is None


def test_confirms_after_required_consecutive_frames():
    t = StabilityTracker(required_frames=5)
    r = None
    for _ in range(5):
        r = t.update("POINT")
    assert r.confirmed_gesture == "POINT"
    assert r.is_new_entry is True


def test_single_noisy_frame_resets_the_streak():
    t = StabilityTracker(required_frames=5)
    for _ in range(4):
        t.update("POINT")
    r = t.update("UNKNOWN")  # one bad frame
    assert r.confirmed_gesture is None
    for _ in range(4):
        r = t.update("POINT")
    assert r.confirmed_gesture is None  # only 4 POINT frames since the blip
    r = t.update("POINT")
    assert r.confirmed_gesture == "POINT"


def test_is_new_entry_fires_only_once_per_confirmation():
    t = StabilityTracker(required_frames=3)
    entries = [t.update("PINCH").is_new_entry for _ in range(10)]
    assert entries.count(True) == 1
    assert entries[2] is True  # becomes True on the 3rd identical frame


def test_switching_confirmed_gesture_fires_new_entry_again():
    t = StabilityTracker(required_frames=3)
    for _ in range(3):
        t.update("POINT")
    for _ in range(2):
        r = t.update("PINCH")
        assert r.is_new_entry is False
    r = t.update("PINCH")
    assert r.confirmed_gesture == "PINCH"
    assert r.is_new_entry is True


def test_reset_clears_confirmed_state():
    t = StabilityTracker(required_frames=3)
    for _ in range(3):
        t.update("FIST")
    assert t.confirmed == "FIST"
    t.reset()
    assert t.confirmed is None
