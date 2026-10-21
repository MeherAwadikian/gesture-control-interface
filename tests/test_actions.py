import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gesture_control.actions import map_normalized_to_screen, PinchStateMachine, ScrollTracker


def test_map_center_of_active_region_is_screen_center():
    x, y = map_normalized_to_screen(0.5, 0.5, 1000, 500, margin=0.15)
    assert abs(x - 500) < 1e-6
    assert abs(y - 250) < 1e-6


def test_map_clamps_beyond_margin_to_screen_edges():
    x, y = map_normalized_to_screen(0.0, 0.0, 1000, 500, margin=0.15)
    assert x == 0
    assert y == 0
    x2, y2 = map_normalized_to_screen(1.0, 1.0, 1000, 500, margin=0.15)
    assert x2 == 1000
    assert y2 == 500


def test_map_independent_axes_handle_aspect_mismatch():
    # A wide screen (1600x400) with a square-ish active region shouldn't
    # skew: x=0.5,y=0.5 must still land at exact screen center on both axes.
    x, y = map_normalized_to_screen(0.5, 0.5, 1600, 400, margin=0.1)
    assert abs(x - 800) < 1e-6
    assert abs(y - 200) < 1e-6


def test_pinch_quick_release_no_movement_is_click():
    pm = PinchStateMachine(click_max_duration=0.3, click_max_movement_px=15)
    calls = []
    pm.start((100, 100), lambda: calls.append("down"))
    event = pm.end((102, 101), lambda: calls.append("up"))
    assert event == "click"
    assert calls == ["down", "up"]
    assert pm.active is False


def test_pinch_with_large_movement_is_drag():
    pm = PinchStateMachine(click_max_duration=0.3, click_max_movement_px=15)
    pm.start((100, 100), lambda: None)
    event = pm.end((300, 300), lambda: None)
    assert event == "drag"


def test_pinch_held_too_long_is_drag_even_without_movement():
    pm = PinchStateMachine(click_max_duration=0.05, click_max_movement_px=15)
    pm.start((100, 100), lambda: None)
    time.sleep(0.1)
    event = pm.end((101, 100), lambda: None)
    assert event == "drag"


def test_scroll_tracker_fires_once_per_sensitivity_threshold():
    st = ScrollTracker(sensitivity_px=40, ticks_per_event=2)
    fired = []
    st.update(100, lambda t: fired.append(t))  # first call just sets baseline
    st.update(90, lambda t: fired.append(t))  # delta=10, below threshold
    assert fired == []
    st.update(50, lambda t: fired.append(t))  # delta from last_y(100) = 50 >= 40
    assert fired == [2]


def test_scroll_tracker_direction_sign():
    st = ScrollTracker(sensitivity_px=40, ticks_per_event=2)
    fired = []
    st.update(100, lambda t: fired.append(t))
    st.update(160, lambda t: fired.append(t))  # moved down -> negative delta -> negative ticks
    assert fired == [-2]


def test_scroll_tracker_reset_clears_baseline():
    st = ScrollTracker(sensitivity_px=40, ticks_per_event=2)
    st.update(100, lambda t: None)
    st.reset()
    fired = []
    st.update(999, lambda t: fired.append(t))  # treated as new baseline, no fire
    assert fired == []
