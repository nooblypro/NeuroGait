"""NeuroGait Control Plane Lambda Handler with DynamoDB State Machine.

Provides HTTP API routing, artifact validation, task orchestration,
and state machine transitions:
- POST /sessions: Validate upload request, create DynamoDB record in CREATED state, generate presigned S3 URLs.
- POST /sessions/confirm-upload (or /sessions/uploaded): Verify S3 artifacts exist, transition CREATED/UPLOADING -> UPLOADED.
- POST /inference/start: Validate state is UPLOADED (rejects CREATED/UPLOADING with HTTP 409), launch ECS Fargate task, transition to PROCESSING.
- GET /inference/status: Check DynamoDB state, advance PROCESSING -> ML_COMPLETE -> NARRATIVE_GENERATING -> COMPLETE with conditional locks, retrieve canonical predictions & explanation from S3.
- GET /health: Health check and service metadata.

Enforces:
- S3 is single source of truth for large artifacts.
- No raw video, IMU, or predictions JSON in DynamoDB.
- Idempotent GET /inference/status.
- Atomic conditional state transitions.
- Clinical safety guardrails.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional, Tuple
from botocore.client import Config

import boto3
from botocore.exceptions import ClientError

from src.state.dynamo_store import DynamoSessionStore
from src.state.models import (
    SessionRecord,
    SessionState,
    StateTransitionError,
)

# Setup structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration from environment variables
S3_BUCKET = os.environ.get("S3_BUCKET", "neurogait-artifacts-955519187785")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "neurogait-sessions")
ECS_CLUSTER = os.environ.get("ECS_CLUSTER", "neurogait-cluster")
ECS_TASK_DEFINITION = os.environ.get("ECS_TASK_DEFINITION", "neurogait-task:1")
ECS_SUBNET = os.environ.get("ECS_SUBNET", "subnet-0ed8b6b6255d19fbe")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

# Validation limits
MAX_VIDEO_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_IMU_SIZE_BYTES = 50 * 1024 * 1024      # 50 MB
ALLOWED_VIDEO_EXTENSIONS = {".mp4"}
ALLOWED_IMU_EXTENSIONS = {".txt", ".csv"}
SAFE_FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

# Lazy AWS clients & stores
_s3_client = None
_ecs_client = None
_session_store = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com",
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )
    return _s3_client


def get_ecs_client():
    global _ecs_client
    if _ecs_client is None:
        _ecs_client = boto3.client("ecs", region_name=AWS_REGION)
    return _ecs_client


def get_session_store():
    global _session_store
    if _session_store is None:
        _session_store = DynamoSessionStore(table_name=DYNAMODB_TABLE, region_name=AWS_REGION)
    return _session_store


from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Format standard API Gateway HTTP API response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def validate_upload_request(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate input parameters for session creation."""
    v_name = payload.get("video_filename")
    i_name = payload.get("imu_filename")
    v_size = payload.get("video_size_bytes")
    i_size = payload.get("imu_size_bytes")

    if not v_name or not isinstance(v_name, str):
        return False, "Missing or invalid 'video_filename'."
    if not i_name or not isinstance(i_name, str):
        return False, "Missing or invalid 'imu_filename'."

    if not SAFE_FILENAME_REGEX.match(v_name) or len(v_name) > 128:
        return False, "Invalid 'video_filename'. Must be alphanumeric characters, dashes, or underscores."
    if not SAFE_FILENAME_REGEX.match(i_name) or len(i_name) > 128:
        return False, "Invalid 'imu_filename'. Must be alphanumeric characters, dashes, or underscores."

    _, v_ext = os.path.splitext(v_name.lower())
    _, i_ext = os.path.splitext(i_name.lower())

    if v_ext not in ALLOWED_VIDEO_EXTENSIONS:
        return False, f"Unsupported video extension '{v_ext}'. Allowed: {sorted(ALLOWED_VIDEO_EXTENSIONS)}"
    if i_ext not in ALLOWED_IMU_EXTENSIONS:
        return False, f"Unsupported IMU extension '{i_ext}'. Allowed: {sorted(ALLOWED_IMU_EXTENSIONS)}"

    if v_size is not None:
        if not isinstance(v_size, (int, float)) or v_size <= 0:
            return False, "'video_size_bytes' must be a positive number."
        if v_size > MAX_VIDEO_SIZE_BYTES:
            return False, f"'video_size_bytes' exceeds maximum allowed limit ({MAX_VIDEO_SIZE_BYTES} bytes)."

    if i_size is not None:
        if not isinstance(i_size, (int, float)) or i_size <= 0:
            return False, "'imu_size_bytes' must be a positive number."
        if i_size > MAX_IMU_SIZE_BYTES:
            return False, f"'imu_size_bytes' exceeds maximum allowed limit ({MAX_IMU_SIZE_BYTES} bytes)."

    return True, None


def handle_health() -> Dict[str, Any]:
    """Return health and service configuration."""
    return build_response(
        200,
        {
            "status": "HEALTHY",
            "service": "neurogait-control-plane",
            "region": AWS_REGION,
            "ecs_cluster": ECS_CLUSTER,
            "s3_bucket": S3_BUCKET,
            "dynamodb_table": DYNAMODB_TABLE,
            "task_definition": ECS_TASK_DEFINITION,
        },
    )


def handle_create_session(body_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Handle session initialization, persist CREATED in DynamoDB, and generate presigned URLs."""
    valid, err_msg = validate_upload_request(body_dict)
    if not valid:
        logger.warning(f"Validation failure in create_session: {err_msg}")
        return build_response(400, {"error": "ValidationError", "message": err_msg})

    session_id = str(uuid.uuid4())
    video_key = f"inputs/{session_id}/video.mp4"
    imu_key = f"inputs/{session_id}/imu.txt"
    output_key = f"outputs/{session_id}/predictions.json"
    explanation_key = f"outputs/{session_id}/explanation.json"

    s3 = get_s3_client()
    try:
        video_put_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": video_key, "ContentType": "video/mp4"},
            ExpiresIn=3600,
            HttpMethod="PUT",
        )
        imu_put_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": imu_key, "ContentType": "text/plain"},
            ExpiresIn=3600,
            HttpMethod="PUT",
        )
    except ClientError as e:
        logger.error(f"Error generating presigned URLs: {e}")
        return build_response(500, {"error": "S3Error", "message": "Failed to generate upload URLs."})

    # Persist session in DynamoDB in CREATED state
    store = get_session_store()
    record = SessionRecord(
        session_id=session_id,
        state=SessionState.CREATED.value,
        data_mode="real",
        video_filename=body_dict.get("video_filename"),
        imu_filename=body_dict.get("imu_filename"),
        video_size_bytes=body_dict.get("video_size_bytes"),
        imu_size_bytes=body_dict.get("imu_size_bytes"),
        video_s3_key=video_key,
        imu_s3_key=imu_key,
        predictions_s3_key=output_key,
        explanation_s3_key=explanation_key,
    )

    try:
        store.create_session(record)
    except Exception as e:
        logger.error(f"Failed to create session in DynamoDB: {e}")
        return build_response(500, {"error": "DynamoDBError", "message": f"Failed to persist session: {str(e)}"})

    logger.info(f"Created session {session_id} in state CREATED")
    return build_response(
        200,
        {
            "session_id": session_id,
            "status": "CREATED",
            "upload_urls": {
                "video": video_put_url,
                "imu": imu_put_url,
            },
            "s3_keys": {
                "video": video_key,
                "imu": imu_key,
                "output": output_key,
                "explanation": explanation_key,
            },
            "expires_in_seconds": 3600,
        },
    )


def handle_confirm_upload(body_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Verify S3 artifacts and transition session from CREATED/UPLOADING -> UPLOADED."""
    session_id = body_dict.get("session_id")
    if not session_id or not isinstance(session_id, str) or not UUID_REGEX.match(session_id):
        return build_response(400, {"error": "ValidationError", "message": "Missing or invalid 'session_id'."})

    store = get_session_store()
    session = store.get_session(session_id)
    if not session:
        return build_response(404, {"error": "SessionNotFound", "message": f"Session '{session_id}' not found."})

    video_key = session.video_s3_key or f"inputs/{session_id}/video.mp4"
    imu_key = session.imu_s3_key or f"inputs/{session_id}/imu.txt"

    s3 = get_s3_client()
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=video_key)
    except ClientError:
        return build_response(400, {"error": "ArtifactMissing", "message": f"Video artifact '{video_key}' not found in S3."})

    try:
        s3.head_object(Bucket=S3_BUCKET, Key=imu_key)
    except ClientError:
        return build_response(400, {"error": "ArtifactMissing", "message": f"IMU artifact '{imu_key}' not found in S3."})

    current_state = SessionState(session.state)
    if current_state in (SessionState.CREATED, SessionState.UPLOADING):
        try:
            session = store.transition_state(
                session_id=session_id,
                from_state=current_state,
                to_state=SessionState.UPLOADED,
            )
            logger.info(f"Session {session_id} confirmed and transitioned to UPLOADED")
        except StateTransitionError as e:
            logger.warning(f"Concurrent transition for {session_id}: {e}")
            session = store.get_session(session_id)

    return build_response(
        200,
        {
            "session_id": session_id,
            "status": session.state,
            "message": "Upload artifacts verified in S3. Session is UPLOADED and ready for inference.",
        },
    )


def handle_start_inference(body_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Verify state is UPLOADED and launch the ECS Fargate inference task."""
    session_id = body_dict.get("session_id")
    if not session_id or not isinstance(session_id, str) or not UUID_REGEX.match(session_id):
        return build_response(400, {"error": "ValidationError", "message": "Missing or invalid 'session_id'."})

    store = get_session_store()
    session = store.get_session(session_id)
    if not session:
        return build_response(404, {"error": "SessionNotFound", "message": f"Session '{session_id}' not found."})

    current_state = SessionState(session.state)

    # Enforce strict transition constraint: Only UPLOADED -> PROCESSING
    if current_state in (SessionState.CREATED, SessionState.UPLOADING):
        logger.warning(f"Inference rejected: session {session_id} is in state {current_state.value}")
        return build_response(
            409,
            {
                "error": "InvalidStateTransition",
                "message": (
                    f"Session is in state '{current_state.value}'. Upload must be verified and established "
                    f"as 'UPLOADED' before starting inference."
                ),
                "session_id": session_id,
                "current_state": current_state.value,
            },
        )

    # Idempotent handling if already PROCESSING or COMPLETE
    if current_state == SessionState.PROCESSING:
        return build_response(
            202,
            {
                "session_id": session_id,
                "status": "PROCESSING",
                "task_arn": session.ecs_task_arn,
                "s3_output_key": session.predictions_s3_key,
                "message": "Inference already in progress.",
            },
        )
    if current_state == SessionState.COMPLETE:
        return build_response(
            200,
            {
                "session_id": session_id,
                "status": "COMPLETE",
                "s3_output_key": session.predictions_s3_key,
                "message": "Inference already completed.",
            },
        )

    if current_state != SessionState.UPLOADED:
        return build_response(
            409,
            {
                "error": "InvalidStateTransition",
                "message": f"Cannot start inference from state '{current_state.value}'.",
                "session_id": session_id,
                "current_state": current_state.value,
            },
        )

    video_key = session.video_s3_key or f"inputs/{session_id}/video.mp4"
    imu_key = session.imu_s3_key or f"inputs/{session_id}/imu.txt"
    output_key = session.predictions_s3_key or f"outputs/{session_id}/predictions.json"

    s3 = get_s3_client()

    # Generate presigned URLs for the ECS container
    try:
        video_get_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": video_key},
            ExpiresIn=7200,
        )
        imu_get_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": imu_key},
            ExpiresIn=7200,
        )
        output_put_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": output_key, "ContentType": "application/json"},
            ExpiresIn=7200,
            HttpMethod="PUT",
        )
    except ClientError as e:
        logger.error(f"Failed to generate container presigned URLs: {e}")
        return build_response(500, {"error": "S3Error", "message": "Failed to generate container access tokens."})

    # Container execution script
    container_script = (
        "import os\n"
        "import json\n"
        "import urllib.request\n"
        "from src.pipeline import predict_fog\n"
        "\n"
        "v_url = os.environ['INPUT_VIDEO_URL']\n"
        "i_url = os.environ['INPUT_IMU_URL']\n"
        "o_url = os.environ['OUTPUT_JSON_URL']\n"
        "session_id = os.environ['SESSION_ID']\n"
        "\n"
        "os.makedirs('/tmp/inputs', exist_ok=True)\n"
        "os.makedirs('/tmp/outputs', exist_ok=True)\n"
        "v_path = f'/tmp/inputs/{session_id}_video.mp4'\n"
        "i_path = f'/tmp/inputs/{session_id}_imu.txt'\n"
        "o_path = f'/tmp/outputs/{session_id}_predictions.json'\n"
        "\n"
        "print(f'Downloading input artifacts for session {session_id}...')\n"
        "urllib.request.urlretrieve(v_url, v_path)\n"
        "urllib.request.urlretrieve(i_url, i_path)\n"
        "\n"
        "print(f'Executing Phase 1 ML inference for session {session_id}...')\n"
        "predict_fog(video_path=v_path, csv_path=i_path, model_path='models/fog_model.pkl', output_json_path=o_path)\n"
        "\n"
        "print(f'Uploading predictions to S3 for session {session_id}...')\n"
        "with open(o_path, 'rb') as f:\n"
        "    data = f.read()\n"
        "req = urllib.request.Request(o_url, data=data, method='PUT')\n"
        "req.add_header('Content-Type', 'application/json')\n"
        "with urllib.request.urlopen(req) as resp:\n"
        "    print(f'S3 upload response: {resp.status}')\n"
        "print(f'Inference task completed successfully for session {session_id}.')\n"
    )

    ecs = get_ecs_client()
    try:
        run_res = ecs.run_task(
            cluster=ECS_CLUSTER,
            taskDefinition=ECS_TASK_DEFINITION,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [ECS_SUBNET],
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": "neurogait-container",
                        "command": ["python3", "-c", container_script],
                        "environment": [
                            {"name": "INPUT_VIDEO_URL", "value": video_get_url},
                            {"name": "INPUT_IMU_URL", "value": imu_get_url},
                            {"name": "OUTPUT_JSON_URL", "value": output_put_url},
                            {"name": "SESSION_ID", "value": session_id},
                        ],
                    }
                ]
            },
        )
    except ClientError as e:
        logger.error(f"Failed to invoke ECS Fargate task: {e}")
        return build_response(500, {"error": "ECSError", "message": f"Failed to dispatch ECS task: {str(e)}"})

    tasks = run_res.get("tasks", [])
    if not tasks:
        failures = run_res.get("failures", [])
        logger.error(f"ECS task launch failure: {failures}")
        return build_response(500, {"error": "ECSError", "message": f"ECS task launch failed: {failures}"})

    task_arn = tasks[0]["taskArn"]
    logger.info(f"Dispatched ECS task {task_arn} for session {session_id}")

    # Conditionally transition UPLOADED -> PROCESSING
    try:
        store.transition_state(
            session_id=session_id,
            from_state=SessionState.UPLOADED,
            to_state=SessionState.PROCESSING,
            updates={
                "ecs_task_arn": task_arn,
                "predictions_s3_key": output_key,
                "explanation_s3_key": f"outputs/{session_id}/explanation.json",
            },
        )
    except StateTransitionError as e:
        logger.warning(f"State transition warning after launching ECS task for {session_id}: {e}")

    return build_response(
        202,
        {
            "session_id": session_id,
            "status": "PROCESSING",
            "task_arn": task_arn,
            "s3_output_key": output_key,
        },
    )


def handle_get_status(query_params: Optional[Dict[str, str]]) -> Dict[str, Any]:
    """Check DynamoDB state, advance state with conditional locks, and return S3 artifacts."""
    params = query_params or {}
    session_id = params.get("session_id")
    if not session_id or not UUID_REGEX.match(session_id):
        return build_response(400, {"error": "ValidationError", "message": "Missing or invalid 'session_id' parameter."})

    store = get_session_store()
    session = store.get_session(session_id)

    output_key = f"outputs/{session_id}/predictions.json"
    explanation_key = f"outputs/{session_id}/explanation.json"
    s3 = get_s3_client()

    # Backfill migration: If not in DynamoDB, check S3 (e.g. Gate 3/4 legacy session)
    if not session:
        try:
            res = s3.get_object(Bucket=S3_BUCKET, Key=output_key)
            content = res["Body"].read().decode("utf-8")
            episodes = json.loads(content)
            fog_count = sum(1 for e in episodes if e.get("type") == "FoG")
            borderline_count = sum(1 for e in episodes if e.get("type") == "Borderline")
            normal_count = sum(1 for e in episodes if e.get("type") == "Normal")
            summary = {
                "fog_episodes": fog_count,
                "borderline_episodes": borderline_count,
                "normal_episodes": normal_count,
            }
            backfill_rec = SessionRecord(
                session_id=session_id,
                state=SessionState.COMPLETE.value,
                data_mode="real",
                video_s3_key=f"inputs/{session_id}/video.mp4",
                imu_s3_key=f"inputs/{session_id}/imu.txt",
                predictions_s3_key=output_key,
                explanation_s3_key=explanation_key,
                episode_count=len(episodes),
                summary=summary,
                provider="deterministic_rule",
                provider_status="SUCCESS",
            )
            store.create_session(backfill_rec)
            session = backfill_rec
            logger.info(f"Backfilled legacy session {session_id} into DynamoDB with COMPLETE state")
        except Exception:
            return build_response(404, {"error": "SessionNotFound", "message": f"Session '{session_id}' not found."})

    current_state = SessionState(session.state)

    # 1. Terminal / Completed state: read canonical S3 artifacts directly (idempotent, 0 transitions)
    if current_state == SessionState.COMPLETE:
        try:
            pred_res = s3.get_object(Bucket=S3_BUCKET, Key=output_key)
            episodes = json.loads(pred_res["Body"].read().decode("utf-8"))
        except ClientError as e:
            logger.error(f"Failed to read predictions from S3 for {session_id}: {e}")
            return build_response(500, {"error": "S3Error", "message": "Failed to read predictions artifact."})

        explanation_data = None
        try:
            exp_res = s3.get_object(Bucket=S3_BUCKET, Key=explanation_key)
            explanation_data = json.loads(exp_res["Body"].read().decode("utf-8"))
            explanation_data["cached"] = True
        except Exception:
            pass

        return build_response(
            200,
            {
                "session_id": session_id,
                "status": "COMPLETE",
                "episode_count": session.episode_count or len(episodes),
                "summary": session.summary or {
                    "fog_episodes": sum(1 for e in episodes if e.get("type") == "FoG"),
                    "borderline_episodes": sum(1 for e in episodes if e.get("type") == "Borderline"),
                    "normal_episodes": sum(1 for e in episodes if e.get("type") == "Normal"),
                },
                "s3_output_key": output_key,
                "s3_explanation_key": explanation_key,
                "episodes": episodes,
                "explanation": explanation_data,
            },
        )

    # 2. Failure states
    if current_state in (SessionState.UPLOAD_FAILED, SessionState.PROCESSING_FAILED, SessionState.NARRATIVE_FAILED, SessionState.CONNECTION_FAILED):
        return build_response(
            200,
            {
                "session_id": session_id,
                "status": current_state.value,
                "error": session.error,
            },
        )

    # 3. Processing state: Check S3 for predictions and advance state
    if current_state == SessionState.PROCESSING:
        try:
            res = s3.get_object(Bucket=S3_BUCKET, Key=output_key)
            content = res["Body"].read().decode("utf-8")
            episodes = json.loads(content)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code in ("NoSuchKey", "404"):
                return build_response(
                    200,
                    {
                        "session_id": session_id,
                        "status": "PROCESSING",
                        "message": "Inference in progress. Output not yet available.",
                    },
                )
            return build_response(500, {"error": "S3Error", "message": "Failed to query S3."})

        # S3 predictions found! Step A: Transition PROCESSING -> ML_COMPLETE
        try:
            store.transition_state(
                session_id=session_id,
                from_state=SessionState.PROCESSING,
                to_state=SessionState.ML_COMPLETE,
            )
            current_state = SessionState.ML_COMPLETE
        except StateTransitionError:
            session = store.get_session(session_id)
            current_state = SessionState(session.state)

        # Step B: Transition ML_COMPLETE -> NARRATIVE_GENERATING (concurrency lock)
        won_narrative_lock = False
        if current_state == SessionState.ML_COMPLETE:
            try:
                store.transition_state(
                    session_id=session_id,
                    from_state=SessionState.ML_COMPLETE,
                    to_state=SessionState.NARRATIVE_GENERATING,
                )
                won_narrative_lock = True
                current_state = SessionState.NARRATIVE_GENERATING
            except StateTransitionError:
                session = store.get_session(session_id)
                current_state = SessionState(session.state)

        # Step C: If this request won the narrative lock, generate & persist explanation
        explanation_data = None
        if won_narrative_lock or current_state == SessionState.NARRATIVE_GENERATING:
            try:
                # Check S3 cache first
                try:
                    exp_res = s3.get_object(Bucket=S3_BUCKET, Key=explanation_key)
                    explanation_data = json.loads(exp_res["Body"].read().decode("utf-8"))
                    explanation_data["cached"] = True
                except ClientError:
                    from src.explanation.orchestrator import generate_explanation
                    res_obj = generate_explanation(episodes, preferred_provider="auto")
                    explanation_data = res_obj.to_dict()
                    explanation_data["cached"] = False

                    s3.put_object(
                        Bucket=S3_BUCKET,
                        Key=explanation_key,
                        Body=json.dumps(explanation_data).encode("utf-8"),
                        ContentType="application/json",
                    )

                # Compute summary metrics
                fog_count = sum(1 for e in episodes if e.get("type") == "FoG")
                borderline_count = sum(1 for e in episodes if e.get("type") == "Borderline")
                normal_count = sum(1 for e in episodes if e.get("type") == "Normal")
                summary = {
                    "fog_episodes": fog_count,
                    "borderline_episodes": borderline_count,
                    "normal_episodes": normal_count,
                }

                # Transition NARRATIVE_GENERATING -> COMPLETE
                try:
                    store.transition_state(
                        session_id=session_id,
                        from_state=SessionState.NARRATIVE_GENERATING,
                        to_state=SessionState.COMPLETE,
                        updates={
                            "episode_count": len(episodes),
                            "summary": summary,
                            "provider": explanation_data.get("provider", "deterministic_rule"),
                            "provider_status": explanation_data.get("status", "SUCCESS"),
                        },
                    )
                except StateTransitionError:
                    pass

            except Exception as exp_err:
                logger.error(f"Narrative generation failure for {session_id}: {exp_err}")
                try:
                    store.record_failure(
                        session_id=session_id,
                        from_state=SessionState.NARRATIVE_GENERATING,
                        failure_state=SessionState.NARRATIVE_FAILED,
                        error_info={"message": str(exp_err), "code": "NarrativeGenerationError"},
                    )
                except Exception:
                    pass

        # Final read of explanation if needed
        if explanation_data is None:
            try:
                exp_res = s3.get_object(Bucket=S3_BUCKET, Key=explanation_key)
                explanation_data = json.loads(exp_res["Body"].read().decode("utf-8"))
                explanation_data["cached"] = True
            except Exception:
                pass

        fog_count = sum(1 for e in episodes if e.get("type") == "FoG")
        borderline_count = sum(1 for e in episodes if e.get("type") == "Borderline")
        normal_count = sum(1 for e in episodes if e.get("type") == "Normal")

        return build_response(
            200,
            {
                "session_id": session_id,
                "status": "COMPLETE",
                "episode_count": len(episodes),
                "summary": {
                    "fog_episodes": fog_count,
                    "borderline_episodes": borderline_count,
                    "normal_episodes": normal_count,
                },
                "s3_output_key": output_key,
                "s3_explanation_key": explanation_key,
                "episodes": episodes,
                "explanation": explanation_data,
            },
        )

    # 4. For CREATED / UPLOADING / UPLOADED: return current state
    return build_response(
        200,
        {
            "session_id": session_id,
            "status": current_state.value,
        },
    )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main routing entry point for API Gateway HTTP API events."""
    http_method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "GET")
    raw_path = event.get("rawPath") or event.get("path", "/")

    # Normalize path
    path = raw_path.rstrip("/")
    if not path:
        path = "/"

    logger.info(f"Incoming request: {http_method} {path}")

    # Route: OPTIONS (CORS preflight)
    if http_method == "OPTIONS":
        return build_response(200, {"status": "OK"})

    # Route: GET /health
    if http_method == "GET" and (path in ("/health", "/")):
        return handle_health()

    # Parse body for POST requests
    body_dict: Dict[str, Any] = {}
    if http_method == "POST":
        raw_body = event.get("body")
        if raw_body:
            if event.get("isBase64Encoded", False):
                import base64
                raw_body = base64.b64decode(raw_body).decode("utf-8")
            try:
                body_dict = json.loads(raw_body)
            except Exception as e:
                return build_response(400, {"error": "InvalidJSON", "message": f"Malformed JSON request body: {str(e)}"})

    # Route: POST /sessions
    if http_method == "POST" and path in ("/sessions", "/inference/upload"):
        return handle_create_session(body_dict)

    # Route: POST /sessions/confirm-upload (or /sessions/uploaded)
    if http_method == "POST" and path in ("/sessions/confirm-upload", "/sessions/uploaded", "/sessions/verify-upload"):
        return handle_confirm_upload(body_dict)

    # Route: POST /inference/start
    if http_method == "POST" and path in ("/inference/start", "/sessions/process"):
        return handle_start_inference(body_dict)

    # Route: GET /inference/status
    if http_method == "GET" and path in ("/inference/status", "/sessions/status"):
        query_params = event.get("queryStringParameters") or {}
        return handle_get_status(query_params)

    return build_response(404, {"error": "NotFound", "message": f"No route for {http_method} {path}"})
