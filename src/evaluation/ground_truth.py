"""Ground-Truth Parsing, Temporal Alignment, and Error Analysis Module for NeuroGait.

Provides authoritative parsing of PDFEinfo.xls/csv annotations,
deterministic temporal intersection/union/IoU calculations,
and episode/window-level evaluation metrics.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class GroundTruthEpisode:
    recording_id: str
    subject_id: str
    session_id: str
    start: float
    end: float
    type: str = "FoG"

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class RecordingAnnotation:
    recording_id: str
    subject_id: str
    session_id: str
    raw_interval_string: str
    raw_duration_string: str
    raw_episodes_count_string: str
    fog_episodes: List[GroundTruthEpisode]
    status: str  # VALID, MISSING_VIDEO, MISSING_IMU, MISSING_ANNOTATION, etc.
    status_reason: str


def parse_raw_interval_string(
    raw_str: str, recording_id: str, subject_id: str, session_id: str
) -> List[GroundTruthEpisode]:
    """Parse raw spreadsheet annotation string into canonical GroundTruthEpisode objects.

    Examples:
        '[55.797-58.507]' -> [GroundTruthEpisode(55.797, 58.507)]
        '[1.383-35.768; 36.696-65.969]' -> 2 episodes
        '0', '0.00', '-', '' -> []
        '[37.609-9.659; ...]' -> preserves timestamps, normalizes inverted order
    """
    cleaned = str(raw_str).strip()
    if not cleaned or cleaned in {"-", "0", "0.0", "0.00", "nan", "None"}:
        return []

    cleaned = cleaned.replace("[", "").replace("]", "").replace('"', "").strip()
    if not cleaned:
        return []

    episodes: List[GroundTruthEpisode] = []
    for part in cleaned.split(";"):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            subparts = part.split("-")
            if len(subparts) >= 2:
                try:
                    # Handle potential leading negative or dash splits
                    t0_str = subparts[0].strip()
                    t1_str = subparts[1].strip()
                    t0 = float(t0_str)
                    t1 = float(t1_str)
                    if t1 < t0:
                        # Malformed inverted entry in raw sheet (e.g. 37.609-9.659)
                        t0, t1 = min(t0, t1), max(t0, t1)
                    episodes.append(
                        GroundTruthEpisode(
                            recording_id=recording_id,
                            subject_id=subject_id,
                            session_id=session_id,
                            start=round(t0, 3),
                            end=round(t1, 3),
                            type="FoG",
                        )
                    )
                except ValueError:
                    continue
    return episodes


def parse_pdfe_info(
    csv_or_xls_path: Union[str, Path],
) -> Dict[str, RecordingAnnotation]:
    """Parse PDFEinfo.csv or PDFEinfo.xls into canonical recording annotations."""
    path = Path(csv_or_xls_path)
    if not path.exists():
        raise FileNotFoundError(f"Annotation source not found: {path}")

    # Read lines (using latin1 to preserve degree and micro symbols)
    with open(path, "r", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    header = rows[0] if rows else []
    recordings: Dict[str, RecordingAnnotation] = {}

    for r in rows[1:]:
        if not r or not r[0].startswith("PDFE"):
            continue
        sub_id = r[0].strip()
        num_sessions_str = r[9].strip() if len(r) > 9 else "0"
        try:
            num_sessions = int(num_sessions_str)
        except ValueError:
            num_sessions = 0

        for s in [1, 2, 3]:
            rec_id = f"{sub_id}_{s}"
            col_fog = 24 if s == 1 else (42 if s == 2 else 60)
            col_dur = 25 if s == 1 else (43 if s == 2 else 61)
            col_cnt = 26 if s == 1 else (44 if s == 2 else 62)

            raw_fog = r[col_fog].strip() if col_fog < len(r) else "-"
            raw_dur = r[col_dur].strip() if col_dur < len(r) else "-"
            raw_cnt = r[col_cnt].strip() if col_cnt < len(r) else "-"

            if raw_fog == "-" or (s > num_sessions and raw_fog in {"-", ""}):
                status = "MISSING ANNOTATION" if s <= num_sessions else "NOT CONDUCTED"
                reason = "Spreadsheet indicates session was not recorded or data is absent ('-')"
                recordings[rec_id] = RecordingAnnotation(
                    recording_id=rec_id,
                    subject_id=sub_id,
                    session_id=str(s),
                    raw_interval_string=raw_fog,
                    raw_duration_string=raw_dur,
                    raw_episodes_count_string=raw_cnt,
                    fog_episodes=[],
                    status=status,
                    status_reason=reason,
                )
            else:
                episodes = parse_raw_interval_string(raw_fog, rec_id, sub_id, str(s))
                recordings[rec_id] = RecordingAnnotation(
                    recording_id=rec_id,
                    subject_id=sub_id,
                    session_id=str(s),
                    raw_interval_string=raw_fog,
                    raw_duration_string=raw_dur,
                    raw_episodes_count_string=raw_cnt,
                    fog_episodes=episodes,
                    status="VALID",
                    status_reason="Authoritative annotation present",
                )

    return recordings


def compute_interval_overlap_and_iou(
    a_start: float, a_end: float, b_start: float, b_end: float
) -> Tuple[float, float]:
    """Compute exact intersection (overlap) in seconds and IoU for two intervals [a_start, a_end] and [b_start, b_end].

    intersection = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = (a_end - a_start) + (b_end - b_start) - intersection
    iou = intersection / union (if union > 0 else 0)
    """
    inter = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    dur_a = max(0.0, a_end - a_start)
    dur_b = max(0.0, b_end - b_start)
    union = dur_a + dur_b - inter
    iou = (inter / union) if union > 1e-9 else 0.0
    return round(inter, 4), round(iou, 4)


def evaluate_temporal_episodes(
    gt_episodes: List[GroundTruthEpisode],
    pred_episodes: List[Dict[str, Any]],
    min_iou_match: float = 0.0,  # Any positive overlap counts as a temporal detection
) -> Dict[str, Any]:
    """Perform deterministic episode-level matching and temporal metrics calculation."""
    # Filter predictions to FoG only
    fog_preds = [p for p in pred_episodes if p.get("type") == "FoG"]

    total_gt = len(gt_episodes)
    total_pred = len(fog_preds)

    if total_gt == 0 and total_pred == 0:
        return {
            "gt_episodes_count": 0,
            "pred_episodes_count": 0,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "mean_iou": 0.0,
            "median_iou": 0.0,
            "temporal_coverage_pct": 100.0,
            "matches": [],
            "extra_predictions": [],
            "missed_ground_truth": [],
            "detailed_comparisons": [],
        }

    if total_gt == 0 and total_pred > 0:
        return {
            "gt_episodes_count": 0,
            "pred_episodes_count": total_pred,
            "tp": 0,
            "fp": total_pred,
            "fn": 0,
            "precision": 0.0,
            "recall": 1.0,  # No GT to miss
            "f1": 0.0,
            "mean_iou": 0.0,
            "median_iou": 0.0,
            "temporal_coverage_pct": 0.0,
            "matches": [],
            "extra_predictions": fog_preds,
            "missed_ground_truth": [],
            "detailed_comparisons": [
                {
                    "pred_start": p["start"],
                    "pred_end": p["end"],
                    "gt_start": None,
                    "gt_end": None,
                    "overlap_seconds": 0.0,
                    "iou": 0.0,
                    "classification": "FALSE_POSITIVE",
                    "confidence": p.get("confidence", 0.0),
                    "primary_cue": p.get("primary_cue", "None"),
                }
                for p in fog_preds
            ],
        }

    # Evaluate overlap for all pairs
    detailed_comparisons: List[Dict[str, Any]] = []
    matched_gt_indices = set()
    matched_pred_indices = set()
    overlap_durations_per_gt: Dict[int, float] = {i: 0.0 for i in range(total_gt)}
    matched_ious: List[float] = []

    for p_idx, p in enumerate(fog_preds):
        best_gt_idx = None
        best_overlap = 0.0
        best_iou = 0.0

        for g_idx, gt in enumerate(gt_episodes):
            overlap, iou = compute_interval_overlap_and_iou(
                p["start"], p["end"], gt.start, gt.end
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_iou = iou
                best_gt_idx = g_idx

        if best_overlap > 0.0 and best_gt_idx is not None:
            overlap_durations_per_gt[best_gt_idx] += best_overlap
            matched_pred_indices.add(p_idx)
            is_first_match = best_gt_idx not in matched_gt_indices
            matched_gt_indices.add(best_gt_idx)
            matched_ious.append(best_iou)

            classification = "TRUE_POSITIVE" if is_first_match else "FRAGMENTED_OVERLAP"
            detailed_comparisons.append({
                "pred_start": p["start"],
                "pred_end": p["end"],
                "gt_start": gt_episodes[best_gt_idx].start,
                "gt_end": gt_episodes[best_gt_idx].end,
                "overlap_seconds": best_overlap,
                "iou": best_iou,
                "classification": classification,
                "confidence": p.get("confidence", 0.0),
                "primary_cue": p.get("primary_cue", "None"),
            })
        else:
            detailed_comparisons.append({
                "pred_start": p["start"],
                "pred_end": p["end"],
                "gt_start": None,
                "gt_end": None,
                "overlap_seconds": 0.0,
                "iou": 0.0,
                "classification": "FALSE_POSITIVE",
                "confidence": p.get("confidence", 0.0),
                "primary_cue": p.get("primary_cue", "None"),
            })

    # Identify missed GT episodes
    missed_gt = []
    for g_idx, gt in enumerate(gt_episodes):
        if g_idx not in matched_gt_indices:
            missed_gt.append(gt)
            detailed_comparisons.append({
                "pred_start": None,
                "pred_end": None,
                "gt_start": gt.start,
                "gt_end": gt.end,
                "overlap_seconds": 0.0,
                "iou": 0.0,
                "classification": "FALSE_NEGATIVE",
                "confidence": 0.0,
                "primary_cue": "None",
            })

    tp = len(matched_gt_indices)
    fn = len(missed_gt)
    # Extra predictions that had 0 overlap with any GT
    fp = total_pred - len(matched_pred_indices)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    mean_iou = sum(matched_ious) / len(matched_ious) if matched_ious else 0.0
    sorted_ious = sorted(matched_ious)
    median_iou = (
        sorted_ious[len(sorted_ious) // 2] if sorted_ious else 0.0
    )

    total_gt_duration = sum(gt.duration for gt in gt_episodes)
    total_covered_duration = sum(
        min(gt.duration, overlap_durations_per_gt[i]) for i, gt in enumerate(gt_episodes)
    )
    temporal_coverage_pct = (
        (total_covered_duration / total_gt_duration) * 100.0 if total_gt_duration > 0 else 0.0
    )

    return {
        "gt_episodes_count": total_gt,
        "pred_episodes_count": total_pred,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mean_iou": round(mean_iou, 4),
        "median_iou": round(median_iou, 4),
        "temporal_coverage_pct": round(temporal_coverage_pct, 2),
        "detailed_comparisons": detailed_comparisons,
    }


def evaluate_window_predictions(
    timestamps: List[float],
    probabilities: List[float],
    gt_episodes: List[GroundTruthEpisode],
    fog_threshold: float = 0.60,
    window_duration: float = 1.0,
) -> Dict[str, Any]:
    """Window-level evaluation matching rolling 1.0s window intervals to ground truth.

    A rolling window ending at timestamp t covers [t - window_duration, t].
    Ground truth label = 1 if the window midpoint (t - window_duration/2) falls inside
    any ground truth FoG episode, else 0.
    Prediction = 1 if posterior probability >= fog_threshold, else 0.
    """
    tp = 0
    tn = 0
    fp = 0
    fn = 0

    total_windows = len(timestamps)
    if total_windows == 0:
        return {
            "total_windows": 0,
            "tp": 0,
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "specificity": 0.0,
            "accuracy": 0.0,
            "fog_prevalence_pct": 0.0,
        }

    for t, p in zip(timestamps, probabilities):
        t_mid = float(t) - (window_duration / 2.0)
        gt_label = 0
        for ep in gt_episodes:
            if ep.start <= t_mid <= ep.end:
                gt_label = 1
                break

        pred_label = 1 if float(p) >= fog_threshold else 0

        if gt_label == 1 and pred_label == 1:
            tp += 1
        elif gt_label == 0 and pred_label == 0:
            tn += 1
        elif gt_label == 0 and pred_label == 1:
            fp += 1
        elif gt_label == 1 and pred_label == 0:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    accuracy = (tp + tn) / total_windows if total_windows > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    prevalence = (tp + fn) / total_windows * 100.0 if total_windows > 0 else 0.0

    return {
        "total_windows": total_windows,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "specificity": round(specificity, 4),
        "accuracy": round(accuracy, 4),
        "fog_prevalence_pct": round(prevalence, 2),
    }


def evaluate_1s_binned_windows(
    gt_episodes: List[GroundTruthEpisode],
    pred_episodes: List[Dict[str, Any]],
    trial_duration: float = 120.0,
) -> Dict[str, Any]:
    """1-second binned temporal window evaluation across the trial duration.

    Evaluates 1.0s discrete windows [t, t+1) for t = 0..int(trial_duration)-1.
    GT = 1 if midpoint (t + 0.5) is inside any GT FoG interval, else 0.
    Pred = 1 if midpoint (t + 0.5) is inside any Predicted FoG episode, else 0.
    """
    fog_preds = [p for p in pred_episodes if p.get("type") == "FoG"]

    tp = 0
    tn = 0
    fp = 0
    fn = 0

    n_windows = int(trial_duration)
    for t in range(n_windows):
        mid = t + 0.5
        gt_val = 1 if any(ep.start <= mid <= ep.end for ep in gt_episodes) else 0
        pred_val = 1 if any(p["start"] <= mid <= p["end"] for p in fog_preds) else 0

        if gt_val == 1 and pred_val == 1:
            tp += 1
        elif gt_val == 0 and pred_val == 0:
            tn += 1
        elif gt_val == 0 and pred_val == 1:
            fp += 1
        elif gt_val == 1 and pred_val == 0:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    accuracy = (tp + tn) / n_windows if n_windows > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    prevalence = (tp + fn) / n_windows * 100.0 if n_windows > 0 else 0.0

    return {
        "total_windows": n_windows,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "specificity": round(specificity, 4),
        "accuracy": round(accuracy, 4),
        "fog_prevalence_pct": round(prevalence, 2),
    }
