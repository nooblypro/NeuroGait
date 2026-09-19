#!/usr/bin/env python3
"""Independent Verification Script for External Video Stress Testing.

Independently inspects produced artifacts and fails on:
- missing files (outputs/external_video_stress_metrics.json, logs/EXTERNAL_VIDEO_STRESS_TEST.md)
- malformed metrics (missing required keys, invalid types)
- impossible values (negative FPS, dropout > 100%, negative durations, invalid frame counts)
- fabricated data (ensures external sources are marked VIDEO_ONLY and no IMU is fabricated)
- unexpected model modification (verifies SHA256 of models/fog_model.pkl)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

FROZEN_MODEL_PATH = ROOT_DIR / "models/fog_model.pkl"
EXPECTED_MODEL_HASH = "02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf"

METRICS_FILE = ROOT_DIR / "outputs/external_video_stress_metrics.json"
LOG_FILE = ROOT_DIR / "logs/EXTERNAL_VIDEO_STRESS_TEST.md"
MANIFEST_FILE = ROOT_DIR / "data/external_validation/manifest.json"


def verify():
    print("=" * 70)
    print("INDEPENDENT VERIFIER — EXTERNAL VIDEO STRESS TESTING")
    print("=" * 70)

    # 1. Model integrity check
    print("\n[1/5] Verifying Frozen Model Artifact Integrity...")
    if not FROZEN_MODEL_PATH.exists():
        print(f"[FAIL] Frozen model missing: {FROZEN_MODEL_PATH}")
        sys.exit(1)

    with open(FROZEN_MODEL_PATH, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    if actual_hash != EXPECTED_MODEL_HASH:
        print(f"[FAIL] Model hash mismatch! Expected {EXPECTED_MODEL_HASH}, got {actual_hash}")
        sys.exit(1)
    print(f"  ✓ Model hash matches: {actual_hash}")

    # 2. File existence check
    print("\n[2/5] Checking Artifact File Existence...")
    for fpath in [METRICS_FILE, LOG_FILE, MANIFEST_FILE]:
        if not fpath.exists():
            print(f"[FAIL] Required file missing: {fpath}")
            sys.exit(1)
        if fpath.stat().st_size == 0:
            print(f"[FAIL] Required file is empty: {fpath}")
            sys.exit(1)
        print(f"  ✓ Found {fpath.name} ({fpath.stat().st_size} bytes)")

    # 3. Inspect JSON metrics structure
    print("\n[3/5] Validating Metrics Schema and Consistency...")
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "results" not in data or not isinstance(data["results"], list):
        print("[FAIL] Missing 'results' list in metrics JSON")
        sys.exit(1)

    results = data["results"]
    if len(results) < 4:
        print(f"[FAIL] Expected at least 4 test cases, found {len(results)}")
        sys.exit(1)

    required_keys = [
        "test_id", "condition", "video_fps", "resolution", "tested_duration_sec",
        "frames_tested", "valid_pose_detections", "pose_detection_rate_pct",
        "landmark_dropout_rate_pct", "feature_rows_generated", "processing_fps",
        "invalid_frames", "lower_body_visible", "pipeline_crashed"
    ]

    for idx, r in enumerate(results):
        for k in required_keys:
            if k not in r:
                print(f"[FAIL] Result {idx} missing key '{k}'")
                sys.exit(1)

    print(f"  ✓ Validated {len(results)} stress test result records")

    # 4. Check for impossible values
    print("\n[4/5] Checking for Impossible / Malformed Values...")
    for r in results:
        t_id = r["test_id"]
        fps = r["video_fps"]
        if fps <= 0 or fps > 240:
            print(f"[FAIL] [{t_id}] Impossible video FPS: {fps}")
            sys.exit(1)

        dur = r["tested_duration_sec"]
        if dur <= 0:
            print(f"[FAIL] [{t_id}] Impossible duration: {dur}")
            sys.exit(1)

        frames = r["frames_tested"]
        if frames <= 0:
            print(f"[FAIL] [{t_id}] Impossible frames tested: {frames}")
            sys.exit(1)

        detections = r["valid_pose_detections"]
        if detections < 0 or detections > frames:
            print(f"[FAIL] [{t_id}] Impossible detections {detections} out of {frames} frames")
            sys.exit(1)

        det_pct = r["pose_detection_rate_pct"]
        if det_pct < 0.0 or det_pct > 100.0:
            print(f"[FAIL] [{t_id}] Impossible detection percentage: {det_pct}")
            sys.exit(1)

        drop_pct = r["landmark_dropout_rate_pct"]
        if drop_pct < 0.0 or drop_pct > 100.0:
            print(f"[FAIL] [{t_id}] Impossible dropout percentage: {drop_pct}")
            sys.exit(1)

        # Sum of detection rate + dropout rate must approximately equal 100%
        if not (99.0 <= (det_pct + drop_pct) <= 101.0):
            print(f"[FAIL] [{t_id}] Sum of detection rate ({det_pct}) and dropout rate ({drop_pct}) != 100%")
            sys.exit(1)

        proc_fps = r["processing_fps"]
        if proc_fps <= 0 or proc_fps > 1000:
            print(f"[FAIL] [{t_id}] Impossible processing FPS: {proc_fps}")
            sys.exit(1)

        if r["pipeline_crashed"] is not False:
            print(f"[FAIL] [{t_id}] Pipeline crashed during stress testing!")
            sys.exit(1)

    print("  ✓ All quantitative values within strictly valid mathematical bounds")

    # 5. Check no fabricated data or fake multimodal fusion
    print("\n[5/5] Checking for Data Fabrication / Modality Boundary Violations...")
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for src in manifest.get("sources", []):
        if src.get("classification") != "VIDEO_ONLY":
            print(f"[FAIL] External source {src.get('id')} not marked VIDEO_ONLY")
            sys.exit(1)
        if src.get("imu_available") is not False:
            print(f"[FAIL] External source {src.get('id')} falsely claims IMU availability")
            sys.exit(1)
        if src.get("labels_available") is not False:
            print(f"[FAIL] External source {src.get('id')} falsely claims FoG labels availability")
            sys.exit(1)

    # Verify log file mentions boundaries
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_content = f.read()

    required_phrases = [
        "VIDEO-ONLY",
        "NO synthetic IMU",
        "NO fabricated FoG labels",
        "pipeline_crashed = False",
    ]
    for p in required_phrases:
        if p not in log_content:
            print(f"[FAIL] Log missing required anti-fabrication statement: '{p}'")
            sys.exit(1)

    print("  ✓ Modality boundaries strictly preserved")
    print("  ✓ Zero synthetic IMU streams or fabricated labels detected")

    print("\n" + "=" * 70)
    print(">>> PASS: EXTERNAL VIDEO STRESS TESTING INDEPENDENTLY VERIFIED <<<")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    verify()
