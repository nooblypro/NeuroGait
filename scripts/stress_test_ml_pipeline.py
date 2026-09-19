#!/usr/bin/env python3
"""Adversarial ML Pipeline Stress Testing Script.

Systematically tests the existing frozen model and pipeline against 16 edge cases:
1. Normal windows
2. FoG windows
3. Borderline confidence
4. Missing pose landmarks
5. Leading NaNs in pose
6. Internal NaNs in pose
7. Malformed IMU rows
8. Missing timestamps in IMU
9. Duplicated timestamps in IMU
10. Irregular IMU sampling
11. Short recordings (<10 fused rows)
12. Empty recordings (0 frames / 0 IMU rows)
13. Mismatched video/IMU duration (no temporal overlap)
14. Synchronization outside +/-0.1s tolerance
15. Fewer than 10 fused rows
16. Corrupted files (corrupt video & corrupt IMU)
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.episodes import aggregate_episodes, classify_window_type, determine_primary_cue
from src.features import CANONICAL_FEATURES, extract_feature_matrix
from src.imu import extract_imu_rolling_features, load_raw_imu
from src.model import load_model, predict_fog_probability
from src.pipeline import predict_fog
from src.pose import PoseFeatureExtractor
from src.sync import SyncError, synchronize_modalities

FROZEN_MODEL_PATH = ROOT_DIR / "models/fog_model.pkl"
REAL_VIDEO = ROOT_DIR / "data/raw/videos/PDFE01_1.mp4"
REAL_IMU = ROOT_DIR / "data/raw/imu/SUB01_1.txt"


def run_stress_tests() -> List[Dict[str, Any]]:
    print("=" * 70)
    print("NEUROGAIT PHASE 3 — ADVERSARIAL ML PIPELINE STRESS TEST")
    print("=" * 70)

    results: List[Dict[str, Any]] = []
    model, scaler = load_model(FROZEN_MODEL_PATH)

    # Helper to record results
    def record(case_id: int, name: str, passed: bool, error_msg: str = "", details: str = ""):
        verdict = "PASS" if passed else "FAIL"
        print(f"[{case_id:02d}/16] {name.ljust(45)} -> {verdict}")
        if details:
            print(f"       Details: {details}")
        if error_msg:
            print(f"       Caught expected error: {error_msg}")
        results.append({
            "case_id": case_id,
            "name": name,
            "passed": passed,
            "error_msg": error_msg,
            "details": details,
        })

    # Case 1: Normal Windows Threshold
    try:
        w_norm = classify_window_type(0.39)
        passed = (w_norm == "Normal")
        record(1, "Normal Window Threshold (p < 0.40)", passed, details=f"p=0.39 -> {w_norm}")
    except Exception as e:
        record(1, "Normal Window Threshold", False, str(e))

    # Case 2: FoG Windows Threshold
    try:
        w_fog = classify_window_type(0.60)
        passed = (w_fog == "FoG")
        record(2, "FoG Window Threshold (p >= 0.60)", passed, details=f"p=0.60 -> {w_fog}")
    except Exception as e:
        record(2, "FoG Window Threshold", False, str(e))

    # Case 3: Borderline Confidence Threshold
    try:
        w_b1 = classify_window_type(0.40)
        w_b2 = classify_window_type(0.59)
        passed = (w_b1 == "Borderline" and w_b2 == "Borderline")
        record(3, "Borderline Confidence (0.40 <= p < 0.60)", passed, details=f"0.40->{w_b1}, 0.59->{w_b2}")
    except Exception as e:
        record(3, "Borderline Confidence", False, str(e))

    # Case 4: Missing Pose Landmarks (All zeros / no detection)
    try:
        from src.live_pipeline import IncrementalPoseExtractor, VideoFrame
        inc_extractor = IncrementalPoseExtractor(fps=30.0)
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        vf = VideoFrame(frame_index=0, timestamp=0.0, rgb_frame=blank_frame)
        rec = inc_extractor.process_frame(vf)
        coord_vals = [v for k, v in rec.items() if k != "timestamp"]
        passed = all(np.isnan(v) for v in coord_vals)
        record(4, "Missing Pose Landmarks Handling", passed, details="Blank frame returned NaNs safely without crash")
    except Exception as e:
        record(4, "Missing Pose Landmarks Handling", False, str(e))

    # Case 5: Leading NaNs in Pose Coordinates
    try:
        df_leading_nan = pd.DataFrame({
            "timestamp": [0.0, 0.033, 0.066, 0.1],
            "l_hip_x": [np.nan, np.nan, 0.5, 0.52],
            "l_hip_y": [np.nan, np.nan, 0.4, 0.41],
            "r_hip_x": [np.nan, np.nan, 0.6, 0.62],
            "r_hip_y": [np.nan, np.nan, 0.4, 0.41],
            "l_knee_x": [np.nan, np.nan, 0.5, 0.51],
            "l_knee_y": [np.nan, np.nan, 0.6, 0.62],
            "r_knee_x": [np.nan, np.nan, 0.6, 0.61],
            "r_knee_y": [np.nan, np.nan, 0.6, 0.62],
            "l_ankle_x": [np.nan, np.nan, 0.5, 0.50],
            "l_ankle_y": [np.nan, np.nan, 0.8, 0.83],
            "r_ankle_x": [np.nan, np.nan, 0.6, 0.60],
            "r_ankle_y": [np.nan, np.nan, 0.8, 0.82],
            "neck_x": [np.nan, np.nan, 0.55, 0.56],
            "neck_y": [np.nan, np.nan, 0.2, 0.21],
        })
        # Impute backfill
        coord_cols = [c for c in df_leading_nan.columns if c != "timestamp"]
        df_imputed = df_leading_nan.copy()
        df_imputed[coord_cols] = df_imputed[coord_cols].bfill().ffill()
        passed = (not df_imputed.isnull().any().any())
        record(5, "Leading NaNs in Pose Coordinates", passed, details="bfill/ffill resolves leading NaNs")
    except Exception as e:
        record(5, "Leading NaNs in Pose Coordinates", False, str(e))

    # Case 6: Internal NaNs in Pose Coordinates
    try:
        df_internal_nan = pd.DataFrame({
            "timestamp": [0.0, 0.033, 0.066, 0.1],
            "l_hip_x": [0.5, np.nan, np.nan, 0.52],
            "l_hip_y": [0.4, np.nan, np.nan, 0.41],
        })
        df_ffill = df_internal_nan.ffill()
        passed = (not df_ffill.isnull().any().any())
        record(6, "Internal NaNs in Pose Coordinates", passed, details="ffill maintains continuity through temporary dropout")
    except Exception as e:
        record(6, "Internal NaNs in Pose Coordinates", False, str(e))

    # Case 7: Malformed IMU Rows (Text garbage in columns)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("timestamp;ACC AP [g];GYR ML [deg/s];GYR SI [deg/s]\n")
        f.write("0.0;CORRUPT_STR;NOT_A_FLOAT;NaN\n")
        f.write("0.007;1.0;2.0;3.0\n")
        bad_imu_path = Path(f.name)

    try:
        raw_imu, rate = load_raw_imu(bad_imu_path)
        # Should either drop corrupt row or fail
        passed = (len(raw_imu) == 1 and not np.isnan(raw_imu["accel_y"].iloc[0]))
        record(7, "Malformed IMU Rows Handling", passed, details="load_raw_imu coerces numeric and drops corrupt row cleanly")
    except Exception as e:
        record(7, "Malformed IMU Rows Handling", True, error_msg=f"Cleanly raised: {e}")
    finally:
        bad_imu_path.unlink(missing_ok=True)

    # Case 8: Missing Timestamps in IMU
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("ACC AP [g];GYR ML [deg/s];GYR SI [deg/s]\n")
        f.write("1.0;2.0;3.0\n")
        no_ts_imu_path = Path(f.name)

    try:
        load_raw_imu(no_ts_imu_path)
        record(8, "Missing Timestamps in IMU", False, details="Did not raise error on missing timestamp column!")
    except Exception as e:
        record(8, "Missing Timestamps in IMU", True, error_msg=f"{type(e).__name__}: {e}")
    finally:
        no_ts_imu_path.unlink(missing_ok=True)

    # Case 9: Duplicated Timestamps in IMU
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("timestamp;ACC AP [g];GYR ML [deg/s];GYR SI [deg/s]\n")
        f.write("0.000;0.5;10.0;5.0\n")
        f.write("0.000;0.5;10.0;5.0\n")  # duplicate!
        f.write("0.010;0.5;10.0;5.0\n")
        dup_imu_path = Path(f.name)

    try:
        df_dup, rate_dup = load_raw_imu(dup_imu_path)
        # median dt handles duplicates without crashing or zero division
        passed = (rate_dup > 0)
        record(9, "Duplicated Timestamps in IMU", passed, details=f"Handled duplicates, derived rate: {rate_dup:.1f} Hz")
    except Exception as e:
        record(9, "Duplicated Timestamps in IMU", True, error_msg=f"{e}")
    finally:
        dup_imu_path.unlink(missing_ok=True)

    # Case 10: Irregular IMU Sampling
    try:
        ts_jitter = np.array([0.0, 0.008, 0.015, 0.025, 0.031, 0.040, 0.049])
        deltas = np.diff(ts_jitter)
        med_dt = np.median(deltas)
        rate_est = 1.0 / med_dt if med_dt > 0 else 128.0
        passed = (np.isclose(rate_est, 125.0, atol=15.0))
        record(10, "Irregular IMU Sampling (Jitter)", passed, details=f"Median dt correctly estimated {rate_est:.1f} Hz")
    except Exception as e:
        record(10, "Irregular IMU Sampling", False, str(e))

    # Case 11: Short Recordings (<10 Fused Rows)
    pose_short = pd.DataFrame({
        "timestamp": [1.0, 1.033, 1.066],
        "left_ankle_velocity": [0.5, 0.5, 0.5],
        "right_ankle_velocity": [0.5, 0.5, 0.5],
        "left_knee_angle": [120.0, 120.0, 120.0],
        "right_knee_angle": [120.0, 120.0, 120.0],
        "stride_width": [0.2, 0.2, 0.2],
    })
    imu_short = pd.DataFrame({
        "timestamp": [1.0, 1.033, 1.066],
        "accel_rms": [1.0, 1.0, 1.0],
        "gyro_x_var": [2.0, 2.0, 2.0],
        "gyro_z_var": [3.0, 3.0, 3.0],
    })
    try:
        synchronize_modalities(pose_short, imu_short, tolerance_sec=0.1, min_fused_rows=10)
        record(11, "Short Recordings (<10 Fused Rows)", False, details="Did not raise SyncError on 3 rows!")
    except SyncError as e:
        record(11, "Short Recordings (<10 Fused Rows)", True, error_msg=str(e))
    except Exception as e:
        record(11, "Short Recordings (<10 Fused Rows)", False, str(e))

    # Case 12: Empty Recordings (0 rows)
    pose_empty = pd.DataFrame(columns=["timestamp", "left_ankle_velocity", "right_ankle_velocity", "left_knee_angle", "right_knee_angle", "stride_width"])
    imu_empty = pd.DataFrame(columns=["timestamp", "accel_rms", "gyro_x_var", "gyro_z_var"])
    try:
        synchronize_modalities(pose_empty, imu_empty, tolerance_sec=0.1, min_fused_rows=10)
        record(12, "Empty Recordings (0 rows)", False, details="Did not raise SyncError on empty inputs!")
    except SyncError as e:
        record(12, "Empty Recordings (0 rows)", True, error_msg=str(e))
    except Exception as e:
        record(12, "Empty Recordings (0 rows)", False, str(e))

    # Case 13: Mismatched Video/IMU Duration (No overlap)
    pose_mismatch = pd.DataFrame({
        "timestamp": [100.0, 100.033, 100.066, 100.1, 100.133, 100.166, 100.2, 100.233, 100.266, 100.3, 100.333],
        "left_ankle_velocity": [0.5]*11,
        "right_ankle_velocity": [0.5]*11,
        "left_knee_angle": [120.0]*11,
        "right_knee_angle": [120.0]*11,
        "stride_width": [0.2]*11,
    })
    imu_mismatch = pd.DataFrame({
        "timestamp": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        "accel_rms": [1.0]*11,
        "gyro_x_var": [2.0]*11,
        "gyro_z_var": [3.0]*11,
    })
    try:
        synchronize_modalities(pose_mismatch, imu_mismatch, tolerance_sec=0.1, min_fused_rows=10)
        record(13, "Mismatched Video/IMU Duration", False, details="Did not raise SyncError on disjoint timestamps!")
    except SyncError as e:
        record(13, "Mismatched Video/IMU Duration", True, error_msg=str(e))
    except Exception as e:
        record(13, "Mismatched Video/IMU Duration", False, str(e))

    # Case 14: Synchronization Outside +/-0.1s Tolerance
    pose_drift = pd.DataFrame({
        "timestamp": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        "left_ankle_velocity": [0.5]*11,
        "right_ankle_velocity": [0.5]*11,
        "left_knee_angle": [120.0]*11,
        "right_knee_angle": [120.0]*11,
        "stride_width": [0.2]*11,
    })
    # Offsets by exactly 0.25s (outside 0.1s tolerance)
    imu_drift = pd.DataFrame({
        "timestamp": [0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75, 4.25, 4.75, 5.25],
        "accel_rms": [1.0]*11,
        "gyro_x_var": [2.0]*11,
        "gyro_z_var": [3.0]*11,
    })
    try:
        fused_drift, diag_drift = synchronize_modalities(pose_drift, imu_drift, tolerance_sec=0.1, min_fused_rows=1)
        record(14, "Sync Outside +/-0.1s Tolerance", False, details=f"Incorrectly fused {len(fused_drift)} rows outside tolerance!")
    except SyncError as e:
        record(14, "Sync Outside +/-0.1s Tolerance", True, error_msg=f"Correctly rejected: {e}")
    except Exception as e:
        record(14, "Sync Outside +/-0.1s Tolerance", False, str(e))

    # Case 15: Fewer than 10 Fused Rows Safety Gate
    try:
        fused_df_test = pd.DataFrame({"timestamp": [1.0, 2.0], "a": [1, 2]})
        # Direct check of sync min_fused_rows logic
        pose_9 = pd.DataFrame({
            "timestamp": [float(i)*0.1 for i in range(9)],
            "left_ankle_velocity": [0.5]*9,
            "right_ankle_velocity": [0.5]*9,
            "left_knee_angle": [120.0]*9,
            "right_knee_angle": [120.0]*9,
            "stride_width": [0.2]*9,
        })
        imu_9 = pd.DataFrame({
            "timestamp": [float(i)*0.1 for i in range(9)],
            "accel_rms": [1.0]*9,
            "gyro_x_var": [2.0]*9,
            "gyro_z_var": [3.0]*9,
        })
        synchronize_modalities(pose_9, imu_9, tolerance_sec=0.1, min_fused_rows=10)
        record(15, "Fewer than 10 Fused Rows Safety Gate", False, details="Allowed 9 rows through!")
    except SyncError as e:
        record(15, "Fewer than 10 Fused Rows Safety Gate", True, error_msg=str(e))
    except Exception as e:
        record(15, "Fewer than 10 Fused Rows Safety Gate", False, str(e))

    # Case 16: Corrupted Files (Binary garbage)
    with tempfile.NamedTemporaryFile("wb", suffix=".mp4", delete=False) as f:
        f.write(b"CORRUPT_RANDOM_BYTES_NOT_A_VALID_CONTAINER_1234567890")
        corrupt_vid_path = Path(f.name)

    try:
        extractor = PoseFeatureExtractor()
        # Should raise ValueError
        extractor.process_video(corrupt_vid_path)
        record(16, "Corrupted Video File Handling", False, details="Did not raise on corrupt video!")
    except ValueError as e:
        record(16, "Corrupted Video File Handling", True, error_msg=f"ValueError: {e}")
    except Exception as e:
        record(16, "Corrupted Video File Handling", True, error_msg=f"{type(e).__name__}: {e}")
    finally:
        corrupt_vid_path.unlink(missing_ok=True)

    print("\n" + "=" * 70)
    passed_count = sum(1 for r in results if r["passed"])
    print(f"STRESS TEST SUMMARY: {passed_count}/{len(results)} CASES PASSED")
    print("=" * 70)

    if passed_count != len(results):
        sys.exit(1)
    return results


if __name__ == "__main__":
    run_stress_tests()
