"""Production runtime parity and regression tests.

Definitions:
- "production runtime parity": Bit-exact equivalence between Local Docker/Linux,
  AWS ECS Fargate, backend canonical JSON, and frontend presentation.
- "cross-platform numerical divergence": Documented runtime floating-point and landmark
  differences between macOS Darwin (Apple Silicon GPU delegate / AVFoundation) and Linux
  ARM64 (TFLite CPU XNNPACK / ffmpeg libavcodec).

Verifies:
1. Production canonical reference fixture satisfies canonical JSON schema.
2. Local Docker container output reproduces production canonical reference fixture exactly.
3. AWS ECS output reproduces production canonical reference fixture exactly.
4. Frozen Phase 1 model artifact SHA256 integrity is preserved.
5. Frozen MediaPipe pose model task artifact SHA256 integrity is preserved.
6. Canonical serialization and JSON round-tripping preserve all fields.
7. Local cached development baseline fixture reflects the documented cross-platform divergence.
"""

import hashlib
import json
from pathlib import Path
import pytest

from src.contract import (
    format_episodes_json,
    load_and_validate_canonical_json,
    validate_episode_dict,
)
from src.episodes import Episode

FROZEN_MODEL_HASH = "02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf"
FROZEN_POSE_MODEL_HASH = "4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad"


def test_frozen_model_hash_integrity():
    """Verify that models/fog_model.pkl matches the immutable Phase 1 SHA256 digest."""
    model_path = Path("models/fog_model.pkl")
    assert model_path.exists(), "models/fog_model.pkl not found"
    with open(model_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    assert digest == FROZEN_MODEL_HASH, f"Model hash mismatch: {digest} != {FROZEN_MODEL_HASH}"


def test_frozen_pose_model_hash_integrity():
    """Verify that models/pose_landmarker_full.task matches the canonical MediaPipe task hash."""
    pose_path = Path("models/pose_landmarker_full.task")
    assert pose_path.exists(), "models/pose_landmarker_full.task not found"
    with open(pose_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    assert digest == FROZEN_POSE_MODEL_HASH, f"Pose model hash mismatch: {digest} != {FROZEN_POSE_MODEL_HASH}"


def test_canonical_episode_serialization_parity():
    """Verify that Episode object serialization satisfies canonical schema and preserves fields."""
    ep = Episode(
        start=55.508,
        end=57.608,
        confidence=0.9018,
        type="FoG",
        primary_cue="gyro_z_var",
        data_mode="real",
    )
    d = ep.to_dict()

    assert d["start"] == 55.508
    assert d["end"] == 57.608
    assert d["confidence"] == 0.9018
    assert d["type"] == "FoG"
    assert d["primary_cue"] == "gyro_z_var"
    assert d["data_mode"] == "real"

    # Schema validation
    validate_episode_dict(d)
    json_str = format_episodes_json([ep])
    loaded = json.loads(json_str)
    assert len(loaded) == 1
    assert loaded[0]["type"] == "FoG"
    assert loaded[0]["start"] == 55.508
    assert loaded[0]["end"] == 57.608


def test_json_roundtrip_fidelity():
    """Verify that JSON serialization and deserialization does not mutate episode fields."""
    episodes = [
        {
            "start": 55.508,
            "end": 57.608,
            "confidence": 0.9018,
            "type": "FoG",
            "primary_cue": "gyro_z_var",
            "data_mode": "real",
        },
        {
            "start": 57.608,
            "end": 57.908,
            "confidence": 0.0590,
            "type": "Normal",
            "primary_cue": "accel_rms",
            "data_mode": "real",
        },
        {
            "start": 57.908,
            "end": 58.008,
            "confidence": 0.4904,
            "type": "Borderline",
            "primary_cue": "gyro_x_var",
            "data_mode": "real",
        },
        {
            "start": 58.008,
            "end": 61.208,
            "confidence": 0.8898,
            "type": "FoG",
            "primary_cue": "gyro_z_var",
            "data_mode": "real",
        },
    ]

    serialized = json.dumps(episodes, indent=2)
    deserialized = json.loads(serialized)

    assert len(deserialized) == len(episodes)
    for orig, loaded in zip(episodes, deserialized):
        assert orig["start"] == loaded["start"]
        assert orig["end"] == loaded["end"]
        assert orig["confidence"] == loaded["confidence"]
        assert orig["type"] == loaded["type"]
        assert orig["primary_cue"] == loaded["primary_cue"]
        assert orig["data_mode"] == loaded["data_mode"]


def test_production_reference_fixture_schema():
    """Verify that tests/fixtures/pdfe31_1_production_reference.json strictly conforms to canonical contract."""
    fixture_path = Path("tests/fixtures/pdfe31_1_production_reference.json")
    assert fixture_path.exists(), f"Production reference fixture not found: {fixture_path}"

    episodes = load_and_validate_canonical_json(fixture_path)
    assert len(episodes) == 76, f"Expected 76 canonical production episodes, got {len(episodes)}"

    fog_eps = [e for e in episodes if e["type"] == "FoG"]
    border_eps = [e for e in episodes if e["type"] == "Borderline"]
    norm_eps = [e for e in episodes if e["type"] == "Normal"]

    assert len(fog_eps) == 27, f"Expected 27 FoG episodes, got {len(fog_eps)}"
    assert len(border_eps) == 24, f"Expected 24 Borderline intervals, got {len(border_eps)}"
    assert len(norm_eps) == 25, f"Expected 25 Normal intervals, got {len(norm_eps)}"

    # Check key ground truth overlapping episodes in canonical production output
    pred1 = next((e for e in episodes if abs(e["start"] - 55.508) < 1e-3 and abs(e["end"] - 57.608) < 1e-3), None)
    assert pred1 is not None, "Pred 1 (55.508–57.608s) not found in production reference"
    assert pred1["type"] == "FoG"
    assert abs(pred1["confidence"] - 0.9018) < 1e-3
    assert pred1["primary_cue"] == "gyro_z_var"

    pred2 = next((e for e in episodes if abs(e["start"] - 58.008) < 1e-3 and abs(e["end"] - 61.208) < 1e-3), None)
    assert pred2 is not None, "Pred 2 (58.008–61.208s) not found in production reference"
    assert pred2["type"] == "FoG"
    assert abs(pred2["confidence"] - 0.8898) < 1e-3
    assert pred2["primary_cue"] == "gyro_z_var"


def test_aws_output_matches_production_reference():
    """Verify that live AWS ECS Fargate inference output matches the production reference fixture 100% bit-exact."""
    aws_path = Path("scratch/aws_pdfe31_predictions.json")
    if not aws_path.exists():
        pytest.skip("scratch/aws_pdfe31_predictions.json not present for live AWS comparison")

    ref_path = Path("tests/fixtures/pdfe31_1_production_reference.json")
    with open(aws_path, "r") as f:
        aws_episodes = json.load(f)
    with open(ref_path, "r") as f:
        ref_episodes = json.load(f)

    assert len(aws_episodes) == len(ref_episodes), (
        f"Episode count mismatch between AWS ({len(aws_episodes)}) and reference ({len(ref_episodes)})"
    )

    for i, (aws_ep, ref_ep) in enumerate(zip(aws_episodes, ref_episodes)):
        for key in ["type", "start", "end", "confidence", "primary_cue", "data_mode"]:
            assert aws_ep[key] == ref_ep[key], (
                f"Discrepancy at episode {i}, field '{key}': AWS={aws_ep[key]} vs Reference={ref_ep[key]}"
            )


def test_container_output_matches_production_reference():
    """Verify that local Docker container execution matches the production reference fixture 100% bit-exact."""
    cnt_path = Path("scratch/container_intermediates.json")
    if not cnt_path.exists():
        pytest.skip("scratch/container_intermediates.json not present for container comparison")

    ref_path = Path("tests/fixtures/pdfe31_1_production_reference.json")
    with open(cnt_path, "r") as f:
        cnt_data = json.load(f)
    with open(ref_path, "r") as f:
        ref_episodes = json.load(f)

    cnt_episodes = cnt_data["stage_j_episodes"]
    assert len(cnt_episodes) == len(ref_episodes), (
        f"Episode count mismatch between Container ({len(cnt_episodes)}) and reference ({len(ref_episodes)})"
    )

    for i, (c_ep, ref_ep) in enumerate(zip(cnt_episodes, ref_episodes)):
        for key in ["type", "start", "end", "confidence", "primary_cue", "data_mode"]:
            assert c_ep[key] == ref_ep[key], (
                f"Discrepancy at episode {i}, field '{key}': Container={c_ep[key]} vs Reference={ref_ep[key]}"
            )


def test_cross_platform_numerical_divergence_documented():
    """Verify and document the cross-platform numerical divergence between macOS Darwin and Linux production runtime.

    Local macOS execution produces 75 intervals with FoG onset at 55.408s due to Metal GPU shaders
    and Darwin AVFoundation decoding.
    Production Linux container execution produces 76 intervals with FoG onset at 55.508s due to
    TFLite CPU XNNPACK instructions and Linux ffmpeg libavcodec decoding.

    This test asserts that both fixtures reflect their documented environment contracts.
    """
    local_path = Path("outputs/predictions/PDFE31_1.json")
    prod_path = Path("tests/fixtures/pdfe31_1_production_reference.json")

    if not local_path.exists() or not prod_path.exists():
        pytest.skip("Fixtures missing for cross-platform comparison")

    with open(local_path) as f:
        local_eps = json.load(f)
    with open(prod_path) as f:
        prod_eps = json.load(f)

    # Local macOS baseline contract
    assert len(local_eps) == 75, f"Local macOS expected 75 episodes, got {len(local_eps)}"
    local_fog1 = next(e for e in local_eps if e["type"] == "FoG" and 55.0 <= e["start"] <= 56.0)
    assert abs(local_fog1["start"] - 55.408) < 1e-3

    # Production Linux container contract
    assert len(prod_eps) == 76, f"Production Linux expected 76 episodes, got {len(prod_eps)}"
    prod_fog1 = next(e for e in prod_eps if e["type"] == "FoG" and 55.0 <= e["start"] <= 56.0)
    assert abs(prod_fog1["start"] - 55.508) < 1e-3


    # Documented shift: 55.508 - 55.408 == +0.100s
    onset_diff = round(prod_fog1["start"] - local_fog1["start"], 3)
    assert onset_diff == 0.100, f"Expected +0.100s onset shift between Darwin and Linux, got {onset_diff}"
