"""Tests for NeuroGait Gate 4 Explanation Provider Subsystem."""

import copy
import json
from unittest.mock import MagicMock, patch
import pytest

from src.explanation.base import CLINICAL_SAFETY_DISCLAIMER, ExplanationResult, ProviderStatus
from src.explanation.bedrock_provider import BedrockExplanationProvider
from src.explanation.orchestrator import generate_explanation, get_provider
from src.explanation.rule_provider import DeterministicRuleExplanationProvider
from src.control_plane.lambda_handler import handle_get_status


@pytest.fixture
def sample_episodes():
    """Sample canonical Phase 1 episode list."""
    return [
        {
            "start": 0.408,
            "end": 35.708,
            "confidence": 0.9774,
            "type": "FoG",
            "primary_cue": "accel_rms",
            "data_mode": "real",
        },
        {
            "start": 35.008,
            "end": 36.008,
            "confidence": 0.4072,
            "type": "Borderline",
            "primary_cue": "gyro_x_var",
            "data_mode": "real",
        },
        {
            "start": 35.108,
            "end": 36.608,
            "confidence": 0.1294,
            "type": "Normal",
            "primary_cue": "gyro_x_var",
            "data_mode": "real",
        },
    ]


# 1. Deterministic Rule Provider Tests
def test_deterministic_rule_provider_success(sample_episodes):
    provider = DeterministicRuleExplanationProvider()
    assert provider.is_available() is True
    assert provider.provider_name == "deterministic_rule"

    res = provider.generate(sample_episodes)
    assert res.status == ProviderStatus.SUCCESS.value
    assert res.provider == "deterministic_rule"
    assert res.narrative is not None
    assert "Freezing of Gait (FoG)" in res.narrative
    assert "Borderline" in res.narrative
    assert "Normal" in res.narrative
    assert res.summary["total_episodes"] == 3
    assert res.summary["fog_episodes"] == 1
    assert res.summary["borderline_episodes"] == 1
    assert res.summary["normal_episodes"] == 1
    assert res.summary["dominant_primary_cue"] == "accel_rms"


def test_deterministic_rule_provider_reproducibility(sample_episodes):
    provider = DeterministicRuleExplanationProvider()
    res1 = provider.generate(sample_episodes)
    res2 = provider.generate(sample_episodes)
    assert res1.narrative == res2.narrative
    assert res1.summary == res2.summary


def test_clinical_safety_guardrails(sample_episodes):
    provider = DeterministicRuleExplanationProvider()
    res = provider.generate(sample_episodes)

    # Must include standard disclaimer
    assert res.clinical_disclaimer == CLINICAL_SAFETY_DISCLAIMER
    assert "DISCLAIMER" in res.clinical_disclaimer
    assert "does NOT constitute a medical diagnosis" in res.clinical_disclaimer

    # Narrative text must not make clinical diagnosis claims
    lower_text = res.narrative.lower()
    assert "diagnosed with" not in lower_text
    assert "diagnosis:" not in lower_text
    assert "patient has parkinson" not in lower_text

    # Primary cue must be qualified as algorithmic/statistical, not clinical etiology
    assert "do not imply clinical causation" in res.narrative or "statistical variance" in res.clinical_disclaimer


# 2. Bedrock Provider Tests
def test_bedrock_provider_unauthorized_graceful_handling(sample_episodes):
    mock_client = MagicMock()
    mock_client.get_foundation_model_availability.return_value = {
        "modelId": "amazon.nova-micro-v1:0",
        "authorizationStatus": "NOT_AUTHORIZED",
    }

    provider = BedrockExplanationProvider(model_id="amazon.nova-micro-v1:0")
    provider._bedrock_client = mock_client

    authorized, reason = provider.check_authorization()
    assert authorized is False
    assert "NOT_AUTHORIZED" in reason

    res = provider.generate(sample_episodes)
    assert res.status == ProviderStatus.UNAVAILABLE.value
    assert res.provider == "bedrock"
    assert res.narrative is None
    assert "NOT_AUTHORIZED" in res.reason


# 3. Orchestrator & Fallback Tests
def test_orchestrator_auto_fallback_to_deterministic(sample_episodes):
    # Mock bedrock as unauthorized
    with patch("src.explanation.bedrock_provider.boto3.client") as mock_boto:
        mock_bedrock = MagicMock()
        mock_bedrock.get_foundation_model_availability.return_value = {"authorizationStatus": "NOT_AUTHORIZED"}
        mock_boto.return_value = mock_bedrock

        res = generate_explanation(sample_episodes, preferred_provider="auto")
        assert res.status == ProviderStatus.SUCCESS.value
        assert res.provider == "deterministic_rule"
        assert res.narrative is not None


def test_orchestrator_preferred_bedrock_records_fallback_reason(sample_episodes):
    with patch("src.explanation.bedrock_provider.boto3.client") as mock_boto:
        mock_bedrock = MagicMock()
        mock_bedrock.get_foundation_model_availability.return_value = {"authorizationStatus": "NOT_AUTHORIZED"}
        mock_boto.return_value = mock_bedrock

        res = generate_explanation(sample_episodes, preferred_provider="bedrock")
        assert res.status == ProviderStatus.SUCCESS.value
        assert res.provider == "deterministic_rule"
        assert res.reason is not None
        assert "Fallback from Bedrock" in res.reason


def test_orchestrator_unsupported_provider():
    res = generate_explanation([], preferred_provider="invalid_provider")
    assert res.status == ProviderStatus.FAILED.value
    assert "Unsupported provider" in res.reason


# 4. Result Integrity & Immutability
def test_explanation_generation_preserves_canonical_json_immutability(sample_episodes):
    episodes_copy = copy.deepcopy(sample_episodes)
    _ = generate_explanation(sample_episodes, preferred_provider="auto")

    # Assert exact bit-for-bit equality of input episodes
    assert sample_episodes == episodes_copy


def test_explanation_failure_leaves_ml_result_intact():
    episodes = [
        {"start": 1.0, "end": 2.0, "confidence": 0.8, "type": "FoG", "primary_cue": "accel_rms", "data_mode": "real"}
    ]

    with patch("src.explanation.rule_provider.DeterministicRuleExplanationProvider.generate", side_effect=RuntimeError("Simulated provider crash")):
        res = generate_explanation(episodes, preferred_provider="deterministic")
        assert res.status == ProviderStatus.FAILED.value
        assert "Simulated provider crash" in res.reason
        assert res.narrative is None


# 5. Lambda Control Plane Status & S3 Idempotency Caching
def test_lambda_control_plane_status_with_explanation_caching(sample_episodes):
    session_id = "12345678-1234-1234-1234-123456789abc"
    predictions_json = json.dumps(sample_episodes).encode("utf-8")

    # Case A: Explanation not yet in S3 -> generated and stored
    mock_s3 = MagicMock()
    # First get_object returns predictions.json, second raises NoSuchKey for explanation.json
    def mock_get_object(Bucket, Key):
        if Key.endswith("predictions.json"):
            return {"Body": MagicMock(read=lambda: predictions_json)}
        elif Key.endswith("explanation.json"):
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        raise RuntimeError(f"Unexpected key: {Key}")

    mock_s3.get_object.side_effect = mock_get_object

    mock_store_a = MagicMock()
    from src.state.models import SessionRecord, SessionState
    mock_store_a.get_session.return_value = SessionRecord(
        session_id=session_id,
        state=SessionState.PROCESSING.value,
    )

    with patch("src.control_plane.lambda_handler.get_s3_client", return_value=mock_s3), \
         patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store_a):
        res = handle_get_status({"session_id": session_id})
        assert res["statusCode"] == 200
        body = json.loads(res["body"])
        assert body["status"] == "COMPLETE"
        assert body["episode_count"] == 3
        assert body["explanation"]["status"] == "SUCCESS"
        assert body["explanation"]["provider"] == "deterministic_rule"
        assert body["explanation"]["cached"] is False
        # Verify put_object was called to persist explanation.json
        mock_s3.put_object.assert_called_once()
        put_kwargs = mock_s3.put_object.call_args[1]
        assert put_kwargs["Key"] == f"outputs/{session_id}/explanation.json"

    # Case B: Explanation already in S3 -> loaded from cache (idempotency)
    cached_explanation = {
        "provider": "deterministic_rule",
        "status": "SUCCESS",
        "narrative": "Cached narrative text",
        "summary": {"total_episodes": 3},
        "latency_ms": 0.5,
    }
    mock_s3_cached = MagicMock()
    def mock_get_object_cached(Bucket, Key):
        if Key.endswith("predictions.json"):
            return {"Body": MagicMock(read=lambda: predictions_json)}
        elif Key.endswith("explanation.json"):
            return {"Body": MagicMock(read=lambda: json.dumps(cached_explanation).encode("utf-8"))}
        raise RuntimeError(f"Unexpected key: {Key}")

    mock_s3_cached.get_object.side_effect = mock_get_object_cached

    mock_store_b = MagicMock()
    mock_store_b.get_session.return_value = SessionRecord(
        session_id=session_id,
        state=SessionState.COMPLETE.value,
        episode_count=3,
    )

    with patch("src.control_plane.lambda_handler.get_s3_client", return_value=mock_s3_cached), \
         patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store_b):
        res = handle_get_status({"session_id": session_id})
        assert res["statusCode"] == 200
        body = json.loads(res["body"])
        assert body["status"] == "COMPLETE"
        assert body["explanation"]["narrative"] == "Cached narrative text"
        assert body["explanation"]["cached"] is True
        mock_s3_cached.put_object.assert_not_called()
