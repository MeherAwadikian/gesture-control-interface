"""Exponential-moving-average smoothing for jittery landmark/cursor positions."""
from __future__ import annotations

from typing import Optional, Tuple

Point = Tuple[float, float]


class EMASmoother:
    """Smooths a stream of 2D points with an exponential moving average.

    alpha close to 1.0 -> fast/responsive, more jitter.
    alpha close to 0.0 -> slow/laggy, very smooth.
    """

    def __init__(self, alpha: float = 0.5):
        if not (0.0 < alpha <= 1.0):
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        self.alpha = alpha
        self._value: Optional[Point] = None

    def update(self, point: Point) -> Point:
        if self._value is None:
            self._value = (float(point[0]), float(point[1]))
        else:
            ax = self.alpha
            px, py = self._value
            self._value = (px * (1 - ax) + point[0] * ax, py * (1 - ax) + point[1] * ax)
        return self._value

    @property
    def value(self) -> Optional[Point]:
        return self._value

    def reset(self) -> None:
        self._value = None
