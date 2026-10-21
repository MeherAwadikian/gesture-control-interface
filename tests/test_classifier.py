import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gesture_control.classifier import (
    classify_gesture, fingers_extended, pinch_distance,
    POINT, PINCH, TWO_FINGER, OPEN_PALM, FIST, THUMBS_UP, THUMBS_DOWN, UNKNOWN,
)
from tests._hand_builder import build_hand, make_pinch_hand


def test_fist_all_curled():
    hand = build_hand(extended=(), thumb="curled")
    assert classify_gesture(hand) == FIST


def test_open_palm_all_extended():
    hand = build_hand(extended=("index", "middle", "ring", "pinky"), thumb="side")
    assert classify_gesture(hand) == OPEN_PALM


def test_point_index_only():
    hand = build_hand(extended=("index",), thumb="curled")
    assert classify_gesture(hand) == POINT


def test_two_finger_index_and_middle():
    hand = build_hand(extended=("index", "middle"), thumb="curled")
    assert classify_gesture(hand) == TWO_FINGER


def test_thumbs_up():
    hand = build_hand(extended=(), thumb="up")
    assert classify_gesture(hand) == THUMBS_UP


def test_thumbs_down():
    hand = build_hand(extended=(), thumb="down")
    assert classify_gesture(hand) == THUMBS_DOWN


def test_pinch_overrides_shape():
    hand = make_pinch_hand()
    assert classify_gesture(hand) == PINCH


def test_pinch_distance_large_when_not_pinching():
    hand = build_hand(extended=("index",), thumb="curled")
    assert pinch_distance(hand) > 0.045


def test_fingers_extended_reports_each_finger():
    hand = build_hand(extended=("index", "middle"), thumb="curled")
    ext = fingers_extended(hand)
    assert ext["index"] is True
    assert ext["middle"] is True
    assert ext["ring"] is False
    assert ext["pinky"] is False


def test_too_few_landmarks_is_unknown():
    assert classify_gesture([(0.5, 0.5)] * 3) == UNKNOWN


def test_three_fingers_up_is_unknown_not_misclassified():
    # index+middle+ring up (not a mapped shape) should not be reported as
    # POINT, TWO_FINGER, or OPEN_PALM.
    hand = build_hand(extended=("index", "middle", "ring"), thumb="curled")
    label = classify_gesture(hand)
    assert label not in (POINT, TWO_FINGER, OPEN_PALM)
