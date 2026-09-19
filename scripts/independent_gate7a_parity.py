#!/usr/bin/env python3
"""Independent Verification Script for Gate 7A Parity Check.

Independently loads and executes Recorded Mode and Live Mode pipelines,
directly comparing episode fields without calling existing parity helper functions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import predict_fog
from src.live_pipeline import VideoFrameGenerator, IMUStreamReplayer, LivePipelineSession


def run_independent_parity():
    video_path = "data/raw/videos/PDFE01_1.mp4"
    imu_path = "data/raw/imu/SUB01_1.txt"
    model_path = "models/fog_model.pkl"

    print("=" * 60)
    print("NEUROGAIT INDEPENDENT GATE 7A PARITY VERIFICATION")
    print("=" * 60)

    # 1. Independently run Recorded Mode
    print("\n[1/3] Running Recorded Mode Pipeline...")
    recorded_episodes = predict_fog(
        video_path=video_path,
        csv_path=imu_path,
        model_path=model_path,
        data_mode="real",
    )

    # 2. Independently run Live Mode Emulation
    print("\n[2/3] Running Live Mode Pipeline...")
    vf_gen = VideoFrameGenerator(video_path)
    imu_rep = IMUStreamReplayer(imu_path)

    session = LivePipelineSession(model_path=model_path)
    session.start_monitoring(video_fps=vf_gen.fps)

    for frame in vf_gen.stream_frames():
        session.process_camera_frame(frame)

    for sample in imu_rep.stream_samples():
        session.process_imu_sample(sample)

    live_res = session.stop_monitoring(video_fps=vf_gen.fps)
    live_episodes = live_res["episodes"]

    # 3. Independent Field-by-Field Analysis
    print("\n[3/3] Performing Independent Numerical & Categorical Comparison...")

    rec_count = len(recorded_episodes)
    live_count = len(live_episodes)

    print(f"\nRecorded episode count: {rec_count}")
    print(f"Live episode count: {live_count}")

    min_len = min(rec_count, live_count)

    exact_start_matches = 0
    exact_end_matches = 0
    exact_conf_matches = 0
    exact_type_matches = 0
    exact_cue_matches = 0

    conf_diffs = []
    start_diffs = []
    end_diffs = []

    print("\nEpisode-by-episode comparison:")
    print("-" * 60)

    all_matched = (rec_count == live_count)

    for idx in range(min_len):
        r = recorded_episodes[idx]
        l = live_episodes[idx]

        s_match = (r["start"] == l["start"])
        e_match = (r["end"] == l["end"])
        c_match = (r["confidence"] == l["confidence"])
        t_match = (r["type"] == l["type"])
        cue_match = (r["primary_cue"] == l["primary_cue"])

        if s_match:
            exact_start_matches += 1
        if e_match:
            exact_end_matches += 1
        if c_match:
            exact_conf_matches += 1
        if t_match:
            exact_type_matches += 1
        if cue_match:
            exact_cue_matches += 1

        conf_diffs.append(abs(r["confidence"] - l["confidence"]))
        start_diffs.append(abs(r["start"] - l["start"]))
        end_diffs.append(abs(r["end"] - l["end"]))

        is_ep_match = s_match and e_match and c_match and t_match and cue_match
        if not is_ep_match:
            all_matched = False

        status_str = "MATCH" if is_ep_match else "MISMATCH"
        print(f"Episode {idx}:")
        print(f"  Recorded: start={r['start']}, end={r['end']}, conf={r['confidence']}, type={r['type']}, cue={r['primary_cue']}")
        print(f"  Live:     start={l['start']}, end={l['end']}, conf={l['confidence']}, type={l['type']}, cue={l['primary_cue']}")
        print(f"  Verdict:  {status_str}")

    print("-" * 60)
    print(f"\nExact start matches: {exact_start_matches} / {min_len}")
    print(f"Exact end matches: {exact_end_matches} / {min_len}")
    print(f"Exact confidence matches: {exact_conf_matches} / {min_len}")
    print(f"Exact type matches: {exact_type_matches} / {min_len}")
    print(f"Exact primary cue matches: {exact_cue_matches} / {min_len}")

    print(f"\nmax confidence absolute difference: {max(conf_diffs):.6f}")
    print(f"mean confidence absolute difference: {np.mean(conf_diffs):.6f}")
    print(f"max start difference: {max(start_diffs):.6f}")
    print(f"max end difference: {max(end_diffs):.6f}")

    print("\nOVERALL PARITY VERDICT:")
    if all_matched and rec_count == live_count:
        print(">>> PASS: 100% INDEPENDENT PARITY CONFIRMED <<<")
    else:
        print(">>> FAIL: PARITY MISMATCH DETECTED <<<")
        sys.exit(1)


if __name__ == "__main__":
    run_independent_parity()
