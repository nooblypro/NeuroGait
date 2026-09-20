#!/usr/bin/env python3
"""CLI script to run inference with the NeuroGait Phase 1 model."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import predict_fog


def main():
    parser = argparse.ArgumentParser(description="Run NeuroGait FoG inference on video and IMU data.")
    parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="Path to patient video (.mp4)",
    )
    parser.add_argument(
        "--imu",
        type=str,
        required=True,
        help="Path to patient IMU file (.txt or .csv)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/fog_model.pkl",
        help="Path to trained model artifact (default: models/fog_model.pkl)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/predictions.json",
        help="Path to output canonical JSON file (default: outputs/predictions.json)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional limit on video frames to process",
    )
    args = parser.parse_args()

    # Compute and verify model hash for observability
    m_path = Path(args.model)
    hasher = hashlib.sha256()
    with open(m_path, "rb") as f:
        hasher.update(f.read())
    digest = hasher.hexdigest()
    hash_status = "MATCHES PHASE 1 BASELINE" if digest == "02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf" else "EXPERIMENTAL / CUSTOM MODEL"
    print(f"Model Artifact: {m_path} (SHA256: {digest[:16]}... [{hash_status}])")

    results = predict_fog(
        video_path=args.video,
        csv_path=args.imu,
        model_path=args.model,
        output_json_path=args.output,
        max_frames=args.max_frames,
    )

    fog_eps = [e for e in results if e.get("type") == "FoG"]
    border_eps = [e for e in results if e.get("type") == "Borderline"]
    norm_eps = [e for e in results if e.get("type") == "Normal"]

    print("\n" + "=" * 50)
    print("MANUAL INFERENCE EXECUTION SUMMARY")
    print("-" * 50)
    print(f"Total Formed Episodes: {len(results)}")
    print(f"  - FoG Episodes (p >= 0.60):       {len(fog_eps)}")
    print(f"  - Borderline Intervals (0.4-0.6): {len(border_eps)}")
    print(f"  - Normal Segments (p < 0.40):     {len(norm_eps)}")
    print(f"Output File: {args.output}")
    print("=" * 50)

    print("\nSample Formed Episodes (First 5):")
    print(json.dumps(results[:5], indent=2))
    if len(results) > 5:
        print(f"... and {len(results) - 5} more episodes.")


if __name__ == "__main__":
    main()
