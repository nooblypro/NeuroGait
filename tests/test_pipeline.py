"""Integration tests for the complete NeuroGait training and inference pipeline."""

from pathlib import Path
import pytest

from src.contract import load_and_validate_canonical_json
from src.pipeline import predict_fog, train_model


def test_pipeline_real_integration(tmp_path):
    """End-to-end integration test:
    KNOWN-GOOD INPUT -> TRAINING -> models/fog_model.pkl -> INFERENCE -> JSON
    """
    dataset_dir = Path("data")
    model_output = tmp_path / "fog_model.pkl"
    json_output = tmp_path / "sample_prediction.json"

    # Train on real dataset with frame limit for fast execution
    train_res = train_model(
        dataset_dir=dataset_dir,
        model_output_path=model_output,
        max_subjects=3,
        max_video_frames=120,  # ~4 seconds per video for fast testing
    )

    assert train_res["status"] == "SUCCESS"
    assert model_output.exists()
    assert train_res["train_accuracy"] > 0.5
    assert train_res["total_windows"] >= 10

    # Run inference on real subject trial
    video_path = Path("data/raw/videos/PDFE01_1.mp4")
    imu_path = Path("data/raw/imu/SUB01_1.txt")

    results = predict_fog(
        video_path=video_path,
        csv_path=imu_path,
        model_path=model_output,
        output_json_path=json_output,
        max_frames=120,
    )

    assert len(results) > 0
    assert json_output.exists()

    # Assert that output strictly validates against canonical JSON contract
    validated = load_and_validate_canonical_json(json_output)
    assert len(validated) == len(results)
    for ep in validated:
        assert "start" in ep
        assert "end" in ep
        assert "confidence" in ep
        assert "type" in ep
        assert "primary_cue" in ep
        assert ep["data_mode"] == "real"
