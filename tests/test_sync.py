"""Unit tests for temporal synchronization."""

import numpy as np
import pandas as pd
import pytest

from src.sync import SyncError, synchronize_modalities


def test_synchronization_within_tolerance(sample_pose_df, sample_imu_df):
    """Verify that rows within 0.1s are successfully matched."""
    from src.imu import extract_imu_rolling_features

    imu_feat = extract_imu_rolling_features(sample_imu_df, window_sec=1.0, step_sec=0.1)
    fused, diag = synchronize_modalities(sample_pose_df, imu_feat, tolerance_sec=0.1, min_fused_rows=10)

    assert len(fused) >= 10
    assert diag["fused_rows"] == len(fused)
    assert "left_ankle_velocity" in fused.columns
    assert "accel_rms" in fused.columns


def test_synchronization_drops_unmatched():
    """Verify that timestamps outside the 0.1s tolerance window are dropped."""
    # Pose timestamps around 10.0s
    pose_df = pd.DataFrame({
        "timestamp": [10.0, 10.1, 10.2],
        "left_ankle_velocity": [0.5, 0.5, 0.5],
        "right_ankle_velocity": [0.5, 0.5, 0.5],
        "left_knee_angle": [120.0, 120.0, 120.0],
        "right_knee_angle": [120.0, 120.0, 120.0],
        "stride_width": [0.2, 0.2, 0.2],
    })
    # IMU timestamps around 0.0s (10 seconds away!)
    imu_df = pd.DataFrame({
        "timestamp": [0.0, 0.1, 0.2],
        "accel_rms": [1.0, 1.0, 1.0],
        "gyro_x_var": [2.0, 2.0, 2.0],
        "gyro_z_var": [3.0, 3.0, 3.0],
    })

    with pytest.raises(SyncError, match="SYNC ERROR"):
        synchronize_modalities(pose_df, imu_df, tolerance_sec=0.1, min_fused_rows=1)


def test_sync_error_under_10_rows(sample_pose_df, sample_imu_df):
    """Verify that SyncError is raised if fused rows < 10."""
    from src.imu import extract_imu_rolling_features

    # Take only 5 pose frames
    small_pose = sample_pose_df.iloc[:5]
    imu_feat = extract_imu_rolling_features(sample_imu_df, window_sec=1.0, step_sec=0.1)

    with pytest.raises(SyncError, match="SYNC ERROR: Only"):
        synchronize_modalities(small_pose, imu_feat, tolerance_sec=0.1, min_fused_rows=10)
