"""Shared pytest fixtures for NeuroGait test suite."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from src.features import CANONICAL_FEATURES


@pytest.fixture
def sample_timestamps() -> np.ndarray:
    """10-second timestamp array at 10 Hz."""
    return np.linspace(1.0, 10.0, 91)


@pytest.fixture
def sample_pose_df() -> pd.DataFrame:
    """Synthetic pose DataFrame with 100 frames at ~30 FPS."""
    t = np.linspace(0.0, 3.3, 100)
    data = {
        "timestamp": t,
        "left_ankle_velocity": 0.5 + 0.1 * np.sin(t),
        "right_ankle_velocity": 0.5 + 0.1 * np.cos(t),
        "left_knee_angle": 120.0 + 10.0 * np.sin(2 * t),
        "right_knee_angle": 125.0 + 10.0 * np.cos(2 * t),
        "stride_width": 0.25 + 0.05 * np.sin(t),
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_imu_df() -> pd.DataFrame:
    """Synthetic raw IMU DataFrame with 400 samples at ~128 Hz."""
    t = np.linspace(0.0, 3.125, 400)
    data = {
        "timestamp": t,
        "accel_y": 0.8 * np.sin(2 * np.pi * 2 * t) + 0.1 * np.random.randn(len(t)),
        "gyro_x": 15.0 * np.sin(2 * np.pi * 1.5 * t) + np.random.randn(len(t)),
        "gyro_z": 20.0 * np.cos(2 * np.pi * 1.5 * t) + np.random.randn(len(t)),
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_fused_df() -> pd.DataFrame:
    """Synthetic fused DataFrame satisfying all 8 canonical features."""
    N = 50
    t = np.linspace(1.0, 5.0, N)
    data = {
        "timestamp": t,
        "left_ankle_velocity": np.linspace(0.2, 0.8, N),
        "right_ankle_velocity": np.linspace(0.3, 0.9, N),
        "left_knee_angle": np.linspace(110.0, 140.0, N),
        "right_knee_angle": np.linspace(115.0, 145.0, N),
        "stride_width": np.linspace(0.2, 0.3, N),
        "accel_rms": np.linspace(0.5, 1.2, N),
        "gyro_x_var": np.linspace(10.0, 50.0, N),
        "gyro_z_var": np.linspace(15.0, 60.0, N),
    }
    return pd.DataFrame(data)


@pytest.fixture
def fitted_scaler() -> StandardScaler:
    """Pre-fitted StandardScaler on canonical features."""
    scaler = StandardScaler()
    X = np.array([
        [0.2, 0.2, 100.0, 100.0, 0.2, 0.5, 10.0, 10.0],
        [0.8, 0.8, 150.0, 150.0, 0.4, 1.5, 50.0, 50.0],
    ])
    scaler.fit(X)
    return scaler
