"""NeuroGait FastAPI Backend Service.

Provides REST API endpoints for multimodal movement assessment:
- GET /health
- POST /sessions
- POST /sessions/confirm-upload
- POST /inference/start
- GET /inference/status

Supports both standalone container execution (uvicorn) and ASGI serverless execution (Mangum).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import canonical control plane business logic
from src.control_plane.lambda_handler import (
    handle_confirm_upload,
    handle_create_session,
    handle_get_status,
    handle_health,
    handle_start_inference,
)

logger = logging.getLogger("neurogait.api")
logging.basicConfig(level=logging.INFO)

# Configurable CORS origins
DEFAULT_ALLOWED_ORIGINS = [
    "https://frontend-woad-iota-23.vercel.app",
    "https://*.vercel.app",
    "https://*.cloudfront.net",
    "http://localhost:5173",
    "http://localhost:3000",
]

CUSTOM_ORIGINS_ENV = os.environ.get("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in CUSTOM_ORIGINS_ENV.split(",") if o.strip()] if CUSTOM_ORIGINS_ENV else DEFAULT_ALLOWED_ORIGINS

app = FastAPI(
    title="NeuroGait Backend API",
    version="1.0.0",
    description="Multimodal Movement Assessment and Freezing-of-Gait (FoG) Cloud Control Plane",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.cloudfront\.net|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["ETag", "x-amz-request-id"],
)


def _unwrap_lambda_response(res: Dict[str, Any]) -> JSONResponse:
    """Helper to convert standard control plane dictionary response into FastAPI JSONResponse."""
    status_code = res.get("statusCode", 200)
    raw_body = res.get("body", "{}")
    if isinstance(raw_body, str):
        try:
            content = json.loads(raw_body)
        except Exception:
            content = {"message": raw_body}
    else:
        content = raw_body
    return JSONResponse(status_code=status_code, content=content)


# --- Pydantic Request Models ---
class CreateSessionRequest(BaseModel):
    video_filename: str = Field(..., example="PDFE01_1.mp4")
    imu_filename: str = Field(..., example="SUB01_1.txt")
    video_size_bytes: Optional[int] = Field(None, example=83886080)
    imu_size_bytes: Optional[int] = Field(None, example=1900000)


class ConfirmUploadRequest(BaseModel):
    session_id: str = Field(..., example="e16d88b0-d66e-4e8f-b0c9-4b75b6a72e8f")


class StartInferenceRequest(BaseModel):
    session_id: str = Field(..., example="e16d88b0-d66e-4e8f-b0c9-4b75b6a72e8f")
    data_mode: Optional[str] = Field("real", example="real")


# --- API Endpoints ---
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint returning system topology and state."""
    res = handle_health()
    return _unwrap_lambda_response(res)


@app.post("/sessions", tags=["Sessions"])
async def create_session(req: CreateSessionRequest):
    """Initialize assessment session and retrieve presigned S3 PUT upload URLs."""
    res = handle_create_session(req.model_dump())
    return _unwrap_lambda_response(res)


@app.post("/sessions/confirm-upload", tags=["Sessions"])
async def confirm_upload(req: ConfirmUploadRequest):
    """Confirm artifact presence in S3 and transition session to UPLOADED state."""
    res = handle_confirm_upload(req.model_dump())
    return _unwrap_lambda_response(res)


@app.post("/inference/start", tags=["Inference"])
async def start_inference(req: StartInferenceRequest):
    """Dispatch ECS Fargate ML inference container for the session."""
    res = handle_start_inference(req.model_dump())
    return _unwrap_lambda_response(res)


@app.get("/inference/status", tags=["Inference"])
async def get_inference_status(session_id: Optional[str] = None, limit: Optional[int] = 20):
    """Poll session status, canonical FoG episodes, and Bedrock explanation."""
    query_params = {}
    if session_id:
        query_params["session_id"] = session_id
    if limit is not None:
        query_params["limit"] = str(limit)

    res = handle_get_status(query_params)
    return _unwrap_lambda_response(res)


# ASGI Mangum Handler for Lambda / API Gateway serverless compatibility
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
