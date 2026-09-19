"""Unit tests for episode aggregation, thresholds, and primary cue attribution."""

import numpy as np
import pytest

from src.episodes import (
    aggregate_episodes,
    classify_window_type,
    determine_primary_cue,
)
from src.features import CANONICAL_FEATURES


def test_classify_window_type_thresholds():
    """Verify Section 10 thresholds:
    p >= 0.60 -> FoG
    0.40 <= p < 0.60 -> Borderline
    p < 0.40 -> Normal
    """
    assert classify_window_type(0.90) == "FoG"
    assert classify_window_type(0.60) == "FoG"
    assert classify_window_type(0.599) == "Borderline"
    assert classify_window_type(0.40) == "Borderline"
    assert classify_window_type(0.399) == "Normal"
    assert classify_window_type(0.0) == "Normal"


def test_episode_aggregation_and_gap_merging(fitted_scaler):
    """Verify contiguous grouping and merging when gap <= 1.0s."""
    # 5 contiguous FoG windows, small gap, then 3 FoG windows
    ts = np.array([1.0, 1.1, 1.2, 1.3, 1.4, 1.8, 1.9, 2.0])
    probs = np.array([0.7, 0.8, 0.9, 0.75, 0.85, 0.65, 0.70, 0.80])
    X = np.ones((len(ts), 8)) * 0.5

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
    )

    # Because gap between 1.4 and 1.8 is 0.4s (<= 1.0s), they should merge into 1 episode!
    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.type == "FoG"
    assert np.isclose(ep.confidence, np.mean(probs))
    assert ep.start <= 0.1  # 1.0 - 1.0 = 0.0
    assert ep.end == 2.0


def test_episode_keeps_large_gaps_separate(fitted_scaler):
    """Verify that same-type episodes with gap > 1.0s are kept separate."""
    # Two FoG windows separated by 3 seconds
    ts = np.array([2.0, 5.5])
    probs = np.array([0.8, 0.85])
    X = np.ones((2, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
    )

    assert len(episodes) == 2
    assert episodes[0].end == 2.0
    assert episodes[1].start == 4.5
    assert episodes[1].end == 5.5


def test_primary_cue_selection(fitted_scaler):
    """Verify that feature with maximum standardized deviation is selected as primary cue."""
    # Episode features: index 0 (left_ankle_velocity) differs greatly from median
    subject_median = np.array([0.5, 0.5, 125.0, 125.0, 0.3, 1.0, 30.0, 30.0])

    # In episode, left_ankle_velocity is 5.0 (huge deviation) while others are near median
    X_ep = np.array([
        [5.0, 0.5, 125.0, 125.0, 0.3, 1.0, 30.0, 30.0],
        [5.2, 0.5, 125.0, 125.0, 0.3, 1.0, 30.0, 30.0],
    ])

    cue = determine_primary_cue(X_ep, subject_median, fitted_scaler)
    assert cue == "left_ankle_velocity"
