"""Training and inference pipeline entry points for NeuroGait.

Provides:
- train_model(dataset_dir, model_output_path="models/fog_model.pkl")
- predict_fog(video_path, csv_path, model_path="models/fog_model.pkl", output_json_path=None)
"""

from __future__ import annotations

import csv
import glob
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.contract import format_episodes_json, save_canonical_json
from src.episodes import aggregate_episodes
from src.features import CANONICAL_FEATURES, extract_feature_matrix, get_canonical_feature_names
from src.imu import extract_imu_rolling_features, load_raw_imu
from src.model import build_model, fit_model, load_model, predict_fog_probability, save_model
from src.pose import PoseFeatureExtractor
from src.sync import synchronize_modalities


def parse_pdfe_intervals(label_str: str) -> List[Tuple[float, float]]:
    """Parse intervals from string like '[1.383-35.768; 36.696-65.969]'.

    Returns:
        List of (start, end) tuples in seconds.
    """
    cleaned = str(label_str).strip()
    if not cleaned or cleaned in {"-", "0", "0.0", "nan", "None"}:
        return []

    # Strip enclosing brackets/quotes
    cleaned = cleaned.replace("[", "").replace("]", "").replace('"', "").strip()
    if not cleaned:
        return []

    intervals: List[Tuple[float, float]] = []
    for part in cleaned.split(";"):
        part = part.strip()
        if "-" in part:
            subparts = part.split("-")
            try:
                t0 = float(subparts[0].strip())
                t1 = float(subparts[1].strip())
                if t1 < t0:
                    # In case of malformed data e.g. 37.609-9.659
                    t0, t1 = min(t0, t1), max(t0, t1)
                intervals.append((t0, t1))
            except ValueError:
                continue
    return intervals


def is_timestamp_in_intervals(t: float, intervals: List[Tuple[float, float]]) -> int:
    """Return 1 if timestamp t falls within any [start, end] interval, else 0."""
    for start, end in intervals:
        if start <= t <= end:
            return 1
    return 0


def print_diagnostics(
    video_duration: float,
    video_fps: float,
    imu_sampling_rate: float,
    pose_rows_predrop: int,
    fused_rows: int,
    fog_windows: int,
    normal_windows: int,
    label_source: str,
    input_shape: Tuple[int, int],
    dropped_rows: int = 0,
    model_artifact_path: Optional[str] = None,
    pairing_status: Optional[str] = None,
) -> None:
    """Print the exact diagnostic summary matching Section 14 specification."""
    print("=" * 50)
    print("DATASET SUMMARY")
    print("---------------")
    print(f"Video duration: {video_duration:.2f} s")
    print(f"Video FPS: {video_fps:.2f}")
    print(f"IMU sampling rate: {imu_sampling_rate:.1f} Hz")
    print(f"Pose rows (pre-drop): {pose_rows_predrop}")
    print(f"Fused rows: {fused_rows}")
    print(f"FoG labeled windows: {fog_windows}")
    print(f"Normal labeled windows: {normal_windows}")
    print(f"Label source: {label_source}")
    if dropped_rows > 0:
        print(f"Dropped rows during sync: {dropped_rows}")
    if pairing_status:
        print(f"Subject pairing: {pairing_status}")

    print("\nFEATURE SUMMARY")
    print("---------------")
    print(f"Feature count: {len(CANONICAL_FEATURES)}")
    print("Feature names:")
    for idx, name in enumerate(CANONICAL_FEATURES, 1):
        print(f"{idx}. {name}")
    print(f"\nModel input shape: {input_shape}")
    if model_artifact_path:
        print(f"Model artifact path: {model_artifact_path}")
    print("=" * 50 + "\n")


def train_model(
    dataset_dir: Union[str, Path],
    model_output_path: Union[str, Path] = "models/fog_model.pkl",
    max_subjects: Optional[int] = None,
    max_video_frames: Optional[int] = None,
) -> Dict[str, Any]:
    """Train the NeuroGait Phase 1 model on available subjects in the dataset.

    Args:
        dataset_dir: Path to dataset directory containing videos, IMU files, and PDFEinfo.csv
        model_output_path: Destination path for saved joblib model artifact
        max_subjects: Optional limit on subjects for fast execution
        max_video_frames: Optional limit on frames per video

    Returns:
        Summary dict containing training metrics and artifact path.
    """
    d_dir = Path(dataset_dir)
    if not d_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {d_dir}")

    # Locate PDFEinfo.csv
    info_candidates = list(d_dir.glob("**/PDFEinfo.csv")) + list(d_dir.glob("PDFEinfo.csv"))
    if not info_candidates:
        # Check /tmp/PDFEinfo.csv fallback
        if Path("/tmp/PDFEinfo.csv").exists():
            info_file = Path("/tmp/PDFEinfo.csv")
        else:
            raise FileNotFoundError(f"PDFEinfo.csv not found in {d_dir}")
    else:
        info_file = info_candidates[0]

    # Parse clinical info and labels
    clinical_labels: Dict[str, List[Tuple[float, float]]] = {}
    with open(info_file, encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)
        for r in rows[1:]:
            if r and r[0].startswith("PDFE"):
                sub_id = r[0].strip()
                s1 = r[24] if len(r) > 24 else ""
                s2 = r[42] if len(r) > 42 else ""
                s3 = r[60] if len(r) > 60 else ""
                clinical_labels[f"{sub_id}_1"] = parse_pdfe_intervals(s1)
                clinical_labels[f"{sub_id}_2"] = parse_pdfe_intervals(s2)
                clinical_labels[f"{sub_id}_3"] = parse_pdfe_intervals(s3)

    # Search for available video and IMU pairs (deduplicated by resolved path)
    raw_video_files = list(d_dir.glob("**/videos/*.mp4")) + list(d_dir.glob("*.mp4"))
    if not raw_video_files:
        raw_video_files = list(Path("data/raw/videos").glob("*.mp4"))

    # Deduplicate resolved paths
    unique_video_paths = {p.resolve(): p for p in raw_video_files}
    video_files = sorted(unique_video_paths.values())

    # Verify pairing table for every candidate subject
    print("\nSUBJECT PAIRING VERIFICATION")
    print("-" * 75)
    print(f"{'SUBJECT':<12} | {'VIDEO':<24} | {'IMU':<20} | {'STATUS':<10}")
    print("-" * 75)

    verified_pairs: List[Tuple[str, Path, Path, List[Tuple[float, float]]]] = []

    for v_path in sorted(video_files):
        stem = v_path.stem  # e.g. PDFE01_1
        parts = stem.split("_")
        if len(parts) < 2:
            continue
        sub_str = parts[0]  # PDFE01
        sess_str = parts[1]  # 1

        # Match IMU: PDFE01 -> SUB01
        imu_sub = sub_str.replace("PDFE", "SUB")
        imu_candidates = (
            list(d_dir.glob(f"**/imu/{imu_sub}_{sess_str}.txt"))
            + list(d_dir.glob(f"**/imu/{imu_sub}_{sess_str}.csv"))
            + list(Path("data/raw/imu").glob(f"{imu_sub}_{sess_str}.txt"))
            + list(Path("data/raw/imu").glob(f"{imu_sub}_{sess_str}.csv"))
        )

        has_v = v_path.exists()
        has_imu = len(imu_candidates) > 0
        imu_file = imu_candidates[0] if has_imu else None
        label_intervals = clinical_labels.get(stem, [])

        status = "VERIFIED" if (has_v and has_imu) else "INVALID"
        print(f"{stem:<12} | {v_path.name:<24} | {imu_file.name if imu_file else 'MISSING':<20} | {status:<10}")

        if status == "VERIFIED" and imu_file is not None:
            verified_pairs.append((stem, v_path, imu_file, label_intervals))

    print("-" * 75)
    print(f"Total Verified Subject Pairs Available for Training: {len(verified_pairs)}\n")

    if not verified_pairs:
        raise FileNotFoundError("STOP — No verified subject video/IMU pairs found for training.")

    if max_subjects is not None:
        verified_pairs = verified_pairs[:max_subjects]

    # Process all verified pairs and extract canonical features + labels
    all_X_list: List[np.ndarray] = []
    all_y_list: List[np.ndarray] = []

    total_fog_windows = 0
    total_norm_windows = 0
    total_fused = 0
    total_pose_predrop = 0
    last_fps = 29.98
    last_rate = 128.0
    last_duration = 0.0

    extractor = PoseFeatureExtractor()
    try:
        for stem, v_path, imu_path, intervals in verified_pairs:
            print(f"Processing subject {stem}...")
            # 1. Pose features
            pose_df, v_meta = extractor.process_video(v_path, max_frames=max_video_frames)
            total_pose_predrop += v_meta.get("total_frames", len(pose_df))
            last_fps = v_meta.get("video_fps", last_fps)
            last_duration = max(last_duration, v_meta.get("duration", 0.0))

            # 2. IMU features
            raw_imu_df, imu_rate = load_raw_imu(imu_path)
            last_rate = imu_rate
            imu_feat_df = extract_imu_rolling_features(raw_imu_df, window_sec=1.0)

            # 3. Synchronize modalities
            fused_df, sync_diag = synchronize_modalities(pose_df, imu_feat_df, tolerance_sec=0.1)
            total_fused += len(fused_df)

            # 4. Extract canonical 8-feature matrix
            X_subj = extract_feature_matrix(fused_df)

            # 5. Extract ground-truth labels for each synchronized window
            # If IMU had freezing event flag, verify against intervals
            timestamps = fused_df["timestamp"].to_numpy()
            y_subj = np.zeros(len(timestamps), dtype=np.int64)

            for i, t in enumerate(timestamps):
                # If explicit intervals exist in PDFEinfo.csv
                if len(intervals) > 0:
                    y_subj[i] = is_timestamp_in_intervals(float(t), intervals)
                elif "fog_flag" in fused_df.columns:
                    y_subj[i] = int(fused_df["fog_flag"].iloc[i])
                else:
                    y_subj[i] = 0

            fog_count = int(np.sum(y_subj == 1))
            norm_count = int(np.sum(y_subj == 0))
            total_fog_windows += fog_count
            total_norm_windows += norm_count
            print(f"  -> Fused: {len(fused_df)} windows (FoG: {fog_count}, Normal: {norm_count})")

            all_X_list.append(X_subj)
            all_y_list.append(y_subj)
    finally:
        extractor.close()

    X_total = np.vstack(all_X_list)
    y_total = np.concatenate(all_y_list)

    # Check for degenerate labels
    unique_classes = np.unique(y_total)
    if len(unique_classes) < 2:
        raise ValueError(
            f"STOP — DEGENERATE LABELS ERROR: Ground truth contains only class {unique_classes}. "
            f"Training requires both FoG (1) and Normal (0) samples."
        )

    # Train model
    model, scaler = build_model()
    train_acc = fit_model(model, scaler, X_total, y_total)
    saved_path = save_model(model, scaler, model_output_path)

    # Diagnostics output
    print_diagnostics(
        video_duration=last_duration,
        video_fps=last_fps,
        imu_sampling_rate=last_rate,
        pose_rows_predrop=total_pose_predrop,
        fused_rows=total_fused,
        fog_windows=total_fog_windows,
        normal_windows=total_norm_windows,
        label_source="REAL (Figshare PDFEinfo.csv + IMU flag)",
        input_shape=X_total.shape,
        model_artifact_path=saved_path,
        pairing_status="VERIFIED",
    )

    print(f"Training completed successfully. Internal Sanity Accuracy: {train_acc * 100:.2f}%\n")

    return {
        "status": "SUCCESS",
        "train_accuracy": train_acc,
        "total_windows": len(X_total),
        "fog_windows": total_fog_windows,
        "normal_windows": total_norm_windows,
        "model_artifact_path": saved_path,
        "input_shape": list(X_total.shape),
    }


def predict_fog(
    video_path: Union[str, Path],
    csv_path: Union[str, Path],
    model_path: Union[str, Path] = "models/fog_model.pkl",
    output_json_path: Optional[Union[str, Path]] = None,
    max_frames: Optional[int] = None,
    data_mode: str = "real",
) -> List[Dict[str, Any]]:
    """Predict FoG episodes and primary cues from a test video and IMU file.

    Args:
        video_path: Path to patient video (.mp4)
        csv_path: Path to patient IMU file (.txt or .csv)
        model_path: Path to trained joblib model artifact
        output_json_path: Optional path to save canonical JSON output
        max_frames: Optional frame limit
        data_mode: "real" or "synthetic_demo"

    Returns:
        List of serialized canonical episode dictionaries.
    """
    v_path = Path(video_path)
    c_path = Path(csv_path)
    m_path = Path(model_path)

    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found: {v_path}")
    if not c_path.exists():
        raise FileNotFoundError(f"IMU file not found: {c_path}")
    if not m_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {m_path}")

    # 1. Load model and scaler
    model, scaler = load_model(m_path)

    # 2. Extract pose features
    with PoseFeatureExtractor() as extractor:
        pose_df, v_meta = extractor.process_video(v_path, max_frames=max_frames)

    # 3. Load IMU and extract rolling features
    raw_imu_df, imu_rate = load_raw_imu(c_path)
    imu_feat_df = extract_imu_rolling_features(raw_imu_df, window_sec=1.0)

    # 4. Synchronize modalities with +/-0.1s tolerance
    fused_df, sync_diag = synchronize_modalities(pose_df, imu_feat_df, tolerance_sec=0.1)

    # 5. Extract canonical 8-feature matrix
    X = extract_feature_matrix(fused_df)

    # 6. Predict class-1 probabilities
    probs = predict_fog_probability(model, scaler, X)

    # 7. Aggregate episodes, merge gaps <= 1s, compute primary cue
    timestamps = fused_df["timestamp"].to_numpy()
    episodes = aggregate_episodes(
        timestamps=timestamps,
        probabilities=probs,
        X=X,
        scaler=scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
        data_mode=data_mode,
    )

    # Diagnostics
    fog_count = int(np.sum(probs >= 0.60))
    norm_count = int(np.sum(probs < 0.40))
    print_diagnostics(
        video_duration=v_meta.get("duration", 0.0),
        video_fps=v_meta.get("video_fps", 29.98),
        imu_sampling_rate=imu_rate,
        pose_rows_predrop=v_meta.get("total_frames", len(pose_df)),
        fused_rows=len(fused_df),
        fog_windows=fog_count,
        normal_windows=norm_count,
        label_source="MODEL PREDICTION (RandomForest)",
        input_shape=X.shape,
        dropped_rows=sync_diag.get("dropped_rows", 0),
        model_artifact_path=str(m_path),
        pairing_status=f"INFERENCE on {v_path.name} + {c_path.name}",
    )

    # Format JSON
    json_dicts = [ep.to_dict() for ep in episodes]

    if output_json_path:
        save_canonical_json(episodes, output_json_path)
        print(f"Canonical JSON output successfully written to: {output_json_path}")

    return json_dicts
