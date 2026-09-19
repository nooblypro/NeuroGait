"""HTTP API client for NeuroGait Cloud Control Plane.

Communicates with the deployed API Gateway endpoint to orchestrate:
- Health checking
- Session initialization & presigned URL retrieval
- Direct S3 binary artifact upload via presigned PUT URLs
- Upload confirmation (establishing UPLOADED state)
- Inference dispatch (transitioning UPLOADED -> PROCESSING)
- State & result polling (retrieving canonical episodes & S3 explanation)

Security & Safety:
- No AWS credentials or secret keys are accepted, logged, or processed.
- Configurable via NEUROGAIT_API_URL environment variable.
- Safe structured error responses without raw stack traces.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

DEFAULT_API_URL = os.environ.get(
    "NEUROGAIT_API_URL",
    "https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com",
).rstrip("/")

SAFE_FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
ALLOWED_VIDEO_EXTENSIONS = {".mp4"}
ALLOWED_IMU_EXTENSIONS = {".txt", ".csv"}
MAX_VIDEO_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_IMU_SIZE_BYTES = 50 * 1024 * 1024      # 50 MB


class APIClientError(Exception):
    """Base API client error containing status code and structured message."""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "ClientError"):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class NeuroGaitAPIClient:
    """Client for NeuroGait API Gateway backend."""

    def __init__(self, base_url: str = DEFAULT_API_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """Check backend service connectivity and configuration."""
        url = f"{self.base_url}/health"
        try:
            resp = requests.get(url, timeout=self.timeout)
            data = resp.json() if resp.content else {}
            return {
                "success": resp.status_code == 200,
                "status_code": resp.status_code,
                "data": data,
            }
        except requests.exceptions.RequestException as e:
            logger.warning(f"Health check connection error: {e}")
            return {
                "success": False,
                "status_code": 0,
                "error": "ConnectionError",
                "message": f"Unable to reach NeuroGait backend at {self.base_url}. Please verify network connectivity.",
            }

    def validate_inputs(
        self,
        video_filename: str,
        imu_filename: str,
        video_size_bytes: int,
        imu_size_bytes: int,
    ) -> Tuple[bool, Optional[str]]:
        """Validate upload parameters before sending to API."""
        if not video_filename or not SAFE_FILENAME_REGEX.match(video_filename):
            return False, "Invalid video filename. Use alphanumeric characters, dashes, and underscores."
        if not imu_filename or not SAFE_FILENAME_REGEX.match(imu_filename):
            return False, "Invalid IMU filename. Use alphanumeric characters, dashes, and underscores."

        _, v_ext = os.path.splitext(video_filename.lower())
        _, i_ext = os.path.splitext(imu_filename.lower())

        if v_ext not in ALLOWED_VIDEO_EXTENSIONS:
            return False, f"Unsupported video extension '{v_ext}'. Allowed: {sorted(ALLOWED_VIDEO_EXTENSIONS)}"
        if i_ext not in ALLOWED_IMU_EXTENSIONS:
            return False, f"Unsupported IMU extension '{i_ext}'. Allowed: {sorted(ALLOWED_IMU_EXTENSIONS)}"

        if video_size_bytes <= 0 or video_size_bytes > MAX_VIDEO_SIZE_BYTES:
            return False, f"Video size exceeds limit (max {MAX_VIDEO_SIZE_BYTES // (1024*1024)} MB)."
        if imu_size_bytes <= 0 or imu_size_bytes > MAX_IMU_SIZE_BYTES:
            return False, f"IMU size exceeds limit (max {MAX_IMU_SIZE_BYTES // (1024*1024)} MB)."

        return True, None

    def create_session(
        self,
        video_filename: str,
        imu_filename: str,
        video_size_bytes: int,
        imu_size_bytes: int,
    ) -> Dict[str, Any]:
        """Create session in CREATED state and obtain presigned upload URLs."""
        valid, err = self.validate_inputs(
            video_filename, imu_filename, video_size_bytes, imu_size_bytes
        )
        if not valid:
            return {"success": False, "status_code": 400, "error": "ValidationError", "message": err}

        url = f"{self.base_url}/sessions"
        payload = {
            "video_filename": video_filename,
            "imu_filename": imu_filename,
            "video_size_bytes": video_size_bytes,
            "imu_size_bytes": imu_size_bytes,
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            data = resp.json() if resp.content else {}
            if resp.status_code == 200:
                return {
                    "success": True,
                    "status_code": 200,
                    "session_id": data.get("session_id"),
                    "status": data.get("status", "CREATED"),
                    "upload_urls": data.get("upload_urls", {}),
                    "s3_keys": data.get("s3_keys", {}),
                }
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": data.get("error", "SessionCreationFailed"),
                "message": data.get("message", "Failed to initialize session on backend."),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating session: {e}")
            return {
                "success": False,
                "status_code": 0,
                "error": "ConnectionError",
                "message": "Network error while contacting NeuroGait control plane.",
            }

    def upload_artifact(
        self,
        presigned_url: str,
        data_bytes: bytes,
        content_type: str,
    ) -> Dict[str, Any]:
        """Upload raw binary artifact directly to S3 via presigned PUT URL."""
        headers = {"Content-Type": content_type}
        try:
            resp = requests.put(
                presigned_url,
                data=data_bytes,
                headers=headers,
                timeout=120.0,  # generous timeout for large video uploads
            )
            if resp.status_code in (200, 204):
                return {"success": True, "status_code": resp.status_code}
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": "S3UploadFailed",
                "message": f"S3 upload rejected with HTTP {resp.status_code}.",
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading artifact to S3: {e}")
            return {
                "success": False,
                "status_code": 0,
                "error": "UploadConnectionError",
                "message": "Network error during S3 artifact upload.",
            }

    def confirm_upload(self, session_id: str) -> Dict[str, Any]:
        """Confirm uploaded artifacts in S3 and transition session to UPLOADED."""
        url = f"{self.base_url}/sessions/confirm-upload"
        try:
            resp = requests.post(url, json={"session_id": session_id}, timeout=self.timeout)
            data = resp.json() if resp.content else {}
            if resp.status_code == 200:
                return {
                    "success": True,
                    "status_code": 200,
                    "session_id": session_id,
                    "status": data.get("status", "UPLOADED"),
                    "message": data.get("message"),
                }
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": data.get("error", "UploadConfirmationFailed"),
                "message": data.get("message", "Failed to confirm upload artifacts."),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error confirming upload for {session_id}: {e}")
            return {
                "success": False,
                "status_code": 0,
                "error": "ConnectionError",
                "message": "Network error while confirming upload.",
            }

    def start_inference(self, session_id: str) -> Dict[str, Any]:
        """Dispatch ECS Fargate ML task for an UPLOADED session."""
        url = f"{self.base_url}/inference/start"
        try:
            resp = requests.post(url, json={"session_id": session_id}, timeout=self.timeout)
            data = resp.json() if resp.content else {}
            if resp.status_code in (200, 202):
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "session_id": session_id,
                    "status": data.get("status", "PROCESSING"),
                    "task_arn": data.get("task_arn"),
                    "s3_output_key": data.get("s3_output_key"),
                }
            elif resp.status_code == 409:
                return {
                    "success": False,
                    "status_code": 409,
                    "error": data.get("error", "InvalidStateTransition"),
                    "message": data.get("message", "Session is not ready for inference."),
                    "current_state": data.get("current_state"),
                }
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": data.get("error", "InferenceStartFailed"),
                "message": data.get("message", "Failed to start inference task."),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error starting inference for {session_id}: {e}")
            return {
                "success": False,
                "status_code": 0,
                "error": "ConnectionError",
                "message": "Network error while initiating inference.",
            }

    def get_status(self, session_id: str) -> Dict[str, Any]:
        """Query session status and retrieve canonical predictions & explanation when COMPLETE."""
        url = f"{self.base_url}/inference/status"
        try:
            resp = requests.get(url, params={"session_id": session_id}, timeout=self.timeout)
            data = resp.json() if resp.content else {}
            if resp.status_code == 200:
                return {
                    "success": True,
                    "status_code": 200,
                    "session_id": session_id,
                    "status": data.get("status"),
                    "episode_count": data.get("episode_count"),
                    "summary": data.get("summary"),
                    "episodes": data.get("episodes", []),
                    "explanation": data.get("explanation"),
                    "s3_output_key": data.get("s3_output_key"),
                    "s3_explanation_key": data.get("s3_explanation_key"),
                    "message": data.get("message"),
                    "error": data.get("error"),
                }
            elif resp.status_code == 404:
                return {
                    "success": False,
                    "status_code": 404,
                    "error": "SessionNotFound",
                    "message": f"Session '{session_id}' was not found.",
                }
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": data.get("error", "StatusQueryFailed"),
                "message": data.get("message", "Failed to query status."),
            }
        except requests.exceptions.RequestException as e:
            logger.warning(f"Status query error for {session_id}: {e}")
            return {
                "success": False,
                "status_code": 0,
                "error": "ConnectionError",
                "message": "Network error while polling status.",
            }
