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
    """Group consecutive windows, merge gaps <= 1s, compute confidence and primary cues.

    Args:
        timestamps: 1D array of window END timestamps.
        probabilities: 1D array of class-1 probabilities.
        X: Feature matrix of shape (N, 8).
        scaler: Fitted StandardScaler from training.
        window_duration: Duration of each rolling window in seconds (default 1.0).
        max_merge_gap: Maximum gap in seconds to merge same-type episodes (default 1.0).
        data_mode: "real" or "synthetic_demo".

    Returns:
        episodes: List of aggregated Episode objects.
    """
    N = len(timestamps)
    if N == 0:
        return []

    types = [classify_window_type(float(p)) for p in probabilities]
    subject_median = np.median(X, axis=0)

    # 1. Group consecutive windows of the same type
    raw_episodes: List[Dict[str, Any]] = []
    curr_type = types[0]
    curr_indices = [0]
    curr_start = max(0.0, float(timestamps[0]) - window_duration)
    curr_end = float(timestamps[0])

    for i in range(1, N):
        t_end = float(timestamps[i])
        t_start = max(0.0, t_end - window_duration)
        w_type = types[i]
        gap = t_start - curr_end

        if w_type == curr_type and gap <= max_merge_gap:
            curr_indices.append(i)
            curr_end = t_end
        else:
            raw_episodes.append({
                "type": curr_type,
                "start": curr_start,
                "end": curr_end,
                "indices": curr_indices,
            })
            curr_type = w_type
            curr_indices = [i]
            curr_start = t_start
            curr_end = t_end

    raw_episodes.append({
        "type": curr_type,
        "start": curr_start,
        "end": curr_end,
        "indices": curr_indices,
    })

    # 2. Merge same-type episodes when gap <= max_merge_gap
    merged = True
    while merged:
        merged = False
        new_episodes: List[Dict[str, Any]] = []
        i = 0
        while i < len(raw_episodes):
            if i + 1 < len(raw_episodes):
                ep1 = raw_episodes[i]
                ep2 = raw_episodes[i + 1]
                gap = ep2["start"] - ep1["end"]
                if ep1["type"] == ep2["type"] and 0.0 <= gap <= max_merge_gap:
                    # Merge ep1 and ep2
                    combined = {
                        "type": ep1["type"],
                        "start": ep1["start"],
                        "end": ep2["end"],
                        "indices": ep1["indices"] + ep2["indices"],
                    }
                    new_episodes.append(combined)
                    i += 2
                    merged = True
                    continue
            new_episodes.append(raw_episodes[i])
            i += 1
        raw_episodes = new_episodes

    # 3. Create Episode instances with confidence and primary cue
    episodes: List[Episode] = []
    for ep_dict in raw_episodes:
        idxs = ep_dict["indices"]
        conf = float(np.mean([probabilities[idx] for idx in idxs]))
        X_sub = X[idxs]
        cue = determine_primary_cue(X_sub, subject_median, scaler)

        ep = Episode(
            start=float(ep_dict["start"]),
            end=float(ep_dict["end"]),
            confidence=conf,
            type=ep_dict["type"],
            primary_cue=cue,
            data_mode=data_mode,
            window_indices=idxs,
        )
        episodes.append(ep)

    return episodes
