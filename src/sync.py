"""Multimodal temporal synchronization for Pose and IMU data.

Synchronizes pose features and IMU rolling window features using nearest timestamps
with +/-0.1 second tolerance. Drops unmatched rows.

Raises SyncError if fused_rows < 10.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


class SyncError(RuntimeError):
    """Raised when temporal synchronization yields insufficient fused rows."""
    pass


def synchronize_modalities(
    pose_df: pd.DataFrame,
    imu_df: pd.DataFrame,
    tolerance_sec: float = 0.1,
    min_fused_rows: int = 10,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Synchronize pose features and IMU rolling features using nearest timestamps.

    Args:
        pose_df: DataFrame containing ['timestamp', 'left_ankle_velocity', 'right_ankle_velocity',
                                      'left_knee_angle', 'right_knee_angle', 'stride_width']
        imu_df: DataFrame containing ['timestamp', 'accel_rms', 'gyro_x_var', 'gyro_z_var']
        tolerance_sec: Maximum allowable timestamp difference (default 0.1s)
        min_fused_rows: Minimum required fused rows (default 10)

    Returns:
        fused_df: Synchronized DataFrame with all 8 features
        diagnostics: Dict with row counts pre and post synchronization
    """
    pose_pre = len(pose_df)
    imu_pre = len(imu_df)

    diagnostics = {
        "pose_rows_predrop": int(pose_pre),
        "imu_rows_predrop": int(imu_pre),
        "fused_rows": 0,
        "dropped_rows": 0,
    }

    if pose_df.empty or imu_df.empty:
        raise SyncError(
            f"SYNC ERROR: Cannot synchronize empty inputs. "
            f"Pose rows: {pose_pre}, IMU rows: {imu_pre}."
        )

    # Ensure sorted by timestamp
    p_sorted = pose_df.sort_values("timestamp").reset_index(drop=True)
    i_sorted = imu_df.sort_values("timestamp").reset_index(drop=True)

    # Merge asof nearest within tolerance_sec
    # We match IMU rolling window ends to nearest pose frame
    merged = pd.merge_asof(
        i_sorted,
        p_sorted,
        on="timestamp",
        direction="nearest",
        tolerance=tolerance_sec,
        suffixes=("", "_pose"),
    )

    # Drop any unmatched rows where pose features could not be found within tolerance
    pose_cols = [
        "left_ankle_velocity",
        "right_ankle_velocity",
        "left_knee_angle",
        "right_knee_angle",
        "stride_width",
    ]
    fused_df = merged.dropna(subset=pose_cols).reset_index(drop=True)
    fused_count = len(fused_df)
    diagnostics["fused_rows"] = int(fused_count)
    diagnostics["dropped_rows"] = int(imu_pre - fused_count)

    if fused_count < min_fused_rows:
        raise SyncError(
            f"SYNC ERROR: Only {fused_count} rows fused (< {min_fused_rows} required). "
            f"Pose pre-drop: {pose_pre}, IMU pre-drop: {imu_pre}, tolerance: {tolerance_sec}s."
        )

    return fused_df, diagnostics
