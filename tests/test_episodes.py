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


def test_overlapping_fog_and_normal_windows(fitted_scaler):
    """1. Overlapping FoG + Normal windows: Strongest evidence resolves to FoG in overlap, zero overlap in final."""
    # Window 0: FoG (prob=0.85) from 6.7 to 7.7 (ts=7.7)
    # Window 1: Normal (prob=0.15) from 6.8 to 8.9 (ts=8.9 with window_duration=2.1, or standard 1.0s)
    # Let's test standard 1.0s windows:
    # W0: 1.0s end at 2.0 -> [1.0, 2.0], FoG (0.85)
    # W1: 1.0s end at 2.5 -> [1.5, 2.5], Normal (0.15)
    ts = np.array([2.0, 2.5])
    probs = np.array([0.85, 0.15])
    X = np.ones((2, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
    )

    # In [1.0, 1.5]: only W0 active -> FoG
    # In [1.5, 2.0]: W0 (0.85) and W1 (0.15) active -> max_prob=0.85 -> FoG
    # In [2.0, 2.5]: only W1 active -> Normal
    # Merged: FoG in [1.0, 2.0], Normal in [2.0, 2.5]
    assert len(episodes) == 2
    assert episodes[0].type == "FoG"
    assert episodes[0].start == 1.0
    assert episodes[0].end == 2.0
    assert episodes[1].type == "Normal"
    assert episodes[1].start == 2.0
    assert episodes[1].end == 2.5
    assert episodes[0].end <= episodes[1].start


def test_overlapping_fog_and_borderline_windows(fitted_scaler):
    """2. Overlapping FoG + Borderline windows: FoG dominates overlap."""
    ts = np.array([2.0, 2.5])
    probs = np.array([0.85, 0.50])
    X = np.ones((2, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
    )

    # [1.0, 2.0] FoG, [2.0, 2.5] Borderline
    assert len(episodes) == 2
    assert episodes[0].type == "FoG"
    assert episodes[0].start == 1.0
    assert episodes[0].end == 2.0
    assert episodes[1].type == "Borderline"
    assert episodes[1].start == 2.0
    assert episodes[1].end == 2.5
    assert episodes[0].end <= episodes[1].start


def test_three_way_overlap(fitted_scaler):
    """3. Three-way overlap: Normal, Borderline, FoG overlapping simultaneously."""
    # W0: [1.0, 2.0] Normal (0.2)
    # W1: [1.2, 2.2] Borderline (0.45)
    # W2: [1.4, 2.4] FoG (0.80)
    ts = np.array([2.0, 2.2, 2.4])
    probs = np.array([0.20, 0.45, 0.80])
    X = np.ones((3, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
    )

    # [1.0, 1.2]: Normal
    # [1.2, 1.4]: Borderline (0.45 > 0.20)
    # [1.4, 2.4]: FoG (0.80 > 0.45, 0.20)
    assert len(episodes) == 3
    assert episodes[0].type == "Normal"
    assert episodes[0].start == 1.0
    assert episodes[0].end == 1.2

    assert episodes[1].type == "Borderline"
    assert episodes[1].start == 1.2
    assert episodes[1].end == 1.4

    assert episodes[2].type == "FoG"
    assert episodes[2].start == 1.4
    assert episodes[2].end == 2.4

    # Strict ordering and non-overlap
    for i in range(len(episodes) - 1):
        assert episodes[i].end <= episodes[i + 1].start


def test_adjacent_same_type_windows(fitted_scaler):
    """4. Adjacent same-type windows: Merge seamlessly."""
    ts = np.array([1.0, 2.0])  # [0.0, 1.0] and [1.0, 2.0]
    probs = np.array([0.70, 0.80])
    X = np.ones((2, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
    )

    assert len(episodes) == 1
    assert episodes[0].type == "FoG"
    assert episodes[0].start == 0.0
    assert episodes[0].end == 2.0


def test_overlapping_same_type_windows(fitted_scaler):
    """5. Overlapping same-type windows: Merge into one continuous episode."""
    ts = np.array([1.0, 1.5, 2.0])
    probs = np.array([0.70, 0.75, 0.80])
    X = np.ones((3, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
    )

    assert len(episodes) == 1
    assert episodes[0].type == "FoG"
    assert episodes[0].start == 0.0
    assert episodes[0].end == 2.0


def test_gaps_between_episodes_preserved(fitted_scaler):
    """6. Gaps between episodes (> 1.0s): Kept distinct."""
    ts = np.array([1.0, 4.0])  # [0.0, 1.0] and [3.0, 4.0], gap = 2.0s > 1.0s
    probs = np.array([0.80, 0.85])
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
    assert episodes[0].start == 0.0
    assert episodes[0].end == 1.0
    assert episodes[1].start == 3.0
    assert episodes[1].end == 4.0
    assert episodes[0].end < episodes[1].start


def test_exact_threshold_boundaries(fitted_scaler):
    """7. Exact threshold values: 0.399999..., 0.40, 0.599999..., 0.60."""
    # 4 distinct windows separated by > 1s gap to test pure classification
    ts = np.array([1.0, 3.0, 5.0, 7.0])
    probs = np.array([0.3999999, 0.40, 0.5999999, 0.60])
    X = np.ones((4, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=0.5,
    )

    assert len(episodes) == 4
    assert episodes[0].type == "Normal"
    assert episodes[1].type == "Borderline"
    assert episodes[2].type == "Borderline"
    assert episodes[3].type == "FoG"


def test_empty_predictions(fitted_scaler):
    """8. Empty predictions input."""
    episodes = aggregate_episodes(
        timestamps=np.array([]),
        probabilities=np.array([]),
        X=np.zeros((0, 8)),
        scaler=fitted_scaler,
    )
    assert episodes == []


def test_single_prediction_window(fitted_scaler):
    """9. Single prediction window."""
    ts = np.array([1.0])
    probs = np.array([0.75])
    X = np.ones((1, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
    )

    assert len(episodes) == 1
    assert episodes[0].type == "FoG"
    assert episodes[0].start == 0.0
    assert episodes[0].end == 1.0
    assert np.isclose(episodes[0].confidence, 0.75)


def test_confidence_preservation(fitted_scaler):
    """10. Confidence preservation across contributing windows."""
    ts = np.array([1.0, 1.5])
    probs = np.array([0.70, 0.80])
    X = np.ones((2, 8))

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
    )

    assert len(episodes) == 1
    assert np.isclose(episodes[0].confidence, 0.75)


def test_primary_cue_preservation(fitted_scaler):
    """11. Primary cue preservation for aggregated episode."""
    # 2 baseline normal windows at 0.0, followed by 2 FoG windows with feature 6 deviation
    ts = np.array([1.0, 2.0, 5.0, 5.5])
    probs = np.array([0.10, 0.10, 0.70, 0.80])
    # Feature 6 (left_knee_flexion_range) deviates significantly in the FoG windows
    X = np.zeros((4, 8))
    X[2:, 6] = 50.0  # Big deviation in FoG episode (subject median for col 6 remains 0.0)

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
    )

    # Episodes: Normal [0.0, 2.0], FoG [4.0, 5.5]
    assert len(episodes) == 2
    fog_ep = episodes[1]
    assert fog_ep.type == "FoG"
    assert fog_ep.primary_cue == "gyro_x_var"


def test_canonical_json_schema_and_non_overlapping_invariant(fitted_scaler):
    """12. Strict invariant: FINAL EPISODES MUST NEVER OVERLAP, schema preserved."""
    # Complex sequence of alternating and overlapping windows
    np.random.seed(42)
    N = 50
    # Sliding windows with step 0.1s
    ts = np.linspace(1.0, 6.0, N)
    probs = np.random.uniform(0.0, 1.0, N)
    X = np.random.randn(N, 8)

    episodes = aggregate_episodes(
        timestamps=ts,
        probabilities=probs,
        X=X,
        scaler=fitted_scaler,
        window_duration=1.0,
        max_merge_gap=1.0,
        data_mode="real",
    )

    assert len(episodes) > 0

    # Invariant: episode[i].end <= episode[i+1].start for every consecutive pair
    for i in range(len(episodes) - 1):
        assert episodes[i].end <= episodes[i + 1].start, (
            f"Overlap detected between episode {i} [{episodes[i].start}, {episodes[i].end}] "
            f"and episode {i+1} [{episodes[i+1].start}, {episodes[i+1].end}]"
        )

    # Invariant: Canonical JSON schema compliance
    required_keys = {"start", "end", "confidence", "type", "primary_cue", "data_mode"}
    for ep in episodes:
        d = ep.to_dict()
        assert set(d.keys()) == required_keys
        assert isinstance(d["start"], float)
        assert isinstance(d["end"], float)
        assert isinstance(d["confidence"], float)
        assert d["type"] in {"FoG", "Borderline", "Normal"}
        assert d["primary_cue"] in CANONICAL_FEATURES
        assert d["data_mode"] == "real"
        assert d["start"] < d["end"]
