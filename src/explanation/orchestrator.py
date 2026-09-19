"""Explanation Orchestrator and Factory for NeuroGait.

Coordinates provider selection, authorization discovery, graceful fallback,
and safety isolation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import CLINICAL_SAFETY_DISCLAIMER, ExplanationResult, ProviderStatus
from .bedrock_provider import BedrockExplanationProvider
from .rule_provider import DeterministicRuleExplanationProvider

logger = logging.getLogger(__name__)


def get_provider(provider_name: str = "auto", **kwargs) -> Any:
    """Instantiate requested provider by name."""
    if provider_name.lower() == "bedrock":
        return BedrockExplanationProvider(**kwargs)
    elif provider_name.lower() in ("deterministic", "deterministic_rule", "rule"):
        return DeterministicRuleExplanationProvider()
    elif provider_name.lower() == "auto":
        # Check if Bedrock is available
        bedrock = BedrockExplanationProvider(**kwargs)
        if bedrock.is_available():
            return bedrock
        return DeterministicRuleExplanationProvider()
    else:
        raise ValueError(f"Unknown explanation provider: '{provider_name}'")


def generate_explanation(
    episodes: List[Dict[str, Any]],
    preferred_provider: str = "auto",
    bedrock_kwargs: Optional[Dict[str, Any]] = None,
) -> ExplanationResult:
    """Generate clinical narrative explanation with explicit fallback and error containment.

    Guarantees:
    - Never throws uncaught exception that would abort the caller.
    - If Bedrock is requested/attempted but unauthorized, records the exact Bedrock status
      and uses DeterministicRuleExplanationProvider.
    - Never mutates the input episodes list.
    """
    kwargs = bedrock_kwargs or {}

    try:
        if preferred_provider in ("auto", "bedrock"):
            bedrock = BedrockExplanationProvider(**kwargs)
            authorized, reason = bedrock.check_authorization()

            if authorized:
                result = bedrock.generate(episodes)
                if result.status == ProviderStatus.SUCCESS.value:
                    return result
                logger.warning(f"Bedrock generation failed ({result.reason}), falling back to deterministic provider.")

            # Fallback to deterministic rule provider
            rule_prov = DeterministicRuleExplanationProvider()
            res = rule_prov.generate(episodes)

            # Enrich explanation with provider fallback metadata
            if preferred_provider == "bedrock" and not authorized:
                res.reason = f"Fallback from Bedrock: {reason}"
            return res

        elif preferred_provider in ("deterministic", "deterministic_rule", "rule"):
            return DeterministicRuleExplanationProvider().generate(episodes)

        else:
            return ExplanationResult(
                provider=preferred_provider,
                status=ProviderStatus.FAILED.value,
                narrative=None,
                reason=f"Unsupported provider: '{preferred_provider}'",
                clinical_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
            )

    except Exception as e:
        logger.error(f"Unexpected explanation generation failure: {e}", exc_info=True)
        return ExplanationResult(
            provider=preferred_provider,
            status=ProviderStatus.FAILED.value,
            narrative=None,
            reason=f"Explanation generation exception: {str(e)}",
            clinical_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
        )
