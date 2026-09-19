# NeuroGait Phase 1 — Gate 3: Control Plane + S3 Evidence

**Execution Date**: 2026-09-18
**Status**: COMPLETE / VERIFIED

---

## 1. Overview & Architecture Target

Gate 3 introduces the lightweight cloud control plane and S3 storage layer without modifying the locked Phase 1 ML behavior or the Gate 2 ECS/Fargate container:

```
Streamlit/Client
       ↓ (HTTP REST / JSON)
API Gateway HTTP API (ap-south-1)
       ↓ (Proxy Integration)
Lambda Control Plane (Python 3.11)
       ↓ (Presigned PUT URLs / Artifact verification)
S3 Bucket (neurogait-artifacts-955519187785)
       ↓ (Presigned GET URLs via container overrides)
ECS Fargate ML Container (neurogait-task:1)
       ↓ (Canonical JSON written to presigned PUT URL)
S3 Bucket Results (outputs/{session_id}/predictions.json)
```

---

## 2. Provisioned AWS Resources

### API Gateway
- **API ID**: `xwncaenjbd`
- **API Name**: `neurogait-api`
- **Protocol**: HTTP (API Gateway v2)
- **Endpoint URL**: `https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com`
- **Stage**: `$default` (auto-deployed)
- **Integration**: AWS Lambda proxy integration to `neurogait-control-plane`

### Lambda Control Plane
- **Function Name**: `neurogait-control-plane`
- **Function ARN**: `arn:aws:lambda:ap-south-1:955519187785:function:neurogait-control-plane`
- **Runtime**: Python 3.11 (Architecture: x86_64)
- **Handler**: `lambda_handler.lambda_handler`
- **Timeout**: 30 seconds
- **Memory**: 256 MB
- **Environment Variables**:
  - `S3_BUCKET`: `neurogait-artifacts-955519187785`
  - `ECS_CLUSTER`: `neurogait-cluster`
  - `ECS_TASK_DEFINITION`: `neurogait-task:1`
  - `ECS_SUBNET`: `subnet-0ed8b6b6255d19fbe`

### S3 Artifact Storage
- **Bucket Name**: `neurogait-artifacts-955519187785`
- **Region**: `ap-south-1`
- **Encryption**: AES256 server-side encryption enabled
- **Public Access Block**: All 4 block settings enabled (`BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`)
- **Key Hierarchy**:
  - Inputs: `inputs/{session_id}/video.mp4`, `inputs/{session_id}/imu.txt`
  - Outputs: `outputs/{session_id}/predictions.json`

### IAM Security & Least Privilege
- **Role Name**: `neurogait-lambda-control-plane-role`
- **Role ARN**: `arn:aws:iam::955519187785:role/neurogait-lambda-control-plane-role`
- **Permissions Policy**:
  - CloudWatch logs: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` on `/aws/lambda/neurogait-control-plane:*`
  - S3 scoped: `s3:GetObject`, `s3:PutObject`, `s3:HeadObject`, `s3:ListBucket` on `arn:aws:s3:::neurogait-artifacts-955519187785/*`
  - ECS scoped: `ecs:RunTask`, `ecs:DescribeTasks` on `arn:aws:ecs:ap-south-1:955519187785:cluster/neurogait-cluster` and `task-definition/neurogait-task:*`
  - IAM pass role: `iam:PassRole` on `arn:aws:iam::955519187785:role/ecsTaskExecutionRole`
- **No Broad Permissions**: No wildcards across unrelated services, accounts, or buckets.

---

## 3. End-to-End Verification Execution

Script: `scripts/e2e_gate3_test.py`

### Step 1: Session Creation via API Gateway
- **Request**:
  ```http
  POST https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com/sessions
  Content-Type: application/json

  {
    "video_filename": "PDFE01_1.mp4",
    "imu_filename": "SUB01_1.txt",
    "video_size_bytes": 84023607,
    "imu_size_bytes": 1930411
  }
  ```
- **Response**: HTTP 200 OK
  - `session_id`: `6ba9e60d-3374-482e-bb0f-0c5f75382c46`
  - `status`: `"AWAITING_UPLOAD"`
  - `upload_urls`: Presigned PUT URLs for video and IMU (3,600s expiry)

### Step 2 & 3: Presigned S3 Uploads
- Video upload: `PUT inputs/6ba9e60d-3374-482e-bb0f-0c5f75382c46/video.mp4` $\to$ HTTP 200 (84,023,607 bytes)
- IMU upload: `PUT inputs/6ba9e60d-3374-482e-bb0f-0c5f75382c46/imu.txt` $\to$ HTTP 200 (1,930,411 bytes)

### Step 4: S3 Object Verification
- Verified both artifacts exist in bucket `neurogait-artifacts-955519187785` via `s3.head_object`.

### Step 5: Dispatch Inference via API Gateway
- **Request**:
  ```http
  POST https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com/inference/start
  Content-Type: application/json

  {
    "session_id": "6ba9e60d-3374-482e-bb0f-0c5f75382c46"
  }
  ```
- **Response**: HTTP 202 Accepted
  - `task_arn`: `arn:aws:ecs:ap-south-1:955519187785:task/neurogait-cluster/3affdebeaf644195bbdc471787143561`
  - `status`: `"PROCESSING"`
  - `s3_output_key`: `outputs/6ba9e60d-3374-482e-bb0f-0c5f75382c46/predictions.json`

### Step 6: ECS Fargate Task Execution
- Task ID: `3affdebeaf644195bbdc471787143561`
- CloudWatch logs verify:
  - Downloaded video & IMU from presigned URLs to `/tmp`
  - Executed `predict_fog()` with exact Phase 1 ML pipeline
  - Uploaded predictions to `outputs/6ba9e60d-3374-482e-bb0f-0c5f75382c46/predictions.json`
- Container exited with `exitCode: 0`.

### Step 7: Retrieve Status & Predictions via API Gateway
- **Request**:
  ```http
  GET https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com/inference/status?session_id=6ba9e60d-3374-482e-bb0f-0c5f75382c46
  ```
- **Response**: HTTP 200 OK
  - `status`: `"COMPLETED"`
  - `episode_count`: `48`
  - `summary`: `{"fog_episodes": 21, "borderline_episodes": 21, "normal_episodes": 6}`
  - `episodes`: Full canonical JSON predictions array

---

## 4. Gate 1 / Gate 2 Baseline Comparison

| Metric | Gate 1 Linux Docker Baseline | Gate 2 ECS Direct Run | Gate 3 Control Plane + S3 E2E | Match Status |
|---|---|---|---|---|
| **Total Episodes** | 48 | 48 | 48 | **100% Exact Match** |
| **FoG Episodes** | 21 | 21 | 21 | **100% Exact Match** |
| **Borderline Episodes** | 21 | 21 | 21 | **100% Exact Match** |
| **Normal Episodes** | 6 | 6 | 6 | **100% Exact Match** |
| **Episode 1** | `0.008–1.308s`, `conf: 0.0511`, `Normal`, `accel_rms` | Identical | Identical | **100% Exact Match** |
| **Episode 2** | `0.408–1.608s`, `conf: 0.4889`, `Borderline`, `accel_rms` | Identical | Identical | **100% Exact Match** |
| **Episode 3** | `0.708–17.808s`, `conf: 0.9677`, `FoG`, `stride_width` | Identical | Identical | **100% Exact Match** |
| **Episode 4** | `16.908–17.908s`, `conf: 0.5879`, `Borderline`, `stride_width` | Identical | Identical | **100% Exact Match** |
| **Episode 5** | `17.008–35.708s`, `conf: 0.9567`, `FoG`, `accel_rms` | Identical | Identical | **100% Exact Match** |
| **Max Confidence Diff** | 0.000000 | 0.000000 | 0.000000 | **BIT-FOR-BIT IDENTICAL** |
| **Canonical JSON Schema** | Valid | Valid | Valid | **100% Valid** |

---

## 5. Input Validation & Failure-Path Tests

All edge cases were tested directly against API Gateway:

| Test Scenario | Request | HTTP Status | Response |
|---|---|---|---|
| **Unsupported Video Format** | `POST /sessions` with `bad.avi` | `400 Bad Request` | `{"error": "ValidationError", "message": "Unsupported video extension '.avi'. Allowed: ['.mp4']"}` |
| **Oversized Video** | `POST /sessions` with size `600MB` | `400 Bad Request` | `{"error": "ValidationError", "message": "'video_size_bytes' exceeds maximum allowed limit (524288000 bytes)."}` |
| **Path Traversal Filename** | `POST /sessions` with `../../secret.mp4` | `400 Bad Request` | `{"error": "ValidationError", "message": "Invalid 'video_filename'. Must be alphanumeric characters, dashes, or underscores."}` |
| **Malformed Session ID** | `POST /inference/start` with `invalid-uuid` | `400 Bad Request` | `{"error": "ValidationError", "message": "Missing or invalid 'session_id'."}` |
| **Missing S3 Artifact** | `POST /inference/start` for non-existent session | `404 Not Found` | `{"error": "ArtifactNotFound", "message": "Video artifact 'inputs/0000.../video.mp4' not found in S3."}` |
| **Status for Unknown Session** | `GET /inference/status?session_id=0000...` | `404 Not Found` | `{"error": "SessionNotFound", "message": "Session '0000...' not found."}` |

---

## 6. Automated Test Suite Execution

```
============================= test session starts ==============================
platform darwin -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/shriram/Documents/Projects/NeuroGait/.venv/bin/python3.13
cachedir: .pytest_cache
rootdir: /Users/shriram/Documents/Projects/NeuroGait
configfile: pytest.ini
collecting ... collected 43 items

tests/test_contract.py::test_valid_canonical_episode_dict PASSED         [  2%]
tests/test_contract.py::test_invalid_primary_cue_rejected PASSED         [  4%]
tests/test_contract.py::test_invalid_confidence_range_rejected PASSED    [  6%]
tests/test_contract.py::test_canonical_json_roundtrip PASSED             [  9%]
tests/test_control_plane.py::test_validate_upload_request_valid PASSED   [ 11%]
tests/test_control_plane.py::test_validate_upload_request_invalid_extension PASSED [ 13%]
tests/test_control_plane.py::test_validate_upload_request_oversized PASSED [ 16%]
tests/test_control_plane.py::test_validate_upload_request_unsafe_characters PASSED [ 18%]
tests/test_control_plane.py::test_handle_health PASSED                   [ 20%]
tests/test_control_plane.py::test_handle_create_session PASSED           [ 23%]
tests/test_control_plane.py::test_handle_start_inference_missing_s3_object PASSED [ 25%]
tests/test_control_plane.py::test_handle_start_inference_success PASSED  [ 27%]
tests/test_control_plane.py::test_handle_get_status_completed PASSED     [ 30%]
tests/test_control_plane.py::test_lambda_handler_routing PASSED          [ 32%]
tests/test_episodes.py::test_classify_window_type_thresholds PASSED      [ 34%]
tests/test_episodes.py::test_episode_aggregation_and_gap_merging PASSED  [ 37%]
tests/test_episodes.py::test_episode_keeps_large_gaps_separate PASSED    [ 39%]
tests/test_episodes.py::test_primary_cue_selection PASSED                [ 41%]
tests/test_features.py::test_canonical_feature_names_and_ordering PASSED [ 44%]
tests/test_features.py::test_extract_feature_matrix_shape_and_ordering PASSED [ 46%]
tests/test_features.py::test_extract_feature_matrix_missing_feature PASSED [ 48%]
tests/test_features.py::test_extract_feature_matrix_rejects_nans PASSED  [ 51%]
tests/test_imu.py::test_detect_imu_columns PASSED                        [ 53%]
tests/test_imu.py::test_detect_imu_columns_lowercase_variants PASSED     [ 55%]
tests/test_imu.py::test_accel_rms_formula PASSED                         [ 58%]
tests/test_imu.py::test_gyro_variance_formulas PASSED                    [ 60%]
tests/test_imu.py::test_rolling_windows_end_timestamps PASSED            [ 62%]
tests/test_imu.py::test_sampling_rate_discovery PASSED                   [ 65%]
tests/test_model.py::test_build_model_hyperparameters PASSED             [ 67%]
tests/test_model.py::test_fit_and_predict_probability PASSED             [ 69%]
tests/test_model.py::test_degenerate_labels_error PASSED                 [ 72%]
tests/test_model.py::test_model_persistence_roundtrip PASSED             [ 74%]
tests/test_pipeline.py::test_pipeline_real_integration PASSED            [ 76%]
tests/test_pose.py::test_knee_angle_orthogonal PASSED                    [ 79%]
tests/test_pose.py::test_knee_angle_straight PASSED                      [ 81%]
tests/test_pose.py::test_knee_angle_fully_flexed PASSED                  [ 83%]
tests/test_pose.py::test_knee_angle_zero_length_vector PASSED            [ 86%]
tests/test_pose.py::test_stride_width PASSED                             [ 88%]
tests/test_pose.py::test_velocity PASSED                                 [ 90%]
tests/test_pose.py::test_velocity_invalid_dt PASSED                      [ 93%]
tests/test_sync.py::test_synchronization_within_tolerance PASSED         [ 95%]
tests/test_sync.py::test_synchronization_drops_unmatched PASSED          [ 97%]
tests/test_sync.py::test_sync_error_under_10_rows PASSED                 [100%]

============================= 43 passed in 10.02s ==============================
```

---

## 7. Non-Negotiables Verification Matrix

| Gate 3 Non-Negotiable | Status | Verification Detail |
|---|---|---|
| Phase 1 ML Behavior Unchanged | PASSED | `src/` ML logic untouched |
| No DynamoDB | PASSED | 0 DynamoDB tables created |
| No Bedrock | PASSED | 0 Bedrock models or calls |
| No Streamlit UI | PASSED | 0 UI components built |
| No Live Mode | PASSED | Batch recorded mode only |
| No EKS / Kubernetes | PASSED | Serverless ECS Fargate |
| No GPU Infrastructure | PASSED | Fargate Graviton ARM64 CPU |
| Lambda Lightweight | PASSED | No inference inside Lambda; memory 256MB, timeout 30s |
| S3 for Large Artifacts | PASSED | Video and IMU streamed directly to S3 via presigned URLs |
| Never Put Video in DynamoDB | PASSED | S3 is sole artifact store |
| Input Validation Enforced | PASSED | Extensions, sizes, filenames, and UUIDs strictly checked |
| No AWS Credentials Exposed | PASSED | Presigned PUT/GET URLs generated server-side |
| Least-Privilege IAM | PASSED | Scoped policies for Lambda and ECS |
| No Patient Data Logged | PASSED | CloudWatch logs capture IDs and summaries only |
| Canonical JSON Contract Preserved | PASSED | 100% compliant schema verified |
