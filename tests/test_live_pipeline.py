"""Unit & integration tests for Gate 7A Local Live Pipeline Proof of Concept."""

from __future__ import annotations

import time
import numpy as np
import pytest
import pandas as pd
from pathlib import Path

from src.live_pipeline import (
    IMUSample,
    IMUStreamReplayer,
    IncrementalPoseExtractor,
    LivePipelineSession,
    LiveReplayWorker,
    VideoFrame,
    VideoFrameGenerator,
    compare_recorded_and_live_pipelines,
)


VIDEO_PATH = "data/raw/videos/PDFE01_1.mp4"
IMU_PATH = "data/raw/imu/SUB01_1.txt"


def test_video_frame_generator_properties():
    """Verify VideoFrameGenerator opens video and streams valid frames with timestamps."""
    vf_gen = VideoFrameGenerator(VIDEO_PATH)
    assert vf_gen.fps > 0
    assert vf_gen.total_frames > 0

    frames = []
    for idx, frame in enumerate(vf_gen.stream_frames()):
        frames.append(frame)
        if idx >= 5:
            break

    assert len(frames) == 6
    assert isinstance(frames[0], VideoFrame)
    assert frames[0].frame_index == 0
    assert frames[0].timestamp >= 0.0
    assert frames[0].rgb_frame.ndim == 3


def test_imu_stream_replayer_properties():
    """Verify IMUStreamReplayer loads sensor file and streams samples with timestamps."""
    imu_rep = IMUStreamReplayer(IMU_PATH)
    assert imu_rep.sampling_rate > 0
    assert imu_rep.total_samples > 0

    samples = []
    for idx, sample in enumerate(imu_rep.stream_samples()):
        samples.append(sample)
        if idx >= 10:
            break

    assert len(samples) == 11
    assert isinstance(samples[0], IMUSample)
    assert samples[0].timestamp >= 0.0
    assert isinstance(samples[0].accel_y, float)


def test_incremental_feature_generation_before_stop():
    """Verify kinematic features are generated incrementally during frame stream, not in batch at stop."""
    extractor = IncrementalPoseExtractor(fps=29.98)
    vf_gen = VideoFrameGenerator(VIDEO_PATH)

    # Stream first 15 frames
    for idx, frame in enumerate(vf_gen.stream_frames()):
        extractor.process_frame(frame)
        if idx >= 14:
            break

    # Feature records must already exist before calling any stop or batch extraction
    assert len(extractor.feature_records) > 0
    assert "left_ankle_velocity" in extractor.feature_records[0]
    assert "stride_width" in extractor.feature_records[0]

    df = extractor.get_feature_dataframe()
    assert len(df) == len(extractor.feature_records)
    assert list(df.columns) == [
        "timestamp", "left_ankle_velocity", "right_ankle_velocity",
        "left_knee_angle", "right_knee_angle", "stride_width"
    ]
    extractor.close()
    vf_gen.close()


def test_live_replay_worker_lifecycle_and_single_instance():
    """Verify LiveReplayWorker start, stop, double-start rejection, and resource cleanup."""
    worker = LiveReplayWorker(video_path=VIDEO_PATH, imu_path=IMU_PATH)
    assert not worker.is_running()

    worker.start()
    assert worker.is_running()

    # Verify duplicate start is rejected with RuntimeError
    with pytest.raises(RuntimeError, match="already running"):
        worker.start()

    # Let it run to accumulate > 10 fused windows (> 2.0s of real video)
    time.sleep(2.5)
    assert worker.session.frames_processed > 0

    # Stop worker cleanly
    res = worker.stop(timeout=10.0)
    assert not worker.is_running()
    assert res is not None
    assert res["state"] == "COMPLETE"
    assert res["status"] == "SUCCESS"
    assert "episodes" in res


def test_live_pipeline_session_lifecycle():
    """Verify live state transitions and end-to-end processing with synthetic_demo mode."""
    session = LivePipelineSession()
    assert session.state == "CONNECTING"
    assert session.data_mode == "synthetic_demo"

    session.start_monitoring()
    assert session.state == "MONITORING"

    vf_gen = VideoFrameGenerator(VIDEO_PATH)
    imu_rep = IMUStreamReplayer(IMU_PATH)

    # Process first 100 frames and 500 IMU samples
    for idx, frame in enumerate(vf_gen.stream_frames()):
        session.process_camera_frame(frame)
        if idx >= 100:
            break

    for idx, sample in enumerate(imu_rep.stream_samples()):
        session.process_imu_sample(sample)
        if idx >= 500:
            break

    res = session.stop_monitoring(video_fps=vf_gen.fps)
    assert res["status"] == "SUCCESS"
    assert res["state"] == "COMPLETE"
    assert res["data_mode"] == "synthetic_demo"
    assert "episodes" in res
    assert "explanation" in res
    assert res["diagnostics"]["frames_processed"] == 101
    assert res["diagnostics"]["imu_samples_received"] == 501


def test_recorded_and_live_parity_comparison():
    """Verify 100% episode parity between Recorded and Live emulated pipelines."""
    res = compare_recorded_and_live_pipelines(VIDEO_PATH, IMU_PATH)
    assert res["exact_match"] is True
    assert res["recorded_episode_count"] == 12
    assert res["live_episode_count"] == 12
    assert res["matching_episodes"] == 12
