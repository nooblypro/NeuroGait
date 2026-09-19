"""Unit tests for canonical JSON schema validation and formatting."""

import json
from pathlib import Path
import pytest

from src.contract import (
    format_episodes_json,
    load_and_validate_canonical_json,
    save_canonical_json,
    validate_episode_dict,
)
from src.episodes import Episode


def test_valid_canonical_episode_dict():
    """Verify valid episode satisfies schema."""
    valid_ep = {
        "start": 5.2,
        "end": 6.8,
        "confidence": 0.92,
        "type": "FoG",
        "primary_cue": "left_ankle_velocity",
        "data_mode": "real",
    }
    validate_episode_dict(valid_ep)


def test_invalid_primary_cue_rejected():
    """Non-canonical primary cue raises ValueError."""
    bad_ep = {
        "start": 5.2,
        "end": 6.8,
        "confidence": 0.92,
        "type": "FoG",
        "primary_cue": "invented_feature",
        "data_mode": "real",
    }
    with pytest.raises(ValueError, match="Invalid 'primary_cue'"):
        validate_episode_dict(bad_ep)


def test_invalid_confidence_range_rejected():
    """Confidence outside [0, 1] raises ValueError."""
    bad_ep = {
        "start": 1.0,
        "end": 2.0,
        "confidence": 1.5,
        "type": "FoG",
        "primary_cue": "stride_width",
        "data_mode": "real",
    }
    with pytest.raises(ValueError, match="Invalid 'confidence'"):
        validate_episode_dict(bad_ep)


def test_canonical_json_roundtrip(tmp_path):
    """Save and load canonical JSON file and assert strict validity."""
    episodes = [
        Episode(
            start=2.0,
            end=4.5,
            confidence=0.88,
            type="FoG",
            primary_cue="accel_rms",
            data_mode="real",
        ),
        Episode(
            start=4.8,
            end=7.0,
            confidence=0.25,
            type="Normal",
            primary_cue="right_knee_angle",
            data_mode="real",
        ),
    ]

    out_file = tmp_path / "test_contract.json"
    save_canonical_json(episodes, out_file)
    assert out_file.exists()

    loaded = load_and_validate_canonical_json(out_file)
    assert len(loaded) == 2
    assert loaded[0]["type"] == "FoG"
    assert loaded[0]["primary_cue"] == "accel_rms"
    assert loaded[1]["type"] == "Normal"
