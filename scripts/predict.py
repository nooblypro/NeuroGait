#!/usr/bin/env python3
"""CLI script to run inference with the NeuroGait Phase 1 model."""

import argparse
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

    results = predict_fog(
        video_path=args.video,
        csv_path=args.imu,
        model_path=args.model,
        output_json_path=args.output,
        max_frames=args.max_frames,
    )

    print("\nInference Output Summary:")
    print(json.dumps(results[:5], indent=2))
    if len(results) > 5:
        print(f"... and {len(results) - 5} more episodes.")


if __name__ == "__main__":
    main()
