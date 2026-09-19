"""Unit tests for NeuroGait Streamlit UI API Client."""

from unittest.mock import MagicMock, patch
import pytest
import requests

from src.ui.api_client import NeuroGaitAPIClient


@pytest.fixture
def client():
    return NeuroGaitAPIClient(base_url="https://api.test.neurogait.com", timeout=5.0)


# 1. Client-Side Input Validation Tests
def test_validate_inputs_valid(client):
    valid, err = client.validate_inputs(
        video_filename="PDFE01_1.mp4",
        imu_filename="SUB01_1.txt",
        video_size_bytes=20_000_000,
        imu_size_bytes=500_000,
    )
    assert valid is True
    assert err is None


def test_validate_inputs_invalid_extension(client):
    # Invalid video extension
    valid, err = client.validate_inputs(
        video_filename="trial.avi",
        imu_filename="SUB01_1.txt",
        video_size_bytes=1000,
        imu_size_bytes=1000,
    )
    assert valid is False
    assert "Unsupported video extension" in err

    # Invalid IMU extension
    valid, err = client.validate_inputs(
        video_filename="trial.mp4",
        imu_filename="SUB01_1.wav",
        video_size_bytes=1000,
        imu_size_bytes=1000,
    )
    assert valid is False
    assert "Unsupported IMU extension" in err


def test_validate_inputs_oversized(client):
    # Video > 500 MB
    valid, err = client.validate_inputs(
        video_filename="trial.mp4",
        imu_filename="SUB01_1.txt",
        video_size_bytes=600 * 1024 * 1024,
        imu_size_bytes=1000,
    )
    assert valid is False
    assert "Video size exceeds limit" in err

    # IMU > 50 MB
    valid, err = client.validate_inputs(
        video_filename="trial.mp4",
        imu_filename="SUB01_1.txt",
        video_size_bytes=1000,
        imu_size_bytes=60 * 1024 * 1024,
    )
    assert valid is False
    assert "IMU size exceeds limit" in err


def test_validate_inputs_unsafe_characters(client):
    valid, err = client.validate_inputs(
        video_filename="../passwd.mp4",
        imu_filename="SUB01_1.txt",
        video_size_bytes=1000,
        imu_size_bytes=1000,
    )
    assert valid is False
    assert "Invalid video filename" in err


# 2. API Method Tests with Mocked Network Calls
@patch("requests.get")
def test_check_health_success(mock_get, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"status": "HEALTHY"}'
    mock_resp.json.return_value = {"status": "HEALTHY", "service": "neurogait-control-plane"}
    mock_get.return_value = mock_resp

    res = client.check_health()
    assert res["success"] is True
    assert res["status_code"] == 200
    assert res["data"]["status"] == "HEALTHY"


@patch("requests.post")
def test_create_session_success(mock_post, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"session_id": "abc-123", "status": "CREATED"}'
    mock_resp.json.return_value = {
        "session_id": "abc-123",
        "status": "CREATED",
        "upload_urls": {"video": "https://s3/v", "imu": "https://s3/i"},
        "s3_keys": {"video": "inputs/abc-123/video.mp4"},
    }
    mock_post.return_value = mock_resp

    res = client.create_session("video.mp4", "imu.txt", 1000, 500)
    assert res["success"] is True
    assert res["session_id"] == "abc-123"
    assert res["status"] == "CREATED"
    assert "video" in res["upload_urls"]


@patch("requests.put")
def test_upload_artifact_success(mock_put, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_put.return_value = mock_resp

    res = client.upload_artifact("https://s3/presigned-url", b"fake binary data", "video/mp4")
    assert res["success"] is True
    assert res["status_code"] == 200
    mock_put.assert_called_once_with(
        "https://s3/presigned-url",
        data=b"fake binary data",
        headers={"Content-Type": "video/mp4"},
        timeout=120.0,
    )


@patch("requests.post")
def test_confirm_upload_success(mock_post, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"session_id": "abc-123", "status": "UPLOADED"}'
    mock_resp.json.return_value = {"session_id": "abc-123", "status": "UPLOADED"}
    mock_post.return_value = mock_resp

    res = client.confirm_upload("abc-123")
    assert res["success"] is True
    assert res["status"] == "UPLOADED"


@patch("requests.post")
def test_start_inference_success(mock_post, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 202
    mock_resp.content = b'{"session_id": "abc-123", "status": "PROCESSING", "task_arn": "arn:ecs:task"}'
    mock_resp.json.return_value = {"session_id": "abc-123", "status": "PROCESSING", "task_arn": "arn:ecs:task"}
    mock_post.return_value = mock_resp

    res = client.start_inference("abc-123")
    assert res["success"] is True
    assert res["status"] == "PROCESSING"
    assert res["task_arn"] == "arn:ecs:task"


@patch("requests.post")
def test_start_inference_409_conflict_handling(mock_post, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 409
    mock_resp.content = b'{"error": "InvalidStateTransition", "message": "Upload must be verified"}'
    mock_resp.json.return_value = {
        "error": "InvalidStateTransition",
        "message": "Session is in state 'CREATED'. Upload must be verified and established as 'UPLOADED' before starting inference.",
        "current_state": "CREATED",
    }
    mock_post.return_value = mock_resp

    res = client.start_inference("abc-123")
    assert res["success"] is False
    assert res["status_code"] == 409
    assert res["error"] == "InvalidStateTransition"
    assert "UPLOADED" in res["message"]


@patch("requests.get")
def test_get_status_complete(mock_get, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"status": "COMPLETE", "episode_count": 48}'
    mock_resp.json.return_value = {
        "status": "COMPLETE",
        "episode_count": 48,
        "summary": {"fog_episodes": 21, "borderline_episodes": 21, "normal_episodes": 6},
        "episodes": [{"start": 0.0, "end": 1.0, "type": "FoG", "confidence": 0.9, "primary_cue": "accel_rms", "data_mode": "real"}],
        "explanation": {"provider": "deterministic_rule", "status": "SUCCESS", "narrative": "Text"},
    }
    mock_get.return_value = mock_resp

    res = client.get_status("abc-123")
    assert res["success"] is True
    assert res["status"] == "COMPLETE"
    assert res["episode_count"] == 48
    assert res["explanation"]["provider"] == "deterministic_rule"


# 3. Network Error Containment Tests
@patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused"))
def test_connection_error_containment(mock_get, client):
    res = client.check_health()
    assert res["success"] is False
    assert res["error"] == "ConnectionError"
    assert "Unable to reach NeuroGait backend" in res["message"]


@patch("requests.post", side_effect=requests.exceptions.Timeout("Read timed out"))
def test_timeout_error_containment(mock_post, client):
    res = client.create_session("v.mp4", "i.txt", 100, 100)
    assert res["success"] is False
    assert res["error"] == "ConnectionError"
    assert "Network error" in res["message"]
