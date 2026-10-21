import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from gesture_control.smoothing import EMASmoother


def test_first_update_returns_point_unchanged():
    s = EMASmoother(alpha=0.5)
    assert s.update((10, 20)) == (10, 20)


def test_smoothing_reduces_jitter():
    s = EMASmoother(alpha=0.3)
    s.update((0, 0))
    out = s.update((100, 100))
    # With alpha=0.3 the jump toward a noisy outlier should be damped.
    assert 0 < out[0] < 100
    assert abs(out[0] - 30) < 1e-6


def test_converges_to_constant_input():
    s = EMASmoother(alpha=0.5)
    for _ in range(50):
        out = s.update((42, 42))
    assert abs(out[0] - 42) < 1e-6
    assert abs(out[1] - 42) < 1e-6


def test_reset_clears_state():
    s = EMASmoother(alpha=0.5)
    s.update((5, 5))
    s.reset()
    assert s.value is None
    assert s.update((9, 9)) == (9, 9)


def test_invalid_alpha_rejected():
    with pytest.raises(ValueError):
        EMASmoother(alpha=0.0)
    with pytest.raises(ValueError):
        EMASmoother(alpha=1.5)
