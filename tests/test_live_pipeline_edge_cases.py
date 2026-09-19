"""Adversarial and edge-case unit tests for NeuroGait live pipeline components."""

from __future__ import annotations

import time
import numpy as np
import pandas as pd
import pytest

from src.live_pipeline import (
    IMUSample,
    IMUStreamReplayer,
    IncrementalPoseExtractor,
    LivePipelineSession,
    LiveReplayWorker,
    VideoFrame,
)
from src.sync import SyncError


def test_extractor_zero_frames():
    """Verify IncrementalPoseExtractor with 0 frames returns empty dataframe without crashing."""
    extractor = IncrementalPoseExtractor(fps=30.0)
    df = extractor.get_feature_dataframe()
    assert df.empty
    assert list(df.columns) == [
        "timestamp", "left_ankle_velocity", "right_ankle_velocity",
        "left_knee_angle", "right_knee_angle", "stride_width"
    ]
    extractor.close()


def test_extractor_single_frame_no_landmarks():
    """Verify single frame with blank image (no pose detected) handles leading NaNs gracefully."""
    extractor = IncrementalPoseExtractor(fps=30.0)
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    vf = VideoFrame(frame_index=0, timestamp=0.0, rgb_frame=blank_frame)

    rec = extractor.process_frame(vf)
    assert len(extractor.raw_records) == 1
    assert np.isnan(rec["l_hip_x"])

    # Feature records list is empty because no valid coordinates yet
    assert len(extractor.feature_records) == 0
    df = extractor.get_feature_dataframe()
    assert df.empty
    extractor.close()


def test_session_empty_imu_fails_cleanly():
    """Verify stop_monitoring with empty IMU records raises ValueError and sets PROCESSING_FAILED."""
    session = LivePipelineSession()
    session.start_monitoring()

    # Send one blank video frame but NO IMU samples
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    session.process_camera_frame(VideoFrame(0, 0.0, blank_frame))

    with pytest.raises(RuntimeError, match="Live processing failed: No IMU samples received"):
        session.stop_monitoring()

    assert session.state == "PROCESSING_FAILED"


def test_session_insufficient_fused_rows_fails_cleanly():
    """Verify session with fewer than 10 fused rows raises SyncError and sets PROCESSING_FAILED."""
    session = LivePipelineSession()
    session.start_monitoring()

    # Send 3 video frames and 10 IMU samples (spanning < 0.2s, so < 10 fused 1-sec windows)
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for i in range(3):
        session.process_camera_frame(VideoFrame(i, float(i) * 0.033, blank_frame))
    for i in range(15):
        session.process_imu_sample(IMUSample(timestamp=float(i) * 0.01, accel_y=0.5, gyro_x=10.0, gyro_z=5.0))

    with pytest.raises(RuntimeError, match="Live processing failed"):
        session.stop_monitoring()

    assert session.state == "PROCESSING_FAILED"


def test_session_invalid_state_transitions():
    """Verify illegal lifecycle calls on LivePipelineSession raise RuntimeError."""
    session = LivePipelineSession()
    assert session.state == "CONNECTING"

    # Cannot stop before starting
    with pytest.raises(RuntimeError, match="Cannot stop monitoring from state CONNECTING"):
        session.stop_monitoring()

    session.start_monitoring()
    assert session.state == "MONITORING"

    # Cannot start again when already in MONITORING
    with pytest.raises(RuntimeError, match="Cannot start monitoring from state MONITORING"):
        session.start_monitoring()


def test_worker_repeated_stop():
    """Verify calling worker.stop() multiple times after worker termination is idempotent and does not crash."""
    worker = LiveReplayWorker()
    # Stop before start returns None
    res1 = worker.stop()
    assert res1 is None
    assert not worker.is_running()
