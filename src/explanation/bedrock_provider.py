"""Amazon Bedrock Explanation Provider implementation for NeuroGait.

Connects to Amazon Bedrock Runtime in AWS (default region: ap-south-1)
to generate clinical explanatory narratives using foundation models.

Enforces:
- Explicit availability and authorization checking.
- Clean UNAVAILABLE reporting when foundation models are not authorized.
- No repeated runtime calls when authorization is known to be missing.
- Clinical safety guardrails in prompting.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

try:
    import boto3
except ImportError:
    boto3 = None  # type: ignore

from .base import CLINICAL_SAFETY_DISCLAIMER, ExplanationProvider, ExplanationResult, ProviderStatus

logger = logging.getLogger(__name__)

DEFAULT_REGION = os.environ.get("AWS_REGION", "ap-south-1")
DEFAULT_BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")


class BedrockExplanationProvider(ExplanationProvider):
    """Generates explanations via Amazon Bedrock with explicit authorization checks."""

    def __init__(
        self,
        region_name: str = DEFAULT_REGION,
        model_id: str = DEFAULT_BEDROCK_MODEL,
        boto3_session: Optional[Any] = None,
    ):
        self.region_name = region_name
        self.model_id = model_id
        self._session = boto3_session
        self._bedrock_client = None
        self._runtime_client = None
        self._auth_checked = False
        self._is_authorized = False
        self._auth_reason: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "bedrock"

    def _get_bedrock_client(self):
        if self._bedrock_client is None:
            if boto3 is None:
                return None
            try:
                if self._session:
                    self._bedrock_client = self._session.client("bedrock", region_name=self.region_name)
                else:
                    self._bedrock_client = boto3.client("bedrock", region_name=self.region_name)
            except Exception as e:
                logger.warning(f"Failed to instantiate Bedrock client: {e}")
                self._bedrock_client = None
        return self._bedrock_client

    def _get_runtime_client(self):
        if self._runtime_client is None:
            if boto3 is None:
                return None
            try:
                if self._session:
                    self._runtime_client = self._session.client("bedrock-runtime", region_name=self.region_name)
                else:
                    self._runtime_client = boto3.client("bedrock-runtime", region_name=self.region_name)
            except Exception as e:
                logger.warning(f"Failed to instantiate Bedrock Runtime client: {e}")
                self._runtime_client = None
        return self._runtime_client

    def check_authorization(self) -> tuple[bool, str]:
        """Verify model authorization without making repeated runtime calls."""
        if self._auth_checked:
            return self._is_authorized, self._auth_reason or ""

        client = self._get_bedrock_client()
        if client is None:
            self._auth_checked = True
            self._is_authorized = False
            self._auth_reason = "boto3/bedrock client unavailable"
            return False, self._auth_reason

        try:
            # Check foundation model availability in Bedrock
            res = client.get_foundation_model_availability(modelId=self.model_id)
            auth_status = res.get("authorizationStatus")
            if auth_status == "AUTHORIZED":
                self._is_authorized = True
                self._auth_reason = "Model authorized and available"
            else:
                self._is_authorized = False
                self._auth_reason = f"Bedrock model access not granted ({auth_status or 'NOT_AUTHORIZED'})"
        except Exception as e:
            err_msg = str(e)
            if "NOT_AUTHORIZED" in err_msg or "ValidationException" in err_msg or "Operation not allowed" in err_msg:
                self._is_authorized = False
                self._auth_reason = "Bedrock model access not granted (NOT_AUTHORIZED)"
            else:
                self._is_authorized = False
                self._auth_reason = f"Bedrock availability check failed: {err_msg}"

        self._auth_checked = True
        return self._is_authorized, self._auth_reason

    def is_available(self) -> bool:
        """Return True only if Bedrock is reachable and model authorization is granted."""
        authorized, _ = self.check_authorization()
        return authorized

    def generate(self, episodes: List[Dict[str, Any]]) -> ExplanationResult:
        """Attempt Bedrock narrative generation or return explicit UNAVAILABLE status."""
        start_time = time.perf_counter()

        authorized, reason = self.check_authorization()
        if not authorized:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ExplanationResult(
                provider=self.provider_name,
                status=ProviderStatus.UNAVAILABLE.value,
                narrative=None,
                reason=reason,
                model_id=self.model_id,
                latency_ms=round(elapsed_ms, 2),
                clinical_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
            )

        runtime = self._get_runtime_client()
        if runtime is None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ExplanationResult(
                provider=self.provider_name,
                status=ProviderStatus.UNAVAILABLE.value,
                narrative=None,
                reason="Bedrock Runtime client unavailable",
                model_id=self.model_id,
                latency_ms=round(elapsed_ms, 2),
                clinical_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
            )

        # Structure sanitized summary for prompt
        fog_count = sum(1 for e in episodes if e.get("type") == "FoG")
        borderline_count = sum(1 for e in episodes if e.get("type") == "Borderline")
        normal_count = sum(1 for e in episodes if e.get("type") == "Normal")

        prompt = (
            f"You are a clinical motion analysis assistant. Summarize the following gait session results.\n"
            f"Do not provide a medical diagnosis. Do not describe primary cues as clinical causes.\n"
            f"Total episodes: {len(episodes)} (FoG: {fog_count}, Borderline: {borderline_count}, Normal: {normal_count}).\n"
            f"Data: {json.dumps(episodes[:10])}\n"
        )

        try:
            response = runtime.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
            )
            output_text = response["output"]["message"]["content"][0]["text"]
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ExplanationResult(
                provider=self.provider_name,
                status=ProviderStatus.SUCCESS.value,
                narrative=output_text.strip(),
                summary={
                    "total_episodes": len(episodes),
                    "fog_episodes": fog_count,
                    "borderline_episodes": borderline_count,
                    "normal_episodes": normal_count,
                },
                model_id=self.model_id,
                latency_ms=round(elapsed_ms, 2),
                clinical_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(f"Bedrock runtime invocation error: {e}")
            return ExplanationResult(
                provider=self.provider_name,
                status=ProviderStatus.FAILED.value,
                narrative=None,
                reason=f"Bedrock invocation failed: {str(e)}",
                model_id=self.model_id,
                latency_ms=round(elapsed_ms, 2),
                clinical_disclaimer=CLINICAL_SAFETY_DISCLAIMER,
            )
