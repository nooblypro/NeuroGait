"""Unit tests for IMU parsing and rolling window features."""

import numpy as np
import pandas as pd
import pytest

from src.imu import (
    compute_accel_rms,
    compute_gyro_x_var,
    compute_gyro_z_var,
    detect_imu_columns,
    extract_imu_rolling_features,
    load_raw_imu,
)


def test_detect_imu_columns():
    """Detects standard Figshare IMU columns."""
    figshare_cols = [
        "Frame #", "Time [s]", "ACC ML [g]", "ACC AP [g]",
        "ACC SI [g]", "GYR ML [deg/s]", "GYR AP [deg/s]", "GYR SI [deg/s]", "Freezing event [flag]"
    ]
    mapping = detect_imu_columns(figshare_cols)
    assert mapping["timestamp"] == "Time [s]"
    assert mapping["accel_y"] == "ACC AP [g]"
    assert mapping["gyro_x"] == "GYR ML [deg/s]"
    assert mapping["gyro_z"] == "GYR SI [deg/s]"
    assert mapping["fog_flag"] == "Freezing event [flag]"


def test_detect_imu_columns_lowercase_variants():
    """Detects lowercase generic IMU column names."""
    generic_cols = ["timestamp", "accel_y", "gyro_x", "gyro_z"]
    mapping = detect_imu_columns(generic_cols)
    assert mapping["timestamp"] == "timestamp"
    assert mapping["accel_y"] == "accel_y"
    assert mapping["gyro_x"] == "gyro_x"
    assert mapping["gyro_z"] == "gyro_z"


def test_accel_rms_formula():
    """accel_rms = sqrt(mean(y^2)). For [3, 4], mean(sq) = (9+16)/2 = 12.5 -> sqrt(12.5) = 3.5355."""
    arr = np.array([3.0, 4.0])
    expected = np.sqrt((9.0 + 16.0) / 2.0)
    res = compute_accel_rms(arr)
    assert np.isclose(res, expected)


def test_gyro_variance_formulas():
    """Sample variance with ddof=1: [10, 20, 30] -> var = 100."""
    arr = np.array([10.0, 20.0, 30.0])
    expected = 100.0
    assert np.isclose(compute_gyro_x_var(arr), expected)
    assert np.isclose(compute_gyro_z_var(arr), expected)


def test_rolling_windows_end_timestamps(sample_imu_df):
    """Verify rolling windows are labeled strictly by END timestamp."""
    window_sec = 1.0
    features_df = extract_imu_rolling_features(sample_imu_df, window_sec=window_sec, step_sec=0.1)

    assert not features_df.empty
    assert "timestamp" in features_df.columns
    assert "accel_rms" in features_df.columns
    assert "gyro_x_var" in features_df.columns
    assert "gyro_z_var" in features_df.columns

    # Verify that the first end timestamp is >= t_min + window_sec
    first_end = features_df["timestamp"].iloc[0]
    t_min = sample_imu_df["timestamp"].iloc[0]
    assert first_end >= t_min + window_sec - 1e-5


def test_sampling_rate_discovery(tmp_path):
    """Verify sampling rate is correctly derived from timestamp deltas."""
    # Write a small 128 Hz file
    t = np.arange(0, 1.0, 1.0 / 128.0)
    df = pd.DataFrame({
        "Time [s]": t,
        "ACC AP [g]": np.zeros(len(t)),
        "GYR ML [deg/s]": np.zeros(len(t)),
        "GYR SI [deg/s]": np.zeros(len(t)),
    })
    csv_file = tmp_path / "test_128hz.txt"
    df.to_csv(csv_file, sep="\t", index=False)

    loaded_df, rate = load_raw_imu(csv_file)
    assert np.isclose(rate, 128.0, atol=0.5)
    assert len(loaded_df) == len(t)
