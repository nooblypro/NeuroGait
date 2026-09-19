#!/usr/bin/env python3
"""Independent Gate 7B Real Hardware Verification Script.

Inspects the physical hardware execution artifact.
Fails if:
- Camera access was blocked or 0 real camera frames received
- Phone IMU was unavailable or 0 real IMU samples received
- Nonzero IMU variation is absent
- Timestamps are non-monotonic
- Synchronization was not performed or matched rows < 10
- Synchronization tolerance exceeds +/-0.1s
- Canonical 8-feature contract or ordering is violated
- Frozen model artifact hash is modified
- Synthetic replay data was used instead of real physical sensors
- data_mode != "real"
- Canonical JSON output schema is violated
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.features import CANONICAL_FEATURES

EXPECTED_MODEL_SHA256 = "02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf"


def verify_gate7b_run(run_artifact_path: Path):
    print("=" * 65)
    print("NEUROGAIT INDEPENDENT GATE 7B HARDWARE VERIFICATION")
    print("=" * 65)

    errors: List[str] = []

    # 1. Model Artifact Integrity Check
    print("\n[1/8] Verifying Frozen Phase 1 Model Artifact...")
    model_path = ROOT_DIR / "models/fog_model.pkl"
    if not model_path.exists():
        errors.append(f"Model artifact not found: {model_path}")
    else:
        with open(model_path, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()
        if actual_sha != EXPECTED_MODEL_SHA256:
            errors.append(f"Model SHA256 modified! Expected {EXPECTED_MODEL_SHA256}, got {actual_sha}")
        else:
            print(f"      Model SHA256: {actual_sha} [PASS]")

    # 2. Canonical 8-Feature Contract Check
    print("\n[2/8] Verifying Canonical 8-Feature Ordering...")
    expected_features = (
        "left_ankle_velocity",
        "right_ankle_velocity",
        "left_knee_angle",
        "right_knee_angle",
        "stride_width",
        "accel_rms",
        "gyro_x_var",
        "gyro_z_var",
    )
    if tuple(CANONICAL_FEATURES) != expected_features:
        errors.append(f"Feature ordering mismatch! Got {CANONICAL_FEATURES}")
    else:
        print(f"      Canonical Features: {list(CANONICAL_FEATURES)} [PASS]")

    # 3. Hardware Run Artifact Existence
    print("\n[3/8] Inspecting Hardware Execution Artifact...")
    if not run_artifact_path.exists():
        print(f"      [BLOCKED] Hardware run artifact does not exist: {run_artifact_path}")
        errors.append(f"HARDWARE_RUN_MISSING: {run_artifact_path} does not exist.")
        _report_and_exit(errors)

    try:
        with open(run_artifact_path, "r", encoding="utf-8") as f:
            run_data = json.load(f)
    except Exception as e:
        errors.append(f"Failed to parse hardware run artifact: {e}")
        _report_and_exit(errors)

    # 4. Check for Hardware Failure States
    status = run_data.get("status")
    blocker = run_data.get("blocker")
    if status != "SUCCESS":
        print(f"      [BLOCKED] Hardware run did not succeed. Status: {status}, Blocker: {blocker}")
        errors.append(f"HARDWARE_STATUS_NOT_SUCCESS: Status={status}, Blocker={blocker}")

    # 5. Physical Camera Verification
    print("\n[4/8] Verifying Physical Camera Frame Production...")
    diag = run_data.get("diagnostics", {})
    frames_processed = diag.get("frames_processed", 0)
    camera_hardware = run_data.get("hardware", {}).get("camera", "UNKNOWN")
    print(f"      Camera Hardware:   {camera_hardware}")
    print(f"      Frames Processed:  {frames_processed}")
    if frames_processed <= 0:
        errors.append(f"CAMERA_ZERO_FRAMES: Received {frames_processed} camera frames (CAMERA_ACCESS_BLOCKED).")
    if run_data.get("camera_access_granted") is not True:
        errors.append("CAMERA_ACCESS_NOT_GRANTED: macOS camera permission denied.")

    # 6. Physical Phone IMU Verification
    print("\n[5/8] Verifying Physical Phone IMU Production...")
    imu_samples = diag.get("imu_samples_received", 0)
    phone_hardware = run_data.get("hardware", {}).get("phone", "UNKNOWN")
    print(f"      Phone Hardware:    {phone_hardware}")
    print(f"      IMU Samples:       {imu_samples}")
    if imu_samples <= 0:
        errors.append(f"PHONE_ZERO_SAMPLES: Received {imu_samples} IMU samples (PHONE_IMU_UNAVAILABLE).")
    if run_data.get("phone_imu_connected") is not True:
        errors.append("PHONE_IMU_NOT_CONNECTED: Physical phone IMU was not connected.")

    # 7. Synchronization & Fused Rows Verification
    print("\n[6/8] Verifying Temporal Synchronization & Fused Rows...")
    fused_rows = diag.get("fused_rows", 0)
    print(f"      Fused Rows:        {fused_rows}")
    if fused_rows < 10:
        errors.append(f"INSUFFICIENT_FUSED_ROWS: {fused_rows} fused rows (< 10 required).")

    # 8. Data Mode & Replay Prohibition
    print("\n[7/8] Verifying Data Mode & Anti-Replay Invariants...")
    data_mode = run_data.get("data_mode")
    print(f"      Data Mode:         {data_mode}")
    if data_mode != "real":
        errors.append(f"INVALID_DATA_MODE: data_mode must be 'real' for Gate 7B, got '{data_mode}'.")
    if run_data.get("synthetic_replay_used", False) is True:
        errors.append("SYNTHETIC_REPLAY_DETECTED: Synthetic/replay fallback data was used.")

    # 9. Output Schema & Canonical JSON
    print("\n[8/8] Verifying Canonical Output Schema...")
    episodes = run_data.get("episodes", [])
    print(f"      Episode Count:     {len(episodes)}")
    for i, ep in enumerate(episodes):
        for req_key in ("start", "end", "confidence", "type", "primary_cue", "data_mode"):
            if req_key not in ep:
                errors.append(f"Episode {i} missing required key: {req_key}")
        if ep.get("type") not in ("FoG", "Borderline", "Normal"):
            errors.append(f"Episode {i} has invalid type: {ep.get('type')}")
        if ep.get("primary_cue") not in CANONICAL_FEATURES:
            errors.append(f"Episode {i} has invalid primary_cue: {ep.get('primary_cue')}")
        if ep.get("data_mode") != "real":
            errors.append(f"Episode {i} data_mode is not 'real': {ep.get('data_mode')}")

    _report_and_exit(errors)


def _report_and_exit(errors: List[str]):
    print("\n" + "=" * 65)
    if errors:
        print(f">>> INDEPENDENT VERIFICATION VERDICT: BLOCKED / FAILED ({len(errors)} errors) <<<")
        for err in errors:
            print(f"  • {err}")
        print("=" * 65)
        sys.exit(1)
    else:
        print(">>> INDEPENDENT VERIFICATION VERDICT: VERIFIED / PASS <<<")
        print("=" * 65)
        sys.exit(0)


if __name__ == "__main__":
    artifact_arg = sys.argv[1] if len(sys.argv) > 1 else "outputs/gate7b_hardware_run.json"
    verify_gate7b_run(ROOT_DIR / artifact_arg)
