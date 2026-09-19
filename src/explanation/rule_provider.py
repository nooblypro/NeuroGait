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
from typing import Any, Dict, List

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

    def generate(self, episodes: List[Dict[str, Any]]) -> ExplanationResult:
        """Generate structured narrative from canonical Phase 1 episode list."""
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

        # 1. Compute summary metrics
        total_episodes = len(episodes)
        fog_episodes = [e for e in episodes if e.get("type") == "FoG"]
        borderline_episodes = [e for e in episodes if e.get("type") == "Borderline"]
        normal_episodes = [e for e in episodes if e.get("type") == "Normal"]

        trial_start = min(e["start"] for e in episodes)
        trial_end = max(e["end"] for e in episodes)
        total_duration = max(0.001, trial_end - trial_start)

        fog_duration = sum(max(0.0, e["end"] - e["start"]) for e in fog_episodes)
        fog_burden_pct = min(100.0, (fog_duration / total_duration) * 100.0)

        # Primary cue frequency for FoG episodes
        fog_cues = [e.get("primary_cue") for e in fog_episodes if e.get("primary_cue")]
        cue_counts = Counter(fog_cues)
        dominant_cue = cue_counts.most_common(1)[0][0] if cue_counts else "none"

        mean_fog_conf = (
            sum(e.get("confidence", 0.0) for e in fog_episodes) / len(fog_episodes)
            if fog_episodes
            else 0.0
        )

        # 2. Build structured deterministic narrative
        narrative_paragraphs = []

        # Paragraph 1: Overview
        p1 = (
            f"Gait trial recorded over {total_duration:.2f} seconds contained {total_episodes} identified "
            f"interval(s). Automated multimodal analysis classified {len(fog_episodes)} Freezing of Gait (FoG) "
            f"episode(s) (posterior probability >= 0.60), {len(borderline_episodes)} Borderline episode(s) "
            f"(0.40 <= probability < 0.60), and {len(normal_episodes)} Normal gait segment(s) (probability < 0.40)."
        )
        narrative_paragraphs.append(p1)

        # Paragraph 2: FoG Characterization
        if fog_episodes:
            longest_fog = max(fog_episodes, key=lambda e: e["end"] - e["start"])
            longest_fog_dur = longest_fog["end"] - longest_fog["start"]
            p2 = (
                f"Total FoG duration was {fog_duration:.2f} seconds, representing an estimated FoG trial burden of "
                f"{fog_burden_pct:.1f}%. Mean FoG classification confidence was {mean_fog_conf:.4f}. The longest "
                f"uninterrupted freezing episode spanned from {longest_fog['start']:.3f}s to {longest_fog['end']:.3f}s "
                f"({longest_fog_dur:.2f}s duration, confidence {longest_fog.get('confidence', 0.0):.4f})."
            )
        else:
            p2 = "No confirmed Freezing of Gait (FoG) episodes were detected during this recording interval."
        narrative_paragraphs.append(p2)

        # Paragraph 3: Primary Cue / Feature Variance Attribution
        if fog_cues:
            cue_summary_parts = [
                f"{cue} ({count} episode{'s' if count > 1 else ''} - {FEATURE_DESCRIPTIONS.get(cue, 'kinematic/inertial deviation')})"
                for cue, count in cue_counts.most_common()
            ]
            p3 = (
                f"Algorithmic feature attribution identified '{dominant_cue}' as the most frequent primary cue "
                f"during freezing intervals. Statistical feature deviations observed across FoG episodes: "
                f"{'; '.join(cue_summary_parts)}. Note: Primary cues reflect the mathematical feature demonstrating "
                f"the maximum standardized deviation relative to the subject baseline and do not imply clinical causation."
            )
            narrative_paragraphs.append(p3)

        # Paragraph 4: Borderline Transitions
        if borderline_episodes:
            p4 = (
                f"A total of {len(borderline_episodes)} Borderline transition interval(s) were flagged between "
                f"0.40 and 0.60 probability. These intervals represent ambiguous kinematic or inertial micro-arrests "
                f"prior to or following overt freezing episodes."
            )
            narrative_paragraphs.append(p4)

        full_narrative = "\n\n".join(narrative_paragraphs)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        summary = {
            "total_episodes": total_episodes,
            "fog_episodes": len(fog_episodes),
            "borderline_episodes": len(borderline_episodes),
            "normal_episodes": len(normal_episodes),
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
