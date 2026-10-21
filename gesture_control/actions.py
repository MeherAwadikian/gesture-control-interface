"""
OS-level action dispatch: cursor mapping/movement, click/drag state machine,
and scroll. Wraps pyautogui. Kept separate from the main loop so the pure
mapping/state-machine math can be unit-tested without a real display or
mouse (tests monkeypatch `pyautogui` calls or just check internal state).
"""
from __future__ import annotations

import time
from typing import Optional, Tuple

from .smoothing import EMASmoother

Point = Tuple[float, float]


def map_normalized_to_screen(
    x: float,
    y: float,
    screen_w: int,
    screen_h: int,
    margin: float = 0.15,
) -> Point:
    """Map a normalized (0-1) frame coordinate to a screen pixel coordinate.

    A margin is trimmed off each edge of the frame first and the remaining
    "active region" is stretched to the full screen, so the hand doesn't
    need to physically reach the camera frame's edges to hit screen corners.
    Independently handles x and y, so frame-vs-screen aspect-ratio mismatch
    doesn't skew the mapping (each axis maps its own active-region span to
    its own screen-dimension span).
    """
    def _map_axis(v: float, m: float, dim: int) -> float:
        span = 1.0 - 2 * m
        v_clamped = min(max(v, m), 1.0 - m)
        fraction = (v_clamped - m) / span if span > 0 else 0.5
        return fraction * dim

    sx = _map_axis(x, margin, screen_w)
    sy = _map_axis(y, margin, screen_h)
    return sx, sy


class PinchStateMachine:
    """Distinguishes CLICK vs CLICK-AND-DRAG from a single pinch gesture,
    the same way a real mouse button does: a quick press+release with little
    movement is a click; a held press with movement is a drag. mouseDown
    fires once on pinch-start, mouseUp once on release — the OS/application
    receiving the events decides click vs drag the same way it would for a
    physical mouse, so there's no separate "fire a click" action needed.
    """

    def __init__(self, click_max_duration: float = 0.3, click_max_movement_px: float = 15):
        self.click_max_duration = click_max_duration
        self.click_max_movement_px = click_max_movement_px
        self._active = False
        self._start_time: Optional[float] = None
        self._start_pos: Optional[Point] = None
        self.last_event: Optional[str] = None  # "click" or "drag", for the overlay

    @property
    def active(self) -> bool:
        return self._active

    def start(self, pos: Point, mouse_down_fn) -> None:
        self._active = True
        self._start_time = time.time()
        self._start_pos = pos
        mouse_down_fn()

    def end(self, pos: Point, mouse_up_fn) -> str:
        mouse_up_fn()
        duration = time.time() - (self._start_time or time.time())
        dx = pos[0] - (self._start_pos[0] if self._start_pos else pos[0])
        dy = pos[1] - (self._start_pos[1] if self._start_pos else pos[1])
        moved = (dx * dx + dy * dy) ** 0.5
        self.last_event = "click" if (duration <= self.click_max_duration and moved <= self.click_max_movement_px) else "drag"
        self._active = False
        self._start_time = None
        self._start_pos = None
        return self.last_event


class ScrollTracker:
    """Translates sustained vertical movement of the two-finger midpoint into
    discrete scroll ticks, firing one `scroll_fn(delta_ticks)` call per
    `sensitivity_px` of accumulated movement rather than every frame.
    """

    def __init__(self, sensitivity_px: float = 40, ticks_per_event: int = 2):
        self.sensitivity_px = sensitivity_px
        self.ticks_per_event = ticks_per_event
        self._last_y: Optional[float] = None

    def reset(self) -> None:
        self._last_y = None

    def update(self, y_px: float, scroll_fn) -> None:
        if self._last_y is None:
            self._last_y = y_px
            return
        delta = self._last_y - y_px  # moving hand up -> scroll up (positive)
        if abs(delta) >= self.sensitivity_px:
            ticks = self.ticks_per_event if delta > 0 else -self.ticks_per_event
            scroll_fn(ticks)
            self._last_y = y_px


class ActionController:
    """Ties the pure helpers above to real pyautogui calls against the real
    screen. Constructed with screen dimensions injected so it's testable
    without querying a real display.
    """

    def __init__(self, screen_w: int, screen_h: int, cfg: dict):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.cfg = cfg
        self.smoother = EMASmoother(alpha=cfg.get("smoothing_factor", 0.5))
        self.pinch_machine = PinchStateMachine(
            click_max_duration=cfg.get("click_max_duration_sec", 0.3),
            click_max_movement_px=cfg.get("click_max_movement_px", 15),
        )
        self.scroll_tracker = ScrollTracker(
            sensitivity_px=cfg.get("scroll_sensitivity_px_per_tick", 40),
            ticks_per_event=cfg.get("scroll_ticks_per_event", 2),
        )

    def _pyautogui(self):
        import pyautogui

        return pyautogui

    def move_cursor(self, norm_x: float, norm_y: float) -> Point:
        raw = map_normalized_to_screen(norm_x, norm_y, self.screen_w, self.screen_h, self.cfg.get("frame_margin", 0.15))
        smoothed = self.smoother.update(raw)
        self._pyautogui().moveTo(smoothed[0], smoothed[1])
        return smoothed

    def start_pinch(self) -> None:
        pos = self.smoother.value or (self.screen_w / 2, self.screen_h / 2)
        self.pinch_machine.start(pos, lambda: self._pyautogui().mouseDown())

    def end_pinch(self) -> str:
        pos = self.smoother.value or (self.screen_w / 2, self.screen_h / 2)
        return self.pinch_machine.end(pos, lambda: self._pyautogui().mouseUp())

    def release_any_held_button(self) -> None:
        if self.pinch_machine.active:
            self._pyautogui().mouseUp()
            self.pinch_machine._active = False

    def scroll(self, norm_y: float) -> None:
        y_px = norm_y * self.screen_h
        self.scroll_tracker.update(y_px, lambda ticks: self._pyautogui().scroll(ticks))

    def reset_scroll(self) -> None:
        self.scroll_tracker.reset()
