"""Pose estimation and kinematic feature extraction using MediaPipe.

Extracts normalized lower-body landmarks and computes the 5 canonical video features:
1. left_ankle_velocity
2. right_ankle_velocity
3. left_knee_angle
4. right_knee_angle
5. stride_width

Raw landmarks are intermediate data only and never exposed to model input.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision
import numpy as np
import pandas as pd

# MediaPipe landmark indices
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_full.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"


def ensure_model_asset(model_path: Path | str = DEFAULT_MODEL_PATH) -> str:
    """Ensure that the MediaPipe pose landmarker task model exists locally."""
    path = Path(model_path)
    if not path.exists() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        import urllib.request
        print(f"Downloading MediaPipe model asset to {path}...")
        urllib.request.urlretrieve(MODEL_URL, str(path))
    return str(path)


def calculate_knee_angle(
    hip: Tuple[float, float],
    knee: Tuple[float, float],
    ankle: Tuple[float, float]
) -> float:
    """Calculate the interior knee joint angle in degrees formed by hip-knee-ankle.

    Formula:
        v1 = hip - knee
        v2 = ankle - knee
        cos(theta) = (v1 . v2) / (||v1|| * ||v2||)
        theta = arccos(clip(cos(theta), -1.0, 1.0)) * 180 / pi
    """
    v1 = np.array([hip[0] - knee[0], hip[1] - knee[1]], dtype=np.float64)
    v2 = np.array([ankle[0] - knee[0], ankle[1] - knee[1]], dtype=np.float64)

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 < 1e-7 or norm2 < 1e-7:
        return np.nan

    cos_theta = np.dot(v1, v2) / (norm1 * norm2)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    angle_rad = np.arccos(cos_theta)
    return float(np.degrees(angle_rad))


def calculate_stride_width(
    left_ankle: Tuple[float, float],
    right_ankle: Tuple[float, float]
) -> float:
    """Calculate stride width as the normalized 2D Euclidean distance between ankles.

    Formula:
        stride_width = sqrt((x_left - x_right)^2 + (y_left - y_right)^2)
    """
    dx = left_ankle[0] - right_ankle[0]
    dy = left_ankle[1] - right_ankle[1]
    return float(np.sqrt(dx * dx + dy * dy))


def calculate_velocity(
    pos_curr: Tuple[float, float],
    pos_prev: Tuple[float, float],
    dt: float
) -> float:
    """Calculate landmark 2D velocity in normalized units per second.

    Formula:
        velocity = sqrt((x_t - x_{t-1})^2 + (y_t - y_{t-1})^2) / dt
    """
    if dt <= 0 or np.isnan(dt):
        return np.nan
    dx = pos_curr[0] - pos_prev[0]
    dy = pos_curr[1] - pos_prev[1]
    dist = np.sqrt(dx * dx + dy * dy)
    return float(dist / dt)


class PoseFeatureExtractor:
    """Extracts pose landmarks and calculates kinematic features from video."""

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        min_detection_confidence: float = 0.3,
        min_presence_confidence: float = 0.3,
    ):
        actual_model_path = ensure_model_asset(model_path or DEFAULT_MODEL_PATH)
        base_opts = BaseOptions(model_asset_path=actual_model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_opts,
            running_mode=vision.RunningMode.IMAGE,
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=min_presence_confidence,
            num_poses=1,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    def close(self):
        if self.landmarker:
            self.landmarker.close()
            self.landmarker = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def process_video(
        self,
        video_path: str | Path,
        max_frames: Optional[int] = None
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """Process video and return canonical kinematic features and video metadata.

        Returns:
            df: DataFrame containing:
                ['timestamp', 'left_ankle_velocity', 'right_ankle_velocity',
                 'left_knee_angle', 'right_knee_angle', 'stride_width']
            metadata: Dict with 'video_fps', 'duration', 'total_frames', 'valid_pose_frames'
        """
        video_path_str = str(video_path)
        if not os.path.exists(video_path_str):
            raise FileNotFoundError(f"Video file not found: {video_path_str}")

        cap = cv2.VideoCapture(video_path_str)
        if not cap.isOpened():
            raise ValueError(f"Unable to open video file: {video_path_str}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or np.isnan(fps):
            # Fallback determination from timestamps if possible
            fps = 29.97

        duration = total_frames / fps if fps > 0 else 0.0

        records: List[Dict[str, float]] = []
        frame_idx = 0
        valid_poses = 0

        prev_left_ankle: Optional[Tuple[float, float]] = None
        prev_right_ankle: Optional[Tuple[float, float]] = None
        prev_time: Optional[float] = None

        try:
            while True:
                if max_frames is not None and frame_idx >= max_frames:
                    break
                ret, frame = cap.read()
                if not ret:
                    break

                # Calculate actual timestamp
                ts_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                if ts_msec > 0:
                    timestamp = ts_msec / 1000.0
                else:
                    timestamp = frame_idx / fps

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                result = self.landmarker.detect(mp_image)

                l_hip, r_hip = None, None
                l_knee, r_knee = None, None
                l_ankle, r_ankle = None, None
                l_shoulder, r_shoulder = None, None
                neck = None

                if result.pose_landmarks and len(result.pose_landmarks) > 0:
                    lms = result.pose_landmarks[0]
                    l_hip = (lms[LEFT_HIP].x, lms[LEFT_HIP].y)
                    r_hip = (lms[RIGHT_HIP].x, lms[RIGHT_HIP].y)
                    l_knee = (lms[LEFT_KNEE].x, lms[LEFT_KNEE].y)
                    r_knee = (lms[RIGHT_KNEE].x, lms[RIGHT_KNEE].y)
                    l_ankle = (lms[LEFT_ANKLE].x, lms[LEFT_ANKLE].y)
                    r_ankle = (lms[RIGHT_ANKLE].x, lms[RIGHT_ANKLE].y)
                    l_shoulder = (lms[LEFT_SHOULDER].x, lms[LEFT_SHOULDER].y)
                    r_shoulder = (lms[RIGHT_SHOULDER].x, lms[RIGHT_SHOULDER].y)
                    neck = ((l_shoulder[0] + r_shoulder[0]) / 2.0, (l_shoulder[1] + r_shoulder[1]) / 2.0)
                    valid_poses += 1

                records.append({
                    "timestamp": timestamp,
                    "l_hip_x": l_hip[0] if l_hip else np.nan,
                    "l_hip_y": l_hip[1] if l_hip else np.nan,
                    "r_hip_x": r_hip[0] if r_hip else np.nan,
                    "r_hip_y": r_hip[1] if r_hip else np.nan,
                    "l_knee_x": l_knee[0] if l_knee else np.nan,
                    "l_knee_y": l_knee[1] if l_knee else np.nan,
                    "r_knee_x": r_knee[0] if r_knee else np.nan,
                    "r_knee_y": r_knee[1] if r_knee else np.nan,
                    "l_ankle_x": l_ankle[0] if l_ankle else np.nan,
                    "l_ankle_y": l_ankle[1] if l_ankle else np.nan,
                    "r_ankle_x": r_ankle[0] if r_ankle else np.nan,
                    "r_ankle_y": r_ankle[1] if r_ankle else np.nan,
                    "neck_x": neck[0] if neck else np.nan,
                    "neck_y": neck[1] if neck else np.nan,
                })
                frame_idx += 1
        finally:
            cap.release()

        raw_df = pd.DataFrame(records)
        metadata = {
            "video_fps": float(fps),
            "duration": float(duration),
            "total_frames": int(frame_idx),
            "valid_pose_frames": int(valid_poses),
        }

        if raw_df.empty:
            empty_df = pd.DataFrame(columns=[
                "timestamp", "left_ankle_velocity", "right_ankle_velocity",
                "left_knee_angle", "right_knee_angle", "stride_width"
            ])
            return empty_df, metadata

        # Section 5 rule:
        # "missing values may initially be NaN;
        #  later pose failures use forward-fill;
        #  remaining NaNs are dropped."
        coord_cols = [c for c in raw_df.columns if c != "timestamp"]
        raw_df[coord_cols] = raw_df[coord_cols].ffill()
        # Any leading NaNs before first detection forward/backward fill or drop
        raw_df[coord_cols] = raw_df[coord_cols].bfill()

        # Compute kinematic features from imputed coordinates
        feature_rows: List[Dict[str, float]] = []
        for i in range(len(raw_df)):
            row = raw_df.iloc[i]
            ts = float(row["timestamp"])

            # Landmark coordinates
            lh = (row["l_hip_x"], row["l_hip_y"])
            rh = (row["r_hip_x"], row["r_hip_y"])
            lk = (row["l_knee_x"], row["l_knee_y"])
            rk = (row["r_knee_x"], row["r_knee_y"])
            la = (row["l_ankle_x"], row["l_ankle_y"])
            ra = (row["r_ankle_x"], row["r_ankle_y"])

            # Knee angles
            l_knee_ang = calculate_knee_angle(lh, lk, la)
            r_knee_ang = calculate_knee_angle(rh, rk, ra)

            # Stride width
            sw = calculate_stride_width(la, ra)

            # Velocities
            if i == 0:
                l_vel = 0.0
                r_vel = 0.0
            else:
                prev_row = raw_df.iloc[i - 1]
                dt = ts - float(prev_row["timestamp"])
                if dt <= 0:
                    dt = 1.0 / fps
                prev_la = (prev_row["l_ankle_x"], prev_row["l_ankle_y"])
                prev_ra = (prev_row["r_ankle_x"], prev_row["r_ankle_y"])
                l_vel = calculate_velocity(la, prev_la, dt)
                r_vel = calculate_velocity(ra, prev_ra, dt)

            feature_rows.append({
                "timestamp": ts,
                "left_ankle_velocity": l_vel,
                "right_ankle_velocity": r_vel,
                "left_knee_angle": l_knee_ang,
                "right_knee_angle": r_knee_ang,
                "stride_width": sw,
            })

        feat_df = pd.DataFrame(feature_rows)
        # Drop any remaining uncomputable rows
        feat_df = feat_df.dropna().reset_index(drop=True)
        return feat_df, metadata
