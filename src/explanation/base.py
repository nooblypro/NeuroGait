"""Base definitions and abstract class for NeuroGait Explanation Providers.

Defines the standard data contract, clinical safety disclaimers, and
abstract interface for narrative generation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Standardized Clinical Non-Diagnostic Disclaimer
CLINICAL_SAFETY_DISCLAIMER = (
    "DISCLAIMER: This explanation is algorithmically generated based on automated "
    "kinematic and inertial feature measurements. It is intended solely for research "
    "and assistive clinical visualization and does NOT constitute a medical diagnosis, "
    "prognosis, or clinical treatment recommendation. Feature attributions (primary cues) "
    "reflect statistical variance relative to patient baseline, not clinical etiology."
)


class ProviderStatus(str, Enum):
    """Execution status of an explanation provider."""
    SUCCESS = "SUCCESS"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


@dataclass
class ExplanationResult:
    """Standardized result envelope for generated explanations."""
    provider: str
    status: str
    narrative: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None
    model_id: Optional[str] = None
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latency_ms: float = 0.0
    cached: bool = False
    clinical_disclaimer: str = CLINICAL_SAFETY_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary."""
        return asdict(self)


class ExplanationProvider(ABC):
    """Abstract base class for all NeuroGait explanation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return unique provider identifier."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this provider is configured and available for inference."""
        pass

    @abstractmethod
    def generate(self, episodes: List[Dict[str, Any]]) -> ExplanationResult:
        """Generate narrative explanation from canonical Phase 1 episode list."""
        pass
