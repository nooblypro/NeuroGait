"""Episode aggregation, threshold classification, and primary cue determination.

Thresholds:
- p >= 0.60: FoG
- 0.40 <= p < 0.60: Borderline
- p < 0.40: Normal
(Borderline is NOT a trained class, it is a post-processing decision band.)

Episodes:
- Group consecutive windows with the same type.
- Merge same-type episodes when gap <= 1.0 second.
- Episode confidence: mean class-1 probability across windows in that episode.
- Preserve actual timestamps.

Primary Cue:
- For each episode, calculate feature means.
- Compare episode means with the subject's overall feature median.
- Use the training scaler for standardized deviation:
    z_j = |mean_j(episode) - median_j(subject)| / scaler.scale_[j]
- Ignore features with zero variance/std.
- Select the largest valid deviation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from sklearn.preprocessing import StandardScaler

from src.features import CANONICAL_FEATURES


@dataclass
class Episode:
    start: float
    end: float
    confidence: float
    type: str
    primary_cue: str
    data_mode: str = "real"
    window_indices: Optional[List[int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": round(float(self.start), 3),
            "end": round(float(self.end), 3),
            "confidence": round(float(self.confidence), 4),
            "type": self.type,
            "primary_cue": self.primary_cue,
            "data_mode": self.data_mode,
        }


def classify_window_type(prob: float) -> str:
    """Classify a single class-1 probability into canonical decision bands."""
    if prob >= 0.60:
        return "FoG"
    elif prob >= 0.40:
        return "Borderline"
    else:
        return "Normal"


def determine_primary_cue(
    X_episode: np.ndarray,
    subject_median: np.ndarray,
    scaler: StandardScaler,
    feature_names: Sequence[str] = CANONICAL_FEATURES,
) -> str:
    """Calculate the primary cue for an episode using standardized absolute deviation.

    Formula:
        z_j = |mean_j(episode) - median_j(subject)| / sigma_j(scaler)
        where sigma_j is scaler.scale_[j]

    Returns:
        feature_name: The canonical feature name with the maximum valid standardized deviation.
    """
    if len(X_episode) == 0:
        return feature_names[0]

    episode_means = np.mean(X_episode, axis=0)
    scales = getattr(scaler, "scale_", None)
    if scales is None:
        scales = np.ones(len(feature_names), dtype=np.float64)

    z_scores = np.zeros(len(feature_names), dtype=np.float64)
    for j in range(len(feature_names)):
        scale = scales[j]
        if scale <= 1e-9 or np.isnan(scale):
            z_scores[j] = -1.0  # Ignore features with zero variance/std
        else:
            diff = np.abs(episode_means[j] - subject_median[j])
            z_scores[j] = diff / scale

    best_idx = int(np.argmax(z_scores))
    if z_scores[best_idx] < 0:
        # If all features were zero-variance, fallback to 0
        best_idx = 0

    return str(feature_names[best_idx])


def aggregate_episodes(
    timestamps: np.ndarray,
    probabilities: np.ndarray,
    X: np.ndarray,
    scaler: StandardScaler,
    window_duration: float = 1.0,
    max_merge_gap: float = 1.0,
    data_mode: str = "real",
) -> List[Episode]:
    """Resolve overlapping prediction windows and aggregate into non-overlapping temporal episodes.

    Pipeline Stages:
    1. RAW MODEL WINDOWS: Extract raw window intervals [t_start, t_end] from end timestamps.
    2. TEMPORALLY RESOLVED WINDOWS: Partition timeline at all window boundaries into elementary
       non-overlapping intervals. For each interval, determine the resolved state by strongest
       evidence (highest class-1 probability among overlapping windows).
    3. FINAL NON-OVERLAPPING EPISODES: Merge adjacent and near-adjacent (gap <= max_merge_gap)
       resolved intervals of the same type into cohesive clinical episodes with confidence and
       primary cue calculation.

    Args:
        timestamps: 1D array of window END timestamps.
        probabilities: 1D array of class-1 probabilities.
        X: Feature matrix of shape (N, 8).
        scaler: Fitted StandardScaler from training.
        window_duration: Duration of each rolling window in seconds (default 1.0).
        max_merge_gap: Maximum gap in seconds to merge same-type episodes (default 1.0).
        data_mode: "real" or "synthetic_demo".

    Returns:
        episodes: Chronologically sorted list of non-overlapping Episode objects.
    """
    N = len(timestamps)
    if N == 0:
        return []

    subject_median = np.median(X, axis=0)

    # ---------------------------------------------------------
    # Stage 1: Raw Model Windows
    # ---------------------------------------------------------
    raw_windows = []
    for i in range(N):
        t_end = float(timestamps[i])
        t_start = max(0.0, t_end - window_duration)
        prob = float(probabilities[i])
        raw_windows.append({
            "index": i,
            "start": t_start,
            "end": t_end,
            "prob": prob,
            "type": classify_window_type(prob),
        })

    # ---------------------------------------------------------
    # Stage 2: Elementary Interval Partitioning & Temporal Resolution
    # ---------------------------------------------------------
    # Collect all distinct critical boundary points
    boundaries = sorted(set(
        [w["start"] for w in raw_windows] + [w["end"] for w in raw_windows]
    ))

    elementary_intervals = []
    for k in range(len(boundaries) - 1):
        t0 = boundaries[k]
        t1 = boundaries[k + 1]
        if t1 - t0 < 1e-6:
            continue

        # Find active covering raw windows for interval [t0, t1]
        covering = [
            w for w in raw_windows
            if w["start"] <= t0 + 1e-6 and w["end"] >= t1 - 1e-6
        ]

        if not covering:
            continue

        # Strongest evidence resolution:
        # Highest probability among covering windows determines the state
        max_prob = max(w["prob"] for w in covering)
        resolved_type = classify_window_type(max_prob)

        # Covering window indices for feature/cue calculation
        matching_indices = [w["index"] for w in covering if w["type"] == resolved_type]
        if not matching_indices:
            matching_indices = [w["index"] for w in covering]

        elementary_intervals.append({
            "start": t0,
            "end": t1,
            "type": resolved_type,
            "indices": matching_indices,
        })

    if not elementary_intervals:
        return []

    # ---------------------------------------------------------
    # Stage 3: Merge Consecutive Same-Type Intervals into Final Episodes
    # ---------------------------------------------------------
    merged_spans = []
    curr = elementary_intervals[0]
    curr_start = curr["start"]
    curr_end = curr["end"]
    curr_type = curr["type"]
    curr_indices = set(curr["indices"])

    for interval in elementary_intervals[1:]:
        gap = interval["start"] - curr_end
        if interval["type"] == curr_type and gap <= max_merge_gap:
            curr_end = max(curr_end, interval["end"])
            curr_indices.update(interval["indices"])
        else:
            merged_spans.append({
                "type": curr_type,
                "start": curr_start,
                "end": curr_end,
                "indices": sorted(curr_indices),
            })
            curr_start = interval["start"]
            curr_end = interval["end"]
            curr_type = interval["type"]
            curr_indices = set(interval["indices"])

    merged_spans.append({
        "type": curr_type,
        "start": curr_start,
        "end": curr_end,
        "indices": sorted(curr_indices),
    })

    # Construct final Episode objects
    episodes: List[Episode] = []
    for span in merged_spans:
        idxs = span["indices"]
        # Filter raw windows that overlap this episode span and match the episode type
        ep_start = span["start"]
        ep_end = span["end"]
        ep_type = span["type"]

        overlapping_idxs = [
            w["index"] for w in raw_windows
            if w["start"] < ep_end and w["end"] > ep_start and w["type"] == ep_type
        ]
        if not overlapping_idxs:
            overlapping_idxs = [
                w["index"] for w in raw_windows
                if w["start"] < ep_end and w["end"] > ep_start
            ]
        if not overlapping_idxs:
            overlapping_idxs = idxs

        conf = float(np.mean([probabilities[idx] for idx in overlapping_idxs]))
        X_sub = X[overlapping_idxs]
        cue = determine_primary_cue(X_sub, subject_median, scaler)

        ep = Episode(
            start=round(float(span["start"]), 3),
            end=round(float(span["end"]), 3),
            confidence=conf,
            type=span["type"],
            primary_cue=cue,
            data_mode=data_mode,
            window_indices=overlapping_idxs,
        )
        episodes.append(ep)

    return episodes
