"""Unit tests for pose calculations and geometry."""

import numpy as np
import pytest

from src.pose import calculate_knee_angle, calculate_stride_width, calculate_velocity


def test_knee_angle_orthogonal():
    """Right angle (90 degrees): hip at (0, 1), knee at (0, 0), ankle at (1, 0)."""
    hip = (0.0, 1.0)
    knee = (0.0, 0.0)
    ankle = (1.0, 0.0)
    angle = calculate_knee_angle(hip, knee, ankle)
    assert np.isclose(angle, 90.0), f"Expected 90 degrees, got {angle}"


def test_knee_angle_straight():
    """Straight leg (180 degrees): hip at (0, 1), knee at (0, 0), ankle at (0, -1)."""
    hip = (0.0, 1.0)
    knee = (0.0, 0.0)
    ankle = (0.0, -1.0)
    angle = calculate_knee_angle(hip, knee, ankle)
    assert np.isclose(angle, 180.0), f"Expected 180 degrees, got {angle}"


def test_knee_angle_fully_flexed():
    """Acute angle (45 degrees): hip at (1, 1), knee at (0, 0), ankle at (1, 0)."""
    hip = (1.0, 1.0)
    knee = (0.0, 0.0)
    ankle = (1.0, 0.0)
    angle = calculate_knee_angle(hip, knee, ankle)
    assert np.isclose(angle, 45.0), f"Expected 45 degrees, got {angle}"


def test_knee_angle_zero_length_vector():
    """Colocated joints should return NaN without raising ZeroDivisionError."""
    hip = (0.0, 0.0)
    knee = (0.0, 0.0)
    ankle = (1.0, 0.0)
    angle = calculate_knee_angle(hip, knee, ankle)
    assert np.isnan(angle)


def test_stride_width():
    """Euclidean distance between ankles: (0.2, 0.8) and (0.6, 0.5) -> dist = 0.5."""
    l_ankle = (0.2, 0.8)
    r_ankle = (0.6, 0.5)
    sw = calculate_stride_width(l_ankle, r_ankle)
    assert np.isclose(sw, 0.5), f"Expected 0.5, got {sw}"


def test_velocity():
    """Velocity: distance / dt."""
    p_prev = (0.1, 0.2)
    p_curr = (0.4, 0.6)  # distance = 0.5
    dt = 0.05  # 20 Hz
    v = calculate_velocity(p_curr, p_prev, dt)
    assert np.isclose(v, 10.0), f"Expected 10.0, got {v}"


def test_velocity_invalid_dt():
    """Non-positive dt should return NaN."""
    assert np.isnan(calculate_velocity((1.0, 1.0), (0.0, 0.0), 0.0))
    assert np.isnan(calculate_velocity((1.0, 1.0), (0.0, 0.0), -0.1))
