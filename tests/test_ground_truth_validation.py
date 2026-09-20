"""Focused validation tests for Ground-Truth Parsing, IoU, and Temporal Matching.

Covers:
1. Ground-truth interval parsing ([55.797-58.507], multi-episode, empty, malformed).
2. PDFEinfo.csv / xls recording mapping and status resolution.
3. Interval overlap and IoU edge cases and invariants.
4. Prediction/ground-truth matching and TP/FP/FN calculations.
5. Empty-FoG recordings (PDFE09_1, PDFE10_1).
6. Multi-FoG recordings (PDFE14_1, PDFE01_1).
7. Boundary conditions (exact matches, zero overlap, touching boundaries, subset intervals).
"""

import pytest
from pathlib import Path

from src.evaluation.ground_truth import (
    GroundTruthEpisode,
    RecordingAnnotation,
    compute_interval_overlap_and_iou,
    evaluate_temporal_episodes,
    evaluate_window_predictions,
    parse_pdfe_info,
    parse_raw_interval_string,
)


def test_independent_check_pdfe31_session_1():
    """Independently verify PDFE31 Session 1 annotation from dataset."""
    info_path = Path("data/raw/PDFEinfo.csv")
    recordings = parse_pdfe_info(info_path)

    assert "PDFE31_1" in recordings
    rec = recordings["PDFE31_1"]
    assert rec.status == "VALID"
    assert rec.subject_id == "PDFE31"
    assert rec.session_id == "1"
    assert rec.raw_interval_string == "[55.797-58.507]"
    assert rec.raw_duration_string == "2.72"
    assert rec.raw_episodes_count_string == "1"

    # Verify parsed episodes
    assert len(rec.fog_episodes) == 1
    ep = rec.fog_episodes[0]
    assert ep.start == 55.797
    assert ep.end == 58.507
    assert ep.duration == pytest.approx(2.710, abs=1e-3)


def test_empty_fog_recordings():
    """Verify empty FoG recordings (annotated as 0) parse to empty list."""
    info_path = Path("data/raw/PDFEinfo.csv")
    recordings = parse_pdfe_info(info_path)

    # PDFE09_1 has '0'
    assert "PDFE09_1" in recordings
    rec9 = recordings["PDFE09_1"]
    assert rec9.status == "VALID"
    assert rec9.raw_interval_string == "0"
    assert len(rec9.fog_episodes) == 0

    # PDFE10_1 has '0'
    assert "PDFE10_1" in recordings
    rec10 = recordings["PDFE10_1"]
    assert rec10.status == "VALID"
    assert rec10.raw_interval_string == "0"
    assert len(rec10.fog_episodes) == 0


def test_multi_fog_recordings():
    """Verify multi-FoG recordings (e.g. PDFE14_1 with 15 episodes)."""
    info_path = Path("data/raw/PDFEinfo.csv")
    recordings = parse_pdfe_info(info_path)

    assert "PDFE14_1" in recordings
    rec14 = recordings["PDFE14_1"]
    assert rec14.status == "VALID"
    assert rec14.raw_episodes_count_string == "15"
    assert len(rec14.fog_episodes) == 15
    assert rec14.fog_episodes[0].start == 9.847
    assert rec14.fog_episodes[0].end == 11.288
    assert rec14.fog_episodes[-1].start == 115.284
    assert rec14.fog_episodes[-1].end == 120.0


def test_missing_annotation_and_not_conducted():
    """Verify recordings with dashes '-' are correctly marked as MISSING_ANNOTATION or NOT CONDUCTED."""
    info_path = Path("data/raw/PDFEinfo.csv")
    recordings = parse_pdfe_info(info_path)

    # PDFE04 had sessions # = 3, but session 2 and 3 had '-'
    assert "PDFE04_2" in recordings
    assert recordings["PDFE04_2"].status == "MISSING ANNOTATION"
    assert len(recordings["PDFE04_2"].fog_episodes) == 0

    # PDFE02 had sessions # = 1, so session 2 was NOT CONDUCTED
    assert "PDFE02_2" in recordings
    assert recordings["PDFE02_2"].status == "NOT CONDUCTED"


def test_compute_interval_overlap_and_iou_exact_match():
    """Identical intervals must produce IoU = 1.0 and overlap = duration."""
    overlap, iou = compute_interval_overlap_and_iou(10.0, 15.0, 10.0, 15.0)
    assert overlap == 5.0
    assert iou == 1.0


def test_compute_interval_overlap_and_iou_disjoint():
    """Completely disjoint intervals must produce IoU = 0.0 and overlap = 0.0."""
    overlap, iou = compute_interval_overlap_and_iou(0.0, 5.0, 6.0, 10.0)
    assert overlap == 0.0
    assert iou == 0.0


def test_compute_interval_overlap_and_iou_touching():
    """Touching intervals [0, 5] and [5, 10] have 0 overlap."""
    overlap, iou = compute_interval_overlap_and_iou(0.0, 5.0, 5.0, 10.0)
    assert overlap == 0.0
    assert iou == 0.0


def test_compute_interval_overlap_and_iou_partial():
    """Partial overlap: [0, 10] and [5, 15] -> inter=5, union=15, iou=1/3."""
    overlap, iou = compute_interval_overlap_and_iou(0.0, 10.0, 5.0, 15.0)
    assert overlap == 5.0
    assert iou == pytest.approx(5.0 / 15.0, abs=1e-4)


def test_evaluate_temporal_episodes_perfect_match():
    """When predictions exactly match GT, TP=1, FP=0, FN=0, IoU=1.0."""
    gt = [GroundTruthEpisode("test", "sub", "1", 10.0, 20.0)]
    preds = [{"start": 10.0, "end": 20.0, "type": "FoG", "confidence": 0.95}]
    res = evaluate_temporal_episodes(gt, preds)

    assert res["tp"] == 1
    assert res["fp"] == 0
    assert res["fn"] == 0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0
    assert res["mean_iou"] == 1.0
    assert res["temporal_coverage_pct"] == 100.0


def test_evaluate_temporal_episodes_false_positive():
    """Predicted FoG when GT has no FoG yields TP=0, FP=1, FN=0."""
    gt = []
    preds = [{"start": 10.0, "end": 20.0, "type": "FoG", "confidence": 0.95}]
    res = evaluate_temporal_episodes(gt, preds)

    assert res["tp"] == 0
    assert res["fp"] == 1
    assert res["fn"] == 0
    assert res["precision"] == 0.0
    assert res["f1"] == 0.0


def test_evaluate_temporal_episodes_false_negative():
    """GT has FoG but model predicts only Normal -> TP=0, FP=0, FN=1."""
    gt = [GroundTruthEpisode("test", "sub", "1", 10.0, 20.0)]
    preds = [{"start": 10.0, "end": 20.0, "type": "Normal", "confidence": 0.15}]
    res = evaluate_temporal_episodes(gt, preds)

    assert res["tp"] == 0
    assert res["fp"] == 0
    assert res["fn"] == 1
    assert res["recall"] == 0.0
    assert res["f1"] == 0.0


def test_evaluate_window_predictions_confusion_matrix():
    """Verify window-level confusion matrix formulas."""
    gt = [GroundTruthEpisode("test", "sub", "1", 5.0, 10.0)]
    # Window ends at t: [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    # Midpoints: t - 0.5 -> 0.5, 1.5, 2.5, 3.5, 4.5, 5.5 (GT=1), 6.5 (GT=1), 7.5 (GT=1), 8.5 (GT=1), 9.5 (GT=1)
    timestamps = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    # Predictions: let window 6, 7 be predicted FoG (0.80), 8 be 0.30 (FN), 2 be 0.70 (FP)
    probs = [0.1, 0.7, 0.1, 0.2, 0.3, 0.8, 0.8, 0.3, 0.8, 0.8]

    res = evaluate_window_predictions(timestamps, probs, gt, fog_threshold=0.60)
    assert res["total_windows"] == 10
    # GT windows: t=6.0 (mid 5.5), 7.0 (mid 6.5), 8.0 (mid 7.5), 9.0 (mid 8.5), 10.0 (mid 9.5) -> 5 windows
    # Predicted FoG windows (prob >= 0.60): t=2.0, 6.0, 7.0, 9.0, 10.0 -> 5 windows
    # TP: 6.0, 7.0, 9.0, 10.0 -> 4
    # FN: 8.0 -> 1
    # FP: 2.0 -> 1
    # TN: 1.0, 3.0, 4.0, 5.0 -> 4
    assert res["tp"] == 4
    assert res["fn"] == 1
    assert res["fp"] == 1
    assert res["tn"] == 4
    assert res["precision"] == 4.0 / 5.0
    assert res["recall"] == 4.0 / 5.0
    assert res["specificity"] == 4.0 / 5.0
    assert res["accuracy"] == 8.0 / 10.0
