"""DynamoDB Session Store and state transition manager for NeuroGait."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore

from .models import (
    LEGAL_TRANSITIONS,
    SessionRecord,
    SessionState,
    StateTransitionError,
    is_legal_transition,
)

logger = logging.getLogger(__name__)

DEFAULT_TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "neurogait-sessions")
DEFAULT_REGION = os.environ.get("AWS_REGION", "ap-south-1")


class DynamoSessionStore:
    """Manages session metadata persistence and atomic conditional state transitions."""

    def __init__(
        self,
        table_name: str = DEFAULT_TABLE_NAME,
        region_name: str = DEFAULT_REGION,
        boto3_session: Optional[Any] = None,
        dynamodb_resource: Optional[Any] = None,
    ):
        self.table_name = table_name
        self.region_name = region_name
        self._session = boto3_session
        self._dynamodb_resource = dynamodb_resource
        self._table = None

    def _get_table(self):
        if self._table is None:
            if self._dynamodb_resource:
                self._table = self._dynamodb_resource.Table(self.table_name)
            else:
                if boto3 is None:
                    raise RuntimeError("boto3 is not available in environment.")
                if self._session:
                    dynamodb = self._session.resource("dynamodb", region_name=self.region_name)
                else:
                    dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
                self._table = dynamodb.Table(self.table_name)
        return self._table

    def create_session(self, record: SessionRecord) -> SessionRecord:
        """Create a new session item in DynamoDB with state CREATED.

        Enforces attribute_not_exists(session_id) to prevent accidental overwrites.
        """
        table = self._get_table()
        now_iso = datetime.now(timezone.utc).isoformat()
        record.created_at = record.created_at or now_iso
        record.updated_at = now_iso

        item = record.to_item()

        try:
            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(session_id)",
            )
            logger.info(f"Created session {record.session_id} with state {record.state}")
            return record
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                logger.warning(f"Session {record.session_id} already exists in DynamoDB.")
                raise StateTransitionError(
                    from_state=SessionState.CREATED,
                    to_state=SessionState.CREATED,
                    message=f"Session '{record.session_id}' already exists.",
                )
            raise

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Fetch session record by session_id."""
        table = self._get_table()
        try:
            res = table.get_item(Key={"session_id": session_id}, ConsistentRead=True)
            item = res.get("Item")
            if not item:
                return None
            return SessionRecord.from_item(item)
        except ClientError as e:
            logger.error(f"Error fetching session {session_id} from DynamoDB: {e}")
            raise

    def transition_state(
        self,
        session_id: str,
        from_state: SessionState,
        to_state: SessionState,
        updates: Optional[Dict[str, Any]] = None,
    ) -> SessionRecord:
        """Atomically transition session state from from_state to to_state using conditional write.

        Raises:
            StateTransitionError if transition is illegal or conditional check fails.
        """
        if not is_legal_transition(from_state, to_state):
            raise StateTransitionError(
                from_state=from_state,
                to_state=to_state,
                message=f"Illegal transition: Cannot move from '{from_state.value}' to '{to_state.value}'.",
            )

        table = self._get_table()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Build update expression
        set_clauses = ["#st = :to_state", "updated_at = :now"]
        attr_names = {"#st": "state"}
        attr_values: Dict[str, Any] = {
            ":from_state": from_state.value,
            ":to_state": to_state.value,
            ":now": now_iso,
        }

        if updates:
            for idx, (k, v) in enumerate(updates.items()):
                if v is not None:
                    var_name = f":val_{idx}"
                    key_placeholder = f"#attr_{idx}"
                    set_clauses.append(f"{key_placeholder} = {var_name}")
                    attr_names[key_placeholder] = k
                    attr_values[var_name] = v

        update_expr = f"SET {', '.join(set_clauses)}"

        try:
            res = table.update_item(
                Key={"session_id": session_id},
                UpdateExpression=update_expr,
                ConditionExpression="attribute_exists(session_id) AND #st = :from_state",
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
                ReturnValues="ALL_NEW",
            )
            updated_item = res.get("Attributes", {})
            logger.info(f"Transitioned session {session_id}: {from_state.value} -> {to_state.value}")
            return SessionRecord.from_item(updated_item)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                # State has already moved or item missing; fetch current state for clear error
                current = self.get_session(session_id)
                observed_state = current.state if current else "NON_EXISTENT"
                logger.warning(
                    f"ConditionalCheckFailed: Failed to transition {session_id} from {from_state.value} "
                    f"to {to_state.value}. Observed current state: {observed_state}"
                )
                raise StateTransitionError(
                    from_state=from_state,
                    to_state=to_state,
                    message=(
                        f"State transition conflict: Expected state '{from_state.value}', but current "
                        f"state is '{observed_state}'."
                    ),
                )
            raise

    def record_failure(
        self,
        session_id: str,
        from_state: SessionState,
        failure_state: SessionState,
        error_info: Dict[str, Any],
    ) -> SessionRecord:
        """Transition session to a failure state recording error details."""
        updates = {"error": error_info}
        return self.transition_state(
            session_id=session_id,
            from_state=from_state,
            to_state=failure_state,
            updates=updates,
        )
