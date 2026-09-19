"""IMU data parsing and feature extraction.

Processes raw IMU data from CSV/TXT files and computes 1-second rolling window features:
- accel_rms = sqrt(mean(accel_y^2))
- gyro_x_var = variance(gyro_x)
- gyro_z_var = variance(gyro_z)

Rules:
- Do not forward-fill IMU data.
- Derive sampling rate from timestamp deltas.
- Labeled by window END timestamp.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


def detect_imu_columns(columns: List[str]) -> Dict[str, str]:
    """Map raw IMU column names to canonical internal names:
    - 'timestamp'
    - 'accel_y' (Anteroposterior / AP)
    - 'gyro_x'  (Mediolateral / ML)
    - 'gyro_z'  (Superior-inferior / SI)
    - 'fog_flag' (Optional freezing event flag)
    """
    col_map: Dict[str, str] = {}
    lower_cols = {c.strip().lower(): c for c in columns}

    # Timestamp
    for pattern in ["time [s]", "time", "timestamp", "t", "seconds", "sec"]:
        if pattern in lower_cols:
            col_map["timestamp"] = lower_cols[pattern]
            break

    # Accel Y (Anteroposterior)
    for pattern in ["acc ap [g]", "acc_ap", "acc ap", "accel_y", "acc_y", "acceleration_y", "acc y"]:
        if pattern in lower_cols:
            col_map["accel_y"] = lower_cols[pattern]
            break

    # Gyro X (Mediolateral)
    for pattern in ["gyr ml [deg/s]", "gyr_ml", "gyr ml", "gyro_x", "gyr_x", "angular_velocity_x", "gyr x"]:
        if pattern in lower_cols:
            col_map["gyro_x"] = lower_cols[pattern]
            break

    # Gyro Z (Superior-inferior)
    for pattern in ["gyr si [deg/s]", "gyr_si", "gyr si", "gyro_z", "gyr_z", "angular_velocity_z", "gyr z"]:
        if pattern in lower_cols:
            col_map["gyro_z"] = lower_cols[pattern]
            break

    # Optional Freezing event flag
    for pattern in ["freezing event [flag]", "freezing event", "fog_flag", "flag", "label", "fog"]:
        if pattern in lower_cols:
            col_map["fog_flag"] = lower_cols[pattern]
            break

    # Fallback to positional if standard names not detected
    if "timestamp" not in col_map and len(columns) >= 2:
        col_map["timestamp"] = columns[1] if columns[0].lower().startswith("frame") else columns[0]
    if "accel_y" not in col_map and len(columns) >= 4:
        # Columns in Figshare: Frame, Time, ACC ML, ACC AP, ACC SI, GYR ML, GYR AP, GYR SI
        col_map["accel_y"] = columns[3]
    if "gyro_x" not in col_map and len(columns) >= 6:
        col_map["gyro_x"] = columns[5]
    if "gyro_z" not in col_map and len(columns) >= 8:
        col_map["gyro_z"] = columns[7]

    return col_map


def load_raw_imu(file_path: Union[str, Path]) -> Tuple[pd.DataFrame, float]:
    """Load raw IMU file (CSV or TXT) and calculate sampling rate from timestamp deltas.

    Returns:
        df: DataFrame with standard columns ['timestamp', 'accel_y', 'gyro_x', 'gyro_z']
            and optionally 'fog_flag'
        sampling_rate: Computed sampling rate in Hz
    """
    path_str = str(file_path)
    if not os.path.exists(path_str):
        raise FileNotFoundError(f"IMU file not found: {path_str}")

    # Inspect first few lines to determine delimiter
    with open(path_str, "rb") as f:
        head_bytes = f.read(2048)

    # Detect if file is binary OLE/BIFF (Excel format saved as .csv)
    if head_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        # Check if corresponding .txt exists alongside
        txt_alt = Path(path_str).with_suffix(".txt")
        if txt_alt.exists():
            return load_raw_imu(txt_alt)
        # Otherwise attempt reading with excel engine or raise informative error
        try:
            raw = pd.read_excel(path_str)
        except Exception as e:
            raise ValueError(
                f"File {path_str} is in binary Excel format. Please provide the plain text (.txt) file: {e}"
            )
    else:
        text_sample = head_bytes.decode("utf-8", errors="ignore")
        if "\t" in text_sample.splitlines()[0]:
            sep = "\t"
        elif ";" in text_sample.splitlines()[0]:
            sep = ";"
        elif "," in text_sample.splitlines()[0]:
            sep = ","
        else:
            sep = r"\s+"

        raw = pd.read_csv(path_str, sep=sep, engine="python")

    col_map = detect_imu_columns(list(raw.columns))
    required = ["timestamp", "accel_y", "gyro_x", "gyro_z"]
    missing = [req for req in required if req not in col_map]
    if missing:
        raise ValueError(f"Missing required IMU sensor columns in {path_str}: {missing}")

    rename_dict = {
        col_map["timestamp"]: "timestamp",
        col_map["accel_y"]: "accel_y",
        col_map["gyro_x"]: "gyro_x",
        col_map["gyro_z"]: "gyro_z",
    }
    if "fog_flag" in col_map:
        rename_dict[col_map["fog_flag"]] = "fog_flag"

    clean_df = raw[list(rename_dict.keys())].rename(columns=rename_dict)

    # Convert to numeric, no forward fill
    for c in clean_df.columns:
        clean_df[c] = pd.to_numeric(clean_df[c], errors="coerce")

    # Drop any NaNs in raw data (IMU: no forward-fill)
    clean_df = clean_df.dropna().sort_values("timestamp").reset_index(drop=True)

    if len(clean_df) < 2:
        raise ValueError(f"Insufficient IMU rows in {path_str}: {len(clean_df)}")

    # Calculate actual sampling rate from timestamp deltas
    dt_series = np.diff(clean_df["timestamp"].to_numpy())
    valid_dts = dt_series[dt_series > 0]
    if len(valid_dts) == 0:
        raise ValueError(f"Invalid non-increasing timestamps in {path_str}")

    median_dt = float(np.median(valid_dts))
    sampling_rate = float(1.0 / median_dt) if median_dt > 0 else 128.0

    return clean_df, sampling_rate


def compute_accel_rms(accel_y: np.ndarray) -> float:
    """Implement exact formula: accel_rms = sqrt(mean(accel_y^2))."""
    if len(accel_y) == 0:
        return np.nan
    return float(np.sqrt(np.mean(accel_y ** 2)))


def compute_gyro_x_var(gyro_x: np.ndarray) -> float:
    """Implement exact formula: gyro_x_var = variance(gyro_x)."""
    if len(gyro_x) < 2:
        return 0.0
    return float(np.var(gyro_x, ddof=1))


def compute_gyro_z_var(gyro_z: np.ndarray) -> float:
    """Implement exact formula: gyro_z_var = variance(gyro_z)."""
    if len(gyro_z) < 2:
        return 0.0
    return float(np.var(gyro_z, ddof=1))


def extract_imu_rolling_features(
    imu_df: pd.DataFrame,
    window_sec: float = 1.0,
    target_timestamps: Optional[np.ndarray] = None,
    step_sec: float = 0.1,
) -> pd.DataFrame:
    """Create 1-second rolling IMU windows labeled by END timestamp.

    Args:
        imu_df: DataFrame with ['timestamp', 'accel_y', 'gyro_x', 'gyro_z']
        window_sec: Duration of the rolling window in seconds (default 1.0)
        target_timestamps: Explicit window end timestamps to evaluate.
                           If None, generates ends from t_min + window_sec to t_max with step_sec.
        step_sec: Step size between window ends when target_timestamps is None.

    Returns:
        DataFrame containing:
        ['timestamp', 'accel_rms', 'gyro_x_var', 'gyro_z_var']
        and 'fog_flag' if present in input.
    """
    ts_arr = imu_df["timestamp"].to_numpy(dtype=np.float64)
    ay_arr = imu_df["accel_y"].to_numpy(dtype=np.float64)
    gx_arr = imu_df["gyro_x"].to_numpy(dtype=np.float64)
    gz_arr = imu_df["gyro_z"].to_numpy(dtype=np.float64)
    has_flag = "fog_flag" in imu_df.columns
    flag_arr = imu_df["fog_flag"].to_numpy(dtype=np.float64) if has_flag else None

    t_min = ts_arr[0]
    t_max = ts_arr[-1]

    if target_timestamps is not None:
        end_times = np.asarray(target_timestamps, dtype=np.float64)
    else:
        first_end = t_min + window_sec
        if first_end > t_max:
            return pd.DataFrame(columns=["timestamp", "accel_rms", "gyro_x_var", "gyro_z_var"])
        end_times = np.arange(first_end, t_max + 1e-6, step_sec)

    results: List[Dict[str, float]] = []

    for t_end in end_times:
        t_start = t_end - window_sec
        # Window samples strictly: t_start < t <= t_end
        idx_start = np.searchsorted(ts_arr, t_start, side="right")
        idx_end = np.searchsorted(ts_arr, t_end, side="right")

        if idx_end <= idx_start:
            continue

        w_ay = ay_arr[idx_start:idx_end]
        w_gx = gx_arr[idx_start:idx_end]
        w_gz = gz_arr[idx_start:idx_end]

        rms = compute_accel_rms(w_ay)
        gx_var = compute_gyro_x_var(w_gx)
        gz_var = compute_gyro_z_var(w_gz)

        record = {
            "timestamp": float(t_end),
            "accel_rms": rms,
            "gyro_x_var": gx_var,
            "gyro_z_var": gz_var,
        }

        if has_flag and flag_arr is not None:
            w_flag = flag_arr[idx_start:idx_end]
            # Label as FoG (1) if majority or any freezing in window
            record["fog_flag"] = 1.0 if np.mean(w_flag) >= 0.5 else 0.0

        results.append(record)

    out_df = pd.DataFrame(results)
    return out_df
