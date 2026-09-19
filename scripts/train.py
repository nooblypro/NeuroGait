#!/usr/bin/env python3
"""CLI script to train the NeuroGait Phase 1 model."""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import train_model


def main():
    parser = argparse.ArgumentParser(description="Train NeuroGait Phase 1 FoG detector model.")
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="data",
        help="Path to dataset directory containing raw/processed data",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/fog_model.pkl",
        help="Path to save the trained model artifact (default: models/fog_model.pkl)",
    )
    parser.add_argument(
        "--max-subjects",
        type=int,
        default=None,
        help="Optional limit on number of subjects to process",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional limit on frames per video for quick test runs",
    )
    args = parser.parse_args()

    train_model(
        dataset_dir=args.dataset_dir,
        model_output_path=args.output,
        max_subjects=args.max_subjects,
        max_video_frames=args.max_frames,
    )


if __name__ == "__main__":
    main()
