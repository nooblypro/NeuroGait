"""State models and transition validation for NeuroGait pipeline state machine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Set


class SessionState(str, Enum):
    """Pipeline state enumeration."""
    # Normal execution states
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    ML_COMPLETE = "ML_COMPLETE"
    NARRATIVE_GENERATING = "NARRATIVE_GENERATING"
    COMPLETE = "COMPLETE"

    # Failure states
    UPLOAD_FAILED = "UPLOAD_FAILED"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    NARRATIVE_FAILED = "NARRATIVE_FAILED"
    CONNECTION_FAILED = "CONNECTION_FAILED"


# Valid transition graph
LEGAL_TRANSITIONS: Dict[SessionState, Set[SessionState]] = {
    SessionState.CREATED: {
        SessionState.UPLOADING,
        SessionState.UPLOADED,
        SessionState.UPLOAD_FAILED,
        SessionState.CONNECTION_FAILED,
    },
    SessionState.UPLOADING: {
        SessionState.UPLOADED,
        SessionState.UPLOAD_FAILED,
        SessionState.CONNECTION_FAILED,
    },
    SessionState.UPLOADED: {
        SessionState.PROCESSING,
        SessionState.PROCESSING_FAILED,
    },
    SessionState.PROCESSING: {
        SessionState.ML_COMPLETE,
        SessionState.PROCESSING_FAILED,
    },
    SessionState.ML_COMPLETE: {
        SessionState.NARRATIVE_GENERATING,
        SessionState.NARRATIVE_FAILED,
    },
    SessionState.NARRATIVE_GENERATING: {
        SessionState.COMPLETE,
        SessionState.NARRATIVE_FAILED,
    },
    # Terminal states
    SessionState.COMPLETE: set(),
    SessionState.UPLOAD_FAILED: set(),
    SessionState.PROCESSING_FAILED: set(),
    SessionState.NARRATIVE_FAILED: set(),
    SessionState.CONNECTION_FAILED: set(),
}


def is_legal_transition(from_state: SessionState, to_state: SessionState) -> bool:
    """Check if transitioning from_state -> to_state is permissible."""
    return to_state in LEGAL_TRANSITIONS.get(from_state, set())


class StateTransitionError(Exception):
    """Raised when an illegal or unauthorized state transition is attempted."""
    def __init__(self, from_state: SessionState, to_state: SessionState, message: Optional[str] = None):
        msg = message or f"Illegal state transition from '{from_state.value}' to '{to_state.value}'."
        super().__init__(msg)
        self.from_state = from_state
        self.to_state = to_state


from decimal import Decimal


def sanitize_dynamo_types(obj: Any) -> Any:
    """Recursively convert boto3 Decimal objects to standard int/float types."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_dynamo_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_dynamo_types(x) for x in obj]
    return obj


@dataclass
class SessionRecord:
    """DynamoDB session metadata item representation."""
    session_id: str
    state: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_mode: str = "real"
    video_filename: Optional[str] = None
    imu_filename: Optional[str] = None
    video_size_bytes: Optional[int] = None
    imu_size_bytes: Optional[int] = None
    video_s3_key: Optional[str] = None
    imu_s3_key: Optional[str] = None
    predictions_s3_key: Optional[str] = None
    explanation_s3_key: Optional[str] = None
    ecs_task_arn: Optional[str] = None
    episode_count: Optional[int] = None
    summary: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    provider_status: Optional[str] = None
    error: Optional[Dict[str, Any]] = None

    def to_item(self) -> Dict[str, Any]:
        """Convert record to clean DynamoDB item dict omitting None values."""
        item = {}
        for k, v in asdict(self).items():
            if v is not None:
                item[k] = v
        return item

    @classmethod
    def from_item(cls, raw_item: Dict[str, Any]) -> SessionRecord:
        """Instantiate SessionRecord from DynamoDB item dict with type sanitization."""
        item = sanitize_dynamo_types(raw_item)
        return cls(
            session_id=item["session_id"],
            state=item["state"],
            created_at=item.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=item.get("updated_at", datetime.now(timezone.utc).isoformat()),
            data_mode=item.get("data_mode", "real"),
            video_filename=item.get("video_filename"),
            imu_filename=item.get("imu_filename"),
            video_size_bytes=int(item["video_size_bytes"]) if "video_size_bytes" in item and item["video_size_bytes"] is not None else None,
            imu_size_bytes=int(item["imu_size_bytes"]) if "imu_size_bytes" in item and item["imu_size_bytes"] is not None else None,
            video_s3_key=item.get("video_s3_key"),
            imu_s3_key=item.get("imu_s3_key"),
            predictions_s3_key=item.get("predictions_s3_key"),
            explanation_s3_key=item.get("explanation_s3_key"),
            ecs_task_arn=item.get("ecs_task_arn"),
            episode_count=int(item["episode_count"]) if "episode_count" in item and item["episode_count"] is not None else None,
            summary=item.get("summary"),
            provider=item.get("provider"),
            provider_status=item.get("provider_status"),
            error=item.get("error"),
        )
