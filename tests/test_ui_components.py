"""Unit tests for UI components and Results Hierarchy presentation."""

from typing import Any, Dict
import pytest
from src.ui.components import (
    render_borderline_section,
    render_explanation_section,
    render_fog_episodes_section,
    render_results_dashboard,
    render_summary_metrics,
    render_technical_details_section,
    render_timeline_visualization,
)


@pytest.fixture
def sample_episodes():
    return [
        {
            "start": 0.008,
            "end": 0.408,
            "confidence": 0.012,
            "type": "Normal",
            "primary_cue": "accel_rms",
            "data_mode": "real",
        },
        {
            "start": 0.408,
            "end": 65.908,
            "confidence": 0.9599,
            "type": "FoG",
            "primary_cue": "stride_width",
            "data_mode": "real",
        },
        {
            "start": 65.908,
            "end": 66.208,
            "confidence": 0.505,
            "type": "Borderline",
            "primary_cue": "gyro_x_var",
            "data_mode": "real",
        },
        {
            "start": 66.208,
            "end": 119.908,
            "confidence": 0.9654,
            "type": "FoG",
            "primary_cue": "left_ankle_velocity",
            "data_mode": "real",
        },
    ]


@pytest.fixture
def sample_results(sample_episodes):
    return {
        "success": True,
        "status": "COMPLETE",
        "session_id": "test-session-123",
        "episode_count": 4,
        "summary": {
            "total_duration": 119.9,
            "fog_episodes": 2,
            "borderline_episodes": 1,
            "normal_episodes": 1,
        },
        "episodes": sample_episodes,
        "explanation": {
            "status": "SUCCESS",
            "provider": "deterministic_rule",
            "narrative": "The patient experienced 2 Freezing of Gait (FoG) episodes.",
            "latency_ms": 12,
            "cached": False,
            "clinical_disclaimer": "NeuroGait is an objective research tool.",
        },
        "diagnostics": {
            "fog_windows": 1161,
            "normal_windows": 25,
            "fused_rows": 1190,
            "frames_processed": 3598,
            "imu_samples_received": 15360,
        },
        "execution_target": "LOCAL_DETERMINISTIC_ENGINE",
    }


def test_render_summary_metrics_calculations(sample_episodes):
    """Verify summary metrics calculation from non-overlapping episodes."""
    summary = {}
    # Executed without raising exception
    render_summary_metrics(summary, sample_episodes)


def test_render_timeline_visualization(sample_episodes):
    """Verify timeline visualization rendering."""
    render_timeline_visualization(sample_episodes)


def test_render_fog_episodes_section(sample_episodes):
    """Verify FoG episode section rendering and empty state."""
    # With FoG episodes
    render_fog_episodes_section(sample_episodes)

    # Empty FoG state
    no_fog = [e for e in sample_episodes if e["type"] != "FoG"]
    render_fog_episodes_section(no_fog)


def test_render_borderline_section(sample_episodes):
    """Verify Borderline section rendering and empty state handling."""
    # With Borderline period
    render_borderline_section(sample_episodes)

    # Empty Borderline state
    no_borderline = [e for e in sample_episodes if e["type"] != "Borderline"]
    render_borderline_section(no_borderline)


def test_render_explanation_section():
    """Verify AI explanation rendering and unavailable fallback."""
    # Valid deterministic explanation
    valid_exp = {
        "status": "SUCCESS",
        "provider": "deterministic_rule",
        "narrative": "Patient gait trial narrative.",
        "clinical_disclaimer": "Clinical safety disclosure text.",
    }
    render_explanation_section(valid_exp)

    # Unavailable explanation
    render_explanation_section(None)
    render_explanation_section({"status": "UNAVAILABLE", "reason": "No response"})


def test_render_technical_details_section(sample_results):
    """Verify technical details rendering with raw model windows label."""
    render_technical_details_section(sample_results)


def test_render_results_dashboard(sample_results):
    """Verify full 6-stage Results Hierarchy dashboard rendering."""
    render_results_dashboard(sample_results)
