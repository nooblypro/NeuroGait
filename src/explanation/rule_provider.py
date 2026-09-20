"""Deterministic Rule-Based Explanation Provider for NeuroGait.

Constructs transparent, deterministic explanatory clinical narratives
strictly grounded in the canonical Phase 1 JSON output and validated feature
definitions.

Enforces Safety Guardrails:
- Does NOT provide a medical diagnosis or disease staging.
- Does NOT label primary cues as clinical causes or pathological etiologies.
- Does NOT invent unobserved symptoms, patient history, or clinical hypotheses.
- Clearly distinguishes automated algorithmic signals from clinical interpretation.
- Completely deterministic and reproducible across identical inputs.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Any, Dict, List, Optional

from .base import CLINICAL_SAFETY_DISCLAIMER, ExplanationProvider, ExplanationResult, ProviderStatus

logger = logging.getLogger(__name__)

FEATURE_DESCRIPTIONS = {
    "left_ankle_velocity": "decreased left ankle displacement rate",
    "right_ankle_velocity": "decreased right ankle displacement rate",
    "left_knee_angle": "left knee joint angle reduction during flexion",
    "right_knee_angle": "right knee joint angle reduction during flexion",
    "stride_width": "abnormal base-of-support narrowing / stride width variation",
    "accel_rms": "diminished anteroposterior linear acceleration root-mean-square",
    "gyro_x_var": "suppressed mediolateral angular velocity variance (trunk/pelvis turning dynamics)",
    "gyro_z_var": "suppressed superior-inferior angular velocity variance (rotational axial sway)",
}


class DeterministicRuleExplanationProvider(ExplanationProvider):
    """Produces structured, transparent explanatory narratives using deterministic domain rules."""

    @property
    def provider_name(self) -> str:
        return "deterministic_rule"

    def is_available(self) -> bool:
        """Always available as a deterministic local provider."""
        return True

    def generate(
        self, episodes: List[Dict[str, Any]], stats: Optional[Dict[str, Any]] = None
    ) -> ExplanationResult:
        """Generate structured narrative from canonical Phase 1 episode list or precomputed stats."""
        start_time = time.perf_counter()

        if not episodes:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ExplanationResult(
                provider=self.provider_name,
                status=ProviderStatus.SUCCESS.value,
                narrative="No gait episodes recorded in the input trial.",
                summary={"total_episodes": 0},
                latency_ms=round(elapsed_ms, 2),
                clinical_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
            )

        # 1. Compute summary metrics from input non-overlapping intervals or stats
        if stats:
            total_episodes = stats.get("totalIntervals", len(episodes))
            fog_episodes = [e for e in episodes if e.get("type") == "FoG"]
            borderline_count = stats.get("borderlineCount", len([e for e in episodes if e.get("type") == "Borderline"]))
            normal_count = stats.get("normalCount", len([e for e in episodes if e.get("type") == "Normal"]))
            dominant_cue = stats.get("dominantCue", "none")
            mean_fog_conf = stats.get("meanFogConfidence", 0.0)
            fog_duration = stats.get("fogDuration", 0.0)
            fog_burden_pct = stats.get("fogBurdenPct", 0.0)
            total_duration = stats.get("totalDuration", 0.0)
            cue_counts = Counter([e.get("primary_cue") for e in fog_episodes if e.get("primary_cue") and e.get("primary_cue") != "None"])
        else:
            total_episodes = len(episodes)
            fog_episodes = [e for e in episodes if e.get("type") == "FoG"]
            borderline_episodes = [e for e in episodes if e.get("type") == "Borderline"]
            normal_episodes = [e for e in episodes if e.get("type") == "Normal"]
            borderline_count = len(borderline_episodes)
            normal_count = len(normal_episodes)

            trial_start = min((e["start"] for e in episodes), default=0.0)
            trial_end = max((e["end"] for e in episodes), default=0.0)
            total_duration = max(0.001, trial_end - trial_start)

            fog_duration = sum(max(0.0, e["end"] - e["start"]) for e in fog_episodes)
            fog_burden_pct = min(100.0, (fog_duration / total_duration) * 100.0) if total_duration > 0 else 0.0

            fog_cues = [e.get("primary_cue") for e in fog_episodes if e.get("primary_cue") and e.get("primary_cue") != "None"]
            cue_counts = Counter(fog_cues)
            dominant_cue = cue_counts.most_common(1)[0][0] if cue_counts else "none"

            mean_fog_conf = (
                sum(e.get("confidence", 0.0) for e in fog_episodes) / len(fog_episodes)
                if fog_episodes
                else 0.0
            )

        fog_count = len(fog_episodes)

        # 2. Build structured deterministic narrative from aggregated intervals
        if fog_count == 0:
            p1 = (
                f"The recording contained {total_episodes} non-overlapping classified intervals. "
                f"The model classified 0 intervals as Freezing of Gait (FoG), {borderline_count} as Borderline, "
                f"and {normal_count} as Normal. No FoG-classified intervals were detected in this recording."
            )
        elif fog_count == 1:
            fog_ep = fog_episodes[0]
            conf_pct = fog_ep.get("confidence", 0.0) * 100.0
            cue = fog_ep.get("primary_cue") or dominant_cue
            p1 = (
                f"The recording contained {total_episodes} non-overlapping classified intervals. "
                f"The model classified 1 interval as Freezing of Gait (FoG), {borderline_count} as Borderline, "
                f"and {normal_count} as Normal. The FoG-classified interval occurred from {fog_ep['start']:.2f}s "
                f"to {fog_ep['end']:.2f}s with a classification confidence of {conf_pct:.1f}%. "
                f"The dominant model-derived cue for the FoG interval was {cue}."
            )
        else:
            longest_fog = max(fog_episodes, key=lambda e: e["end"] - e["start"])
            longest_dur = longest_fog["end"] - longest_fog["start"]
            longest_conf_pct = longest_fog.get("confidence", 0.0) * 100.0
            p1 = (
                f"The recording contained {total_episodes} non-overlapping classified intervals. "
                f"The model classified {fog_count} intervals as Freezing of Gait (FoG), {borderline_count} as Borderline, "
                f"and {normal_count} as Normal. Total FoG duration was {fog_duration:.2f} seconds ({fog_burden_pct:.1f}% burden). "
                f"The longest FoG interval spanned from {longest_fog['start']:.2f}s to {longest_fog['end']:.2f}s "
                f"({longest_dur:.2f}s duration, confidence {longest_conf_pct:.1f}%). "
                f"The dominant model-derived cue across FoG intervals was {dominant_cue}."
            )

        safety_stmt = (
            "These model-derived feature cues represent statistical associations within the model output "
            "and do not imply clinical causation or diagnosis."
        )

        full_narrative = f"{p1}\n\n{safety_stmt}"
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        summary = {
            "total_episodes": total_episodes,
            "fog_episodes": fog_count,
            "borderline_episodes": borderline_count,
            "normal_episodes": normal_count,
            "trial_duration_seconds": round(total_duration, 3),
            "fog_duration_seconds": round(fog_duration, 3),
            "fog_burden_percentage": round(fog_burden_pct, 2),
            "mean_fog_confidence": round(mean_fog_conf, 4),
            "dominant_primary_cue": dominant_cue,
            "primary_cue_distribution": dict(cue_counts),
        }

        return ExplanationResult(
            provider=self.provider_name,
            status=ProviderStatus.SUCCESS.value,
            narrative=full_narrative,
            summary=summary,
            latency_ms=round(elapsed_ms, 2),
            clinical_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
        )
