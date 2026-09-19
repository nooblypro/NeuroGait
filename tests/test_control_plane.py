"""Unit tests for the NeuroGait Control Plane Lambda Handler."""

import json
from unittest.mock import MagicMock, patch
import pytest

from src.control_plane.lambda_handler import (
    build_response,
    handle_confirm_upload,
    handle_create_session,
    handle_get_status,
    handle_health,
    handle_start_inference,
    lambda_handler,
    validate_upload_request,
)
from src.state.models import SessionRecord, SessionState


def test_validate_upload_request_valid():
    payload = {
        "video_filename": "PDFE01_1.mp4",
        "imu_filename": "SUB01_1.txt",
        "video_size_bytes": 20_000_000,
        "imu_size_bytes": 200_000,
    }
    valid, err = validate_upload_request(payload)
    assert valid is True
    assert err is None


def test_validate_upload_request_invalid_extension():
    valid, err = validate_upload_request({
        "video_filename": "trial.avi",
        "imu_filename": "imu.txt",
    })
    assert valid is False
    assert "Unsupported video extension" in err

    valid, err = validate_upload_request({
        "video_filename": "trial.mp4",
        "imu_filename": "imu.wav",
    })
    assert valid is False
    assert "Unsupported IMU extension" in err


def test_validate_upload_request_oversized():
    valid, err = validate_upload_request({
        "video_filename": "trial.mp4",
        "imu_filename": "imu.txt",
        "video_size_bytes": 600 * 1024 * 1024,
    })
    assert valid is False
    assert "exceeds maximum allowed limit" in err

    valid, err = validate_upload_request({
        "video_filename": "trial.mp4",
        "imu_filename": "imu.txt",
        "imu_size_bytes": 60 * 1024 * 1024,
    })
    assert valid is False
    assert "exceeds maximum allowed limit" in err


def test_validate_upload_request_unsafe_characters():
    valid, err = validate_upload_request({
        "video_filename": "../../../etc/passwd.mp4",
        "imu_filename": "imu.txt",
    })
    assert valid is False
    assert "Invalid 'video_filename'" in err


def test_handle_health():
    res = handle_health()
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["status"] == "HEALTHY"
    assert "ecs_cluster" in body
    assert "s3_bucket" in body
    assert "dynamodb_table" in body


@patch("src.control_plane.lambda_handler.get_session_store")
@patch("src.control_plane.lambda_handler.get_s3_client")
def test_handle_create_session(mock_get_s3, mock_get_store):
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://s3.ap-south-1.amazonaws.com/test-url"
    mock_get_s3.return_value = mock_s3

    mock_store = MagicMock()
    mock_get_store.return_value = mock_store

    payload = {
        "video_filename": "PDFE01_1.mp4",
        "imu_filename": "SUB01_1.txt",
        "video_size_bytes": 15_000_000,
        "imu_size_bytes": 100_000,
    }
    res = handle_create_session(payload)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert "session_id" in body
    assert body["status"] == "CREATED"
    assert "video" in body["upload_urls"]
    assert "imu" in body["upload_urls"]
    assert body["s3_keys"]["video"].startswith("inputs/")
    assert body["s3_keys"]["output"].startswith("outputs/")
    mock_store.create_session.assert_called_once()


@patch("src.control_plane.lambda_handler.get_session_store")
def test_handle_start_inference_session_not_found(mock_get_store):
    mock_store = MagicMock()
    mock_store.get_session.return_value = None
    mock_get_store.return_value = mock_store

    payload = {"session_id": "12345678-1234-1234-1234-123456789abc"}
    res = handle_start_inference(payload)
    assert res["statusCode"] == 404
    body = json.loads(res["body"])
    assert body["error"] == "SessionNotFound"


@patch("src.control_plane.lambda_handler.get_session_store")
@patch("src.control_plane.lambda_handler.get_s3_client")
@patch("src.control_plane.lambda_handler.get_ecs_client")
def test_handle_start_inference_success(mock_get_ecs, mock_get_s3, mock_get_store):
    mock_store = MagicMock()
    mock_store.get_session.return_value = SessionRecord(
        session_id="12345678-1234-1234-1234-123456789abc",
        state=SessionState.UPLOADED.value,
        video_s3_key="inputs/12345678-1234-1234-1234-123456789abc/video.mp4",
        imu_s3_key="inputs/12345678-1234-1234-1234-123456789abc/imu.txt",
    )
    mock_get_store.return_value = mock_store

    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://presigned.s3.url"
    mock_get_s3.return_value = mock_s3

    mock_ecs = MagicMock()
    mock_ecs.run_task.return_value = {
        "tasks": [{"taskArn": "arn:aws:ecs:ap-south-1:123456789012:task/test-task"}]
    }
    mock_get_ecs.return_value = mock_ecs

    payload = {"session_id": "12345678-1234-1234-1234-123456789abc"}
    res = handle_start_inference(payload)
    assert res["statusCode"] == 202
    body = json.loads(res["body"])
    assert body["status"] == "PROCESSING"
    assert body["task_arn"] == "arn:aws:ecs:ap-south-1:123456789012:task/test-task"


@patch("src.control_plane.lambda_handler.get_session_store")
@patch("src.control_plane.lambda_handler.get_s3_client")
def test_handle_get_status_completed(mock_get_s3, mock_get_store):
    mock_store = MagicMock()
    mock_store.get_session.return_value = SessionRecord(
        session_id="12345678-1234-1234-1234-123456789abc",
        state=SessionState.COMPLETE.value,
        episode_count=1,
        summary={"fog_episodes": 1, "borderline_episodes": 0, "normal_episodes": 0},
    )
    mock_get_store.return_value = mock_store

    mock_s3 = MagicMock()
    canonical_output = [
        {
            "start": 0.0,
            "end": 2.0,
            "confidence": 0.95,
            "type": "FoG",
            "primary_cue": "accel_rms",
            "data_mode": "real"
        }
    ]
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: json.dumps(canonical_output).encode("utf-8"))
    }
    mock_get_s3.return_value = mock_s3

    res = handle_get_status({"session_id": "12345678-1234-1234-1234-123456789abc"})
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["status"] == "COMPLETE"
    assert body["episode_count"] == 1
    assert body["episodes"][0]["type"] == "FoG"


def test_lambda_handler_routing():
    # 1. Health
    res = lambda_handler({"rawPath": "/health", "requestContext": {"http": {"method": "GET"}}}, None)
    assert res["statusCode"] == 200

    # 2. Unknown route
    res = lambda_handler({"rawPath": "/unknown", "requestContext": {"http": {"method": "GET"}}}, None)
    assert res["statusCode"] == 404

    # 3. Malformed JSON
    res = lambda_handler({
        "rawPath": "/sessions",
        "requestContext": {"http": {"method": "POST"}},
        "body": "not json"
    }, None)
    assert res["statusCode"] == 400
