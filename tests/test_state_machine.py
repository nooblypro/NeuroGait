"""Tests for NeuroGait Gate 5 DynamoDB State Machine and Pipeline Lifecycle."""

import json
from unittest.mock import MagicMock, patch
import pytest

from src.control_plane.lambda_handler import (
    handle_confirm_upload,
    handle_create_session,
    handle_get_status,
    handle_start_inference,
)
from src.state.dynamo_store import DynamoSessionStore
from src.state.models import (
    LEGAL_TRANSITIONS,
    SessionRecord,
    SessionState,
    StateTransitionError,
    is_legal_transition,
)


# 1. State Model and Legal Transition Matrix Tests
def test_all_legal_transitions():
    assert is_legal_transition(SessionState.CREATED, SessionState.UPLOADING) is True
    assert is_legal_transition(SessionState.CREATED, SessionState.UPLOADED) is True
    assert is_legal_transition(SessionState.UPLOADING, SessionState.UPLOADED) is True
    assert is_legal_transition(SessionState.UPLOADED, SessionState.PROCESSING) is True
    assert is_legal_transition(SessionState.PROCESSING, SessionState.ML_COMPLETE) is True
    assert is_legal_transition(SessionState.ML_COMPLETE, SessionState.NARRATIVE_GENERATING) is True
    assert is_legal_transition(SessionState.NARRATIVE_GENERATING, SessionState.COMPLETE) is True


def test_illegal_transitions_rejected():
    # Direct jump from CREATED to PROCESSING is strictly invalid
    assert is_legal_transition(SessionState.CREATED, SessionState.PROCESSING) is False
    assert is_legal_transition(SessionState.CREATED, SessionState.COMPLETE) is False
    assert is_legal_transition(SessionState.UPLOADING, SessionState.PROCESSING) is False

    # Cannot move backwards from COMPLETE
    assert is_legal_transition(SessionState.COMPLETE, SessionState.PROCESSING) is False
    assert is_legal_transition(SessionState.COMPLETE, SessionState.CREATED) is False
    assert is_legal_transition(SessionState.COMPLETE, SessionState.ML_COMPLETE) is False

    # Failure states are terminal
    assert is_legal_transition(SessionState.PROCESSING_FAILED, SessionState.PROCESSING) is False


def test_no_large_artifacts_in_dynamo_record():
    record = SessionRecord(
        session_id="test-session-123",
        state=SessionState.CREATED.value,
        video_filename="test.mp4",
        imu_filename="test.txt",
        video_size_bytes=1000,
        imu_size_bytes=500,
        video_s3_key="inputs/test-session-123/video.mp4",
        imu_s3_key="inputs/test-session-123/imu.txt",
        predictions_s3_key="outputs/test-session-123/predictions.json",
        explanation_s3_key="outputs/test-session-123/explanation.json",
    )
    item = record.to_item()
    assert "video_data" not in item
    assert "imu_data" not in item
    assert "episodes" not in item
    assert "predictions" not in item
    assert item["session_id"] == "test-session-123"
    assert item["state"] == "CREATED"
    assert item["video_s3_key"] == "inputs/test-session-123/video.mp4"


# 2. DynamoSessionStore Unit Tests with Mock Table
def test_dynamo_store_create_and_transition():
    mock_table = MagicMock()
    store = DynamoSessionStore(table_name="test-table")
    store._table = mock_table

    rec = SessionRecord(session_id="s-1", state=SessionState.CREATED.value)
    store.create_session(rec)
    mock_table.put_item.assert_called_once()
    assert mock_table.put_item.call_args[1]["ConditionExpression"] == "attribute_not_exists(session_id)"

    # Transition to UPLOADED
    mock_table.update_item.return_value = {
        "Attributes": {
            "session_id": "s-1",
            "state": "UPLOADED",
            "created_at": "2026-09-18T00:00:00Z",
            "updated_at": "2026-09-18T00:01:00Z",
        }
    }
    updated = store.transition_state(
        session_id="s-1",
        from_state=SessionState.CREATED,
        to_state=SessionState.UPLOADED,
    )
    assert updated.state == "UPLOADED"
    update_kwargs = mock_table.update_item.call_args[1]
    assert update_kwargs["ConditionExpression"] == "attribute_exists(session_id) AND #st = :from_state"


def test_dynamo_store_rejects_illegal_transition():
    store = DynamoSessionStore(table_name="test-table")
    with pytest.raises(StateTransitionError) as exc_info:
        store.transition_state("s-1", SessionState.CREATED, SessionState.PROCESSING)
    assert "Illegal transition" in str(exc_info.value)


# 3. Control Plane End-to-End State Machine Routing Tests
def test_create_session_persists_in_created_state():
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://s3/presigned"
    mock_store = MagicMock()

    with patch("src.control_plane.lambda_handler.get_s3_client", return_value=mock_s3), \
         patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store):

        res = handle_create_session({
            "video_filename": "PDFE01_1.mp4",
            "imu_filename": "SUB01_1.txt",
            "video_size_bytes": 1024,
            "imu_size_bytes": 512,
        })
        assert res["statusCode"] == 200
        body = json.loads(res["body"])
        assert body["status"] == "CREATED"
        mock_store.create_session.assert_called_once()
        created_rec = mock_store.create_session.call_args[0][0]
        assert created_rec.state == "CREATED"


def test_start_inference_rejects_created_state_with_409():
    mock_store = MagicMock()
    mock_store.get_session.return_value = SessionRecord(
        session_id="12345678-1234-1234-1234-123456789abc",
        state=SessionState.CREATED.value,
    )

    with patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store):
        res = handle_start_inference({"session_id": "12345678-1234-1234-1234-123456789abc"})
        assert res["statusCode"] == 409
        body = json.loads(res["body"])
        assert body["error"] == "InvalidStateTransition"
        assert "Upload must be verified and established as 'UPLOADED'" in body["message"]


def test_confirm_upload_transitions_to_uploaded():
    mock_s3 = MagicMock()
    mock_store = MagicMock()
    mock_store.get_session.return_value = SessionRecord(
        session_id="12345678-1234-1234-1234-123456789abc",
        state=SessionState.CREATED.value,
        video_s3_key="inputs/12345678-1234-1234-1234-123456789abc/video.mp4",
        imu_s3_key="inputs/12345678-1234-1234-1234-123456789abc/imu.txt",
    )
    mock_store.transition_state.return_value = SessionRecord(
        session_id="12345678-1234-1234-1234-123456789abc",
        state=SessionState.UPLOADED.value,
    )

    with patch("src.control_plane.lambda_handler.get_s3_client", return_value=mock_s3), \
         patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store):

        res = handle_confirm_upload({"session_id": "12345678-1234-1234-1234-123456789abc"})
        assert res["statusCode"] == 200
        body = json.loads(res["body"])
        assert body["status"] == "UPLOADED"
        mock_store.transition_state.assert_called_once_with(
            session_id="12345678-1234-1234-1234-123456789abc",
            from_state=SessionState.CREATED,
            to_state=SessionState.UPLOADED,
        )


def test_start_inference_accepts_uploaded_state():
    mock_store = MagicMock()
    mock_store.get_session.return_value = SessionRecord(
        session_id="12345678-1234-1234-1234-123456789abc",
        state=SessionState.UPLOADED.value,
        video_s3_key="inputs/12345678-1234-1234-1234-123456789abc/video.mp4",
        imu_s3_key="inputs/12345678-1234-1234-1234-123456789abc/imu.txt",
    )
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://s3/presigned"
    mock_ecs = MagicMock()
    mock_ecs.run_task.return_value = {"tasks": [{"taskArn": "arn:aws:ecs:task:123"}]}

    with patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store), \
         patch("src.control_plane.lambda_handler.get_s3_client", return_value=mock_s3), \
         patch("src.control_plane.lambda_handler.get_ecs_client", return_value=mock_ecs):

        res = handle_start_inference({"session_id": "12345678-1234-1234-1234-123456789abc"})
        assert res["statusCode"] == 202
        body = json.loads(res["body"])
        assert body["status"] == "PROCESSING"
        assert body["task_arn"] == "arn:aws:ecs:task:123"
        mock_store.transition_state.assert_called_once()
        call_kwargs = mock_store.transition_state.call_args[1]
        assert call_kwargs["from_state"] == SessionState.UPLOADED
        assert call_kwargs["to_state"] == SessionState.PROCESSING


def test_get_status_complete_idempotent_read():
    mock_store = MagicMock()
    mock_store.get_session.return_value = SessionRecord(
        session_id="12345678-1234-1234-1234-123456789abc",
        state=SessionState.COMPLETE.value,
        episode_count=48,
        summary={"fog_episodes": 21, "borderline_episodes": 21, "normal_episodes": 6},
    )
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = lambda Bucket, Key: {
        "Body": MagicMock(read=lambda: json.dumps([{"start": 0.0, "end": 1.0, "type": "FoG", "confidence": 0.9, "primary_cue": "accel_rms", "data_mode": "real"}]).encode("utf-8"))
    }

    with patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store), \
         patch("src.control_plane.lambda_handler.get_s3_client", return_value=mock_s3):

        res = handle_get_status({"session_id": "12345678-1234-1234-1234-123456789abc"})
        assert res["statusCode"] == 200
        body = json.loads(res["body"])
        assert body["status"] == "COMPLETE"
        # Zero state transitions performed on COMPLETE session
        mock_store.transition_state.assert_not_called()
