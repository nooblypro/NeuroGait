"""Local Live Pipeline Proof of Concept & Emulation for NeuroGait (Gate 7A).

Provides:
- VideoFrameGenerator: Incremental frame reader from video preserving timestamps & FPS.
- IMUStreamReplayer: Incremental IMU sample replayer preserving timestamps & actual rate.
- LivePipelineSession: Manages live state, incremental pose & IMU windowing, sync, inference, and canonical result output.
- compare_recorded_and_live_pipelines: Canonical parity comparison between Recorded and Live pipelines.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import cv2
import numpy as np
import pandas as pd
import mediapipe as mp

from src.contract import format_episodes_json
from src.episodes import Episode, aggregate_episodes, classify_window_type, determine_primary_cue
from src.explanation.orchestrator import generate_explanation
from src.features import CANONICAL_FEATURES, extract_feature_matrix
from src.imu import compute_accel_rms, compute_gyro_x_var, compute_gyro_z_var, extract_imu_rolling_features, load_raw_imu
from src.model import load_model, predict_fog_probability
from src.pose import (
    LEFT_ANKLE, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER,
    RIGHT_ANKLE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER,
    calculate_knee_angle, calculate_stride_width, calculate_velocity, ensure_model_asset
)
from src.sync import synchronize_modalities


@dataclass
class VideoFrame:
    frame_index: int
    timestamp: float
    rgb_frame: np.ndarray


class VideoFrameGenerator:
    """Incremental frame generator preserving actual video timestamps and FPS."""

    def __init__(self, video_path: Union[str, Path]):
        self.video_path = str(video_path)
        if not Path(self.video_path).exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Unable to open video file: {self.video_path}")

        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if self.fps <= 0 or np.isnan(self.fps):
            self.fps = 29.97

        self.duration = self.total_frames / self.fps if self.fps > 0 else 0.0
        self.frames_read = 0

    def stream_frames(self) -> Generator[VideoFrame, None, None]:
        """Expose video frames incrementally."""
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    break

                ts_msec = self.cap.get(cv2.CAP_PROP_POS_MSEC)
                if ts_msec > 0:
                    timestamp = ts_msec / 1000.0
                else:
                    timestamp = self.frames_read / self.fps

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                vf = VideoFrame(
                    frame_index=self.frames_read,
                    timestamp=float(timestamp),
                    rgb_frame=rgb,
                )
                self.frames_read += 1
                yield vf
        finally:
            self.close()

    def close(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()


@dataclass
class IMUSample:
    timestamp: float
    accel_y: float
    gyro_x: float
    gyro_z: float


class IMUStreamReplayer:
    """Incremental IMU sample replayer preserving timestamps and actual sampling rate."""

    def __init__(self, imu_path: Union[str, Path]):
        self.imu_path = str(imu_path)
        self.df, self.sampling_rate = load_raw_imu(self.imu_path)
        self.total_samples = len(self.df)
        self.samples_emitted = 0

    def stream_samples(self) -> Generator[IMUSample, None, None]:
        """Emit IMU samples incrementally."""
        for _, row in self.df.iterrows():
            sample = IMUSample(
                timestamp=float(row["timestamp"]),
                accel_y=float(row["accel_y"]),
                gyro_x=float(row["gyro_x"]),
                gyro_z=float(row["gyro_z"]),
            )
            self.samples_emitted += 1
            yield sample


class IncrementalPoseExtractor:
    """Processes video frames incrementally using MediaPipe Pose Landmarker with online stateful feature extraction."""

    def __init__(self, fps: float = 29.98):
        model_path = ensure_model_asset()
        base_opts = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_opts,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            min_pose_detection_confidence=0.3,
            min_pose_presence_confidence=0.3,
            num_poses=1,
        )
        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self.fps = fps
        self.raw_records: List[Dict[str, float]] = []
        self.feature_records: List[Dict[str, float]] = []
        self.valid_pose_count = 0
        self.last_valid_coords: Optional[Dict[str, float]] = None

    def process_frame(self, frame: VideoFrame) -> Dict[str, float]:
        """Process a single incoming frame, update landmark states, and compute kinematic features incrementally."""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame.rgb_frame)
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
            self.valid_pose_count += 1

        rec = {
            "timestamp": frame.timestamp,
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
        }
        self.raw_records.append(rec)

        # Forward fill from last valid coordinates if current is missing
        coord_keys = [k for k in rec if k != "timestamp"]
        imputed_coords = {}
        if l_hip is not None:
            imputed_coords = {k: rec[k] for k in coord_keys}
            self.last_valid_coords = imputed_coords.copy()
        elif self.last_valid_coords is not None:
            imputed_coords = self.last_valid_coords.copy()
        else:
            # Leading NaNs before first detection
            imputed_coords = {k: np.nan for k in coord_keys}

        # Calculate incremental features if coordinates are available
        if not np.isnan(imputed_coords.get("l_hip_x", np.nan)):
            lh = (imputed_coords["l_hip_x"], imputed_coords["l_hip_y"])
            rh = (imputed_coords["r_hip_x"], imputed_coords["r_hip_y"])
            lk = (imputed_coords["l_knee_x"], imputed_coords["l_knee_y"])
            rk = (imputed_coords["r_knee_x"], imputed_coords["r_knee_y"])
            la = (imputed_coords["l_ankle_x"], imputed_coords["l_ankle_y"])
            ra = (imputed_coords["r_ankle_x"], imputed_coords["r_ankle_y"])

            l_knee_ang = calculate_knee_angle(lh, lk, la)
            r_knee_ang = calculate_knee_angle(rh, rk, ra)
            sw = calculate_stride_width(la, ra)

            if len(self.feature_records) == 0:
                l_vel = 0.0
                r_vel = 0.0
            else:
                prev_feat = self.feature_records[-1]
                prev_ts = prev_feat["timestamp"]
                dt = frame.timestamp - prev_ts
                if dt <= 0:
                    dt = 1.0 / self.fps
                prev_la = (prev_feat["_la_x"], prev_feat["_la_y"])
                prev_ra = (prev_feat["_ra_x"], prev_feat["_ra_y"])
                l_vel = calculate_velocity(la, prev_la, dt)
                r_vel = calculate_velocity(ra, prev_ra, dt)

            feat_entry = {
                "timestamp": frame.timestamp,
                "left_ankle_velocity": l_vel,
                "right_ankle_velocity": r_vel,
                "left_knee_angle": l_knee_ang,
                "right_knee_angle": r_knee_ang,
                "stride_width": sw,
                "_la_x": la[0],
                "_la_y": la[1],
                "_ra_x": ra[0],
                "_ra_y": ra[1],
            }
            self.feature_records.append(feat_entry)

        return rec

    def get_feature_dataframe(self, fps: Optional[float] = None) -> pd.DataFrame:
        """Return computed kinematic pose features."""
        if not self.feature_records:
            # If no features or leading NaNs, use full imputation fallback matching recorded mode
            if not self.raw_records:
                return pd.DataFrame(columns=[
                    "timestamp", "left_ankle_velocity", "right_ankle_velocity",
                    "left_knee_angle", "right_knee_angle", "stride_width"
                ])
            raw_df = pd.DataFrame(self.raw_records)
            coord_cols = [c for c in raw_df.columns if c != "timestamp"]
            raw_df[coord_cols] = raw_df[coord_cols].ffill()
            raw_df[coord_cols] = raw_df[coord_cols].bfill()
            actual_fps = fps or self.fps

            feature_rows: List[Dict[str, float]] = []
            for i in range(len(raw_df)):
                row = raw_df.iloc[i]
                ts = float(row["timestamp"])
                lh = (row["l_hip_x"], row["l_hip_y"])
                rh = (row["r_hip_x"], row["r_hip_y"])
                lk = (row["l_knee_x"], row["l_knee_y"])
                rk = (row["r_knee_x"], row["r_knee_y"])
                la = (row["l_ankle_x"], row["l_ankle_y"])
                ra = (row["r_ankle_x"], row["r_ankle_y"])

                l_knee_ang = calculate_knee_angle(lh, lk, la)
                r_knee_ang = calculate_knee_angle(rh, rk, ra)
                sw = calculate_stride_width(la, ra)

                if i == 0:
                    l_vel = 0.0
                    r_vel = 0.0
                else:
                    prev_row = raw_df.iloc[i - 1]
                    dt = ts - float(prev_row["timestamp"])
                    if dt <= 0:
                        dt = 1.0 / actual_fps
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
            return pd.DataFrame(feature_rows).dropna().reset_index(drop=True)

        cols = [
            "timestamp", "left_ankle_velocity", "right_ankle_velocity",
            "left_knee_angle", "right_knee_angle", "stride_width"
        ]
        feat_df = pd.DataFrame(self.feature_records)[cols].dropna().reset_index(drop=True)
        return feat_df

    def close(self):
        if self.landmarker:
            self.landmarker.close()
            self.landmarker = None


class LivePipelineSession:
    """Manages the lifecycle of a Live Monitoring session (Gate 7A)."""

    def __init__(self, model_path: Union[str, Path] = "models/fog_model.pkl"):
        self.model_path = Path(model_path)
        self.model, self.scaler = load_model(self.model_path)

        self.state = "CONNECTING"
        self.data_mode = "synthetic_demo"

        self.pose_extractor: Optional[IncrementalPoseExtractor] = None
        self.imu_records: List[Dict[str, float]] = []

        self.frames_processed = 0
        self.imu_samples_received = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.inference_latencies: List[float] = []
        self._is_active = False

    def start_monitoring(self, video_fps: float = 29.98):
        """Transition from CONNECTING -> CONNECTED -> MONITORING."""
        if self.state not in ("CONNECTING", "CONNECTED"):
            raise RuntimeError(f"Cannot start monitoring from state {self.state}")

        self.pose_extractor = IncrementalPoseExtractor(fps=video_fps)
        self.imu_records.clear()
        self.frames_processed = 0
        self.imu_samples_received = 0
        self.inference_latencies.clear()
        self.start_time = time.time()
        self._is_active = True
        self.state = "MONITORING"

    def process_camera_frame(self, frame: VideoFrame):
        if self.state != "MONITORING" or self.pose_extractor is None or not self._is_active:
            return
        self.pose_extractor.process_frame(frame)
        self.frames_processed += 1

    def process_imu_sample(self, sample: IMUSample):
        if self.state != "MONITORING" or not self._is_active:
            return
        self.imu_records.append({
            "timestamp": sample.timestamp,
            "accel_y": sample.accel_y,
            "gyro_x": sample.gyro_x,
            "gyro_z": sample.gyro_z,
        })
        self.imu_samples_received += 1

    def stop_monitoring(self, video_fps: Optional[float] = None) -> Dict[str, Any]:
        """Transition from MONITORING -> STOPPING -> COMPLETE and generate canonical output."""
        if self.state != "MONITORING":
            raise RuntimeError(f"Cannot stop monitoring from state {self.state}")

        self.state = "STOPPING"
        self._is_active = False
        self.end_time = time.time()

        if self.pose_extractor is None:
            self.state = "PROCESSING_FAILED"
            raise RuntimeError("Pose extractor was not initialized.")

        try:
            t0 = time.time()
            # 1. Retrieve incrementally computed pose features
            pose_df = self.pose_extractor.get_feature_dataframe(fps=video_fps)

            # 2. Extract IMU rolling features
            imu_raw_df = pd.DataFrame(self.imu_records)
            if imu_raw_df.empty:
                raise ValueError("No IMU samples received during live session.")

            imu_feat_df = extract_imu_rolling_features(imu_raw_df, window_sec=1.0)

            # 3. Synchronize modalities with +/-0.1s tolerance
            fused_df, sync_diag = synchronize_modalities(pose_df, imu_feat_df, tolerance_sec=0.1)

            # 4. Extract canonical 8-feature matrix
            X = extract_feature_matrix(fused_df)

            # 5. Predict probabilities using existing model and scaler
            probs = predict_fog_probability(self.model, self.scaler, X)

            # 6. Aggregate episodes with canonical thresholds
            timestamps = fused_df["timestamp"].to_numpy()
            episodes = aggregate_episodes(
                timestamps=timestamps,
                probabilities=probs,
                X=X,
                scaler=self.scaler,
                window_duration=1.0,
                max_merge_gap=1.0,
                data_mode=self.data_mode,
            )

            # 7. Generate deterministic explanation
            canonical_episodes = [ep.to_dict() for ep in episodes]
            explanation_res = generate_explanation(
                episodes=canonical_episodes,
                preferred_provider="auto",
            )

            t1 = time.time()
            self.inference_latencies.append(t1 - t0)

            elapsed = (self.end_time - self.start_time) if self.start_time else 0.0
            actual_fps = self.frames_processed / elapsed if elapsed > 0 else 0.0

            result = {
                "status": "SUCCESS",
                "state": "COMPLETE",
                "data_mode": self.data_mode,
                "episodes": canonical_episodes,
                "episode_count": len(canonical_episodes),
                "summary": {
                    "total_duration": float(np.max(timestamps)) if len(timestamps) > 0 else 0.0,
                    "fog_episodes": sum(1 for ep in episodes if ep.type == "FoG"),
                    "borderline_episodes": sum(1 for ep in episodes if ep.type == "Borderline"),
                    "normal_episodes": sum(1 for ep in episodes if ep.type == "Normal"),
                },
                "explanation": explanation_res.to_dict(),
                "diagnostics": {
                    "frames_processed": self.frames_processed,
                    "imu_samples_received": self.imu_samples_received,
                    "fused_rows": len(fused_df),
                    "dropped_rows": sync_diag.get("dropped_rows", 0),
                    "valid_pose_frames": self.pose_extractor.valid_pose_count,
                    "observed_fps": round(actual_fps, 2),
                    "processing_latency_sec": round(float(np.mean(self.inference_latencies)), 4) if self.inference_latencies else 0.0,
                },
            }
            self.state = "COMPLETE"
            return result

        except Exception as e:
            self.state = "PROCESSING_FAILED"
            raise RuntimeError(f"Live processing failed: {e}") from e
        finally:
            if self.pose_extractor:
                self.pose_extractor.close()


class LiveReplayWorker:
    """Manages an asynchronous background replay thread for Streamlit Live Demo."""

    def __init__(
        self,
        video_path: Union[str, Path] = "data/raw/videos/PDFE01_1.mp4",
        imu_path: Union[str, Path] = "data/raw/imu/SUB01_1.txt",
        model_path: Union[str, Path] = "models/fog_model.pkl",
    ):
        self.video_path = str(video_path)
        self.imu_path = str(imu_path)
        self.model_path = str(model_path)
        self.session = LivePipelineSession(model_path=self.model_path)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.error: Optional[Exception] = None
        self.result: Optional[Dict[str, Any]] = None
        self.is_completed = False

    def start(self):
        """Start replay worker thread. Raises RuntimeError if already running."""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Replay worker is already running.")

        self._stop_event.clear()
        self.error = None
        self.result = None
        self.is_completed = False

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        vf_gen = None
        try:
            vf_gen = VideoFrameGenerator(self.video_path)
            imu_rep = IMUStreamReplayer(self.imu_path)

            self.session.start_monitoring(video_fps=vf_gen.fps)

            # Replay IMU and Video streams
            imu_iter = imu_rep.stream_samples()
            for frame in vf_gen.stream_frames():
                if self._stop_event.is_set():
                    break
                self.session.process_camera_frame(frame)

                # Feed IMU samples up to current video timestamp
                while True:
                    if self._stop_event.is_set():
                        break
                    try:
                        sample = next(imu_iter)
                        self.session.process_imu_sample(sample)
                        if sample.timestamp > frame.timestamp:
                            break
                    except StopIteration:
                        break

            # If stopped prematurely or EOF reached, finalize output
            self.result = self.session.stop_monitoring(video_fps=vf_gen.fps)
            self.is_completed = True

        except Exception as e:
            self.error = e
            self.session.state = "PROCESSING_FAILED"
        finally:
            if vf_gen:
                vf_gen.close()

    def stop(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Signal stop event and wait for worker thread termination."""
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        return self.result

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


def compare_recorded_and_live_pipelines(
    video_path: Union[str, Path],
    imu_path: Union[str, Path],
    model_path: Union[str, Path] = "models/fog_model.pkl",
) -> Dict[str, Any]:
    """Execute Recorded and Live emulated pipelines on identical files and compare output."""
    from src.pipeline import predict_fog

    # 1. Run Recorded Mode
    recorded_episodes = predict_fog(
        video_path=video_path,
        csv_path=imu_path,
        model_path=model_path,
        data_mode="real",
    )

    # 2. Run Emulated Live Mode
    vf_gen = VideoFrameGenerator(video_path)
    imu_rep = IMUStreamReplayer(imu_path)

    session = LivePipelineSession(model_path=model_path)
    session.start_monitoring(video_fps=vf_gen.fps)

    # Stream all frames and samples
    for frame in vf_gen.stream_frames():
        session.process_camera_frame(frame)

    for sample in imu_rep.stream_samples():
        session.process_imu_sample(sample)

    live_res = session.stop_monitoring(video_fps=vf_gen.fps)
    live_episodes = live_res["episodes"]

    # 3. Canonical comparison (excluding data_mode label which is 'synthetic_demo' for live)
    def normalize_ep(ep):
        d = ep.copy()
        d.pop("data_mode", None)
        return d

    rec_norm = [normalize_ep(e) for e in recorded_episodes]
    live_norm = [normalize_ep(e) for e in live_episodes]

    exact_match = (rec_norm == live_norm)
    match_count = sum(1 for r, l in zip(rec_norm, live_norm) if r == l)

    return {
        "exact_match": exact_match,
        "recorded_episode_count": len(recorded_episodes),
        "live_episode_count": len(live_episodes),
        "matching_episodes": match_count,
        "recorded_episodes": recorded_episodes,
        "live_episodes": live_episodes,
        "live_diagnostics": live_res["diagnostics"],
    }
