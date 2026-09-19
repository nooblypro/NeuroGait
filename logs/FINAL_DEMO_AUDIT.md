# NEUROGAIT — FINAL DEMO-DAY ADVERSARIAL AUDIT REPORT
**Date:** 2026-09-19
**Target:** Clean recorded pipeline, ML inference, AWS control plane, and Streamlit demo interface verification
**Hardware Status:** Gate 7B Live Hardware remains **FROZEN & BLOCKED** (no camera permissions, phone IMU, WebRTC, or live hardware modifications).

---

## 1. Clean Environment Verification
*Evidence: Independent dependency & environment audit*

### Startup Commands
- **Local Recorded Demo:**
  ```bash
  streamlit run app.py
  ```
- **AWS Cloud Pipeline Demo:**
  ```bash
  streamlit run app.py
  ```
- **API URL Configuration:** Streamlit communicates with AWS API Gateway via `https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com` (configured in `src/ui/api_client.py` as default or overridden by `API_BASE_URL` env var).
- **Credentials Requirement:** AWS credentials are **NOT** required on the user's Streamlit machine. All authentication is scoped to presigned S3 URLs and IAM roles within AWS Lambda / ECS.
- **Model Integrity:** `models/fog_model.pkl` SHA256 is `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf` [VERIFIED UNMODIFIED].

---

## 2. Real User Demo — Local Mode
*Evidence: Direct execution of `predict_fog` + `generate_explanation` on bundled trial `PDFE01_1.mp4` + `SUB01_1.txt`*

- **Pipeline Execution:** 100% On-Device Deterministic ML Engine (`models/fog_model.pkl`).
- **Processing Time:**
  - Video Pose Kinematics + IMU Fusion (120.02s video, 3,598 frames, 1,190 fused rows): **58.55s**
  - Explanation Generation: **0.24s**
  - Total Local Processing: **58.79s**
- **Output Metrics:**
  - Total Episodes Generated: **12**
  - Freezing of Gait (FoG, $p \ge 0.60$): **4 episodes**
  - Borderline Gait ($0.40 \le p < 0.60$): **3 episodes**
  - Normal Gait ($p < 0.40$): **5 episodes**
- **Explanation Provider:** `deterministic_rule` (Reproducible, zero hallucination risk, includes clinical safety disclaimer).
- **Refresh & Session Persistence:** URL query parameter `?session_id=local-xxxxxxxx` stores session state, preventing rerun or session wipe upon browser refresh.

---

## 3. Real User Demo — AWS Mode
*Evidence: Live end-to-end execution of session `b3199c8d-6426-4750-9b43-8b9fb93711d0` on remote AWS infrastructure*

- **API Health:** HTTP 200 `HEALTHY` (`service: neurogait-control-plane`, `ecs_cluster: neurogait-cluster`, `dynamodb_table: neurogait-sessions`).
- **Execution Flow & State Machine:**
  1. `CREATE SESSION` -> HTTP 200 (`CREATED`, S3 presigned URLs generated)
  2. `S3 ARTIFACT UPLOAD` -> HTTP 200 (Video: 84.02 MB in 18.08s, IMU: 1.93 MB in 0.41s)
  3. `CONFIRM UPLOAD` -> HTTP 200 (`UPLOADED`, S3 artifact existence verified)
  4. `START INFERENCE` -> HTTP 202 (`PROCESSING`, ECS Fargate Task ARN `arn:aws:ecs:ap-south-1:955519187785:task/neurogait-cluster/e976760fc9fd41239c20957e487ec688` dispatched)
  5. `POLL STATUS` -> Polled every 5s; transitioned to `COMPLETE` at ~120s
- **Output Results:**
  - Episode Count: **48 episodes**
  - FoG Episodes: **21**
  - Borderline Episodes: **21**
  - Normal Episodes: **6**
  - Explanation Provider: `deterministic_rule` (cached in S3, latency 0.13ms)
  - DynamoDB Record: Cleanly locked in `COMPLETE` state with immutable output S3 key.

---

## 4. Failure Demonstrations & Defenses
*Evidence: 14 adversarial scenarios in `scripts/verify_complete_recorded_pipeline.py` & 16 ML stress cases*

| Failure Scenario | Handled Behavior | Result |
| :--- | :--- | :--- |
| **Missing Video File** | Clean `FileNotFoundError`, no crash, useful user error | **VERIFIED DIRECTLY** |
| **Missing IMU File** | Clean `FileNotFoundError`, no crash, useful user error | **VERIFIED DIRECTLY** |
| **Corrupt Video File** | OpenCV VideoCapture failure caught, raises `ValueError` | **VERIFIED DIRECTLY** |
| **Corrupt IMU File** | Missing header / column check rejects file cleanly | **VERIFIED DIRECTLY** |
| **Mismatched Timestamps** | `SyncError` raised when $<10$ rows fused, no silent garbage | **VERIFIED DIRECTLY** |
| **API Disconnection** | `NeuroGaitAPIClient` catches connection errors, returns clean error dict | **VERIFIED DIRECTLY** |
| **Invalid State Jump (CREATED -> START)**| DynamoDB Conditional Check rejects with HTTP 409 Conflict | **VERIFIED DIRECTLY** |
| **S3 Missing Artifact on Confirm** | Lambda HeadObject check fails with HTTP 400 | **VERIFIED DIRECTLY** |
| **Browser Refresh Post-Completion** | Query parameter `?session_id=` cleanly reloads without duplicate inference | **VERIFIED DIRECTLY** |
| **Duplicate Start Request**| Prevented by UI disabling and backend 409 conflict | **VERIFIED DIRECTLY** |

---

## 5. Demo Mode Transparency
- **Explicit Labeling:** Local engine mode displays: `💻 EXECUTION MODE: DETERMINISTIC LOCAL ENGINE (OFFLINE DEMO FALLBACK)`.
- **Modality Preservation:** Replay mode is explicitly labeled as `synthetic_demo` / replayed input.
- **Provider Attribution:** All narratives explicitly show provider tag (`deterministic_rule` or `bedrock_claude`) with clinical safety disclaimer.

---

## 6. Result Correctness & Model Contract
- **Model SHA256:** `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf` [VERIFIED UNCHANGED]
- **Canonical Feature List (8 Features, Strict Order):**
  1. `left_ankle_velocity`
  2. `right_ankle_velocity`
  3. `left_knee_angle`
  4. `right_knee_angle`
  5. `stride_width`
  6. `accel_rms`
  7. `gyro_x_var`
  8. `gyro_z_var`
- **Threshold Bands:**
  - $p < 0.40 \rightarrow$ **Normal**
  - $0.40 \le p < 0.60 \rightarrow$ **Borderline**
  - $p \ge 0.60 \rightarrow$ **FoG**

---

## 7. Performance Timings (Measured Apple Silicon M4 / AWS ap-south-1)
- **Application Startup (`streamlit run`):** ~1.8 seconds
- **Local Inference Pipeline (120s video):** 58.55 seconds
- **Local Explanation Generation:** 0.24 seconds
- **AWS S3 Artifact Upload (86 MB total):** 18.49 seconds
- **AWS ECS Fargate Task Cold-Start + Execution:** ~102 seconds
- **AWS Result Retrieval (DynamoDB/S3):** ~0.15 seconds

---

## 8. Final Verification Command Log

| Verification Check | Command | Output Summary | Status |
| :--- | :--- | :--- | :--- |
| **Full Pytest Suite** | `.venv/bin/pytest -v` | **88 passed in 133.18s** | **VERIFIED DIRECTLY** |
| **Gate 7A Parity** | `.venv/bin/python scripts/independent_gate7a_parity.py` | **12/12 Episodes Matched (0.000000 diff)** | **VERIFIED DIRECTLY** |
| **ML Stress Suite** | `.venv/bin/python scripts/stress_test_ml_pipeline.py` | **16/16 Edge Cases Handled** | **VERIFIED DIRECTLY** |
| **External Video Stress** | `.venv/bin/python scripts/verify_external_video_stress.py` | **Independent Verifier: PASS** | **VERIFIED DIRECTLY** |
| **Pipeline E2E Scenarios** | `.venv/bin/python scripts/verify_complete_recorded_pipeline.py` | **14/14 Scenarios Passed** | **VERIFIED DIRECTLY** |
| **AWS Remote E2E Session** | Remote ECS / API Gateway Execution | **Session `b3199c8d` COMPLETE (48 episodes)** | **VERIFIED DIRECTLY** |
| **Gate 7B Physical Hardware**| Camera / Phone IMU | **Intentionally FROZEN / BLOCKED** | **BLOCKED** |

---

## FINAL VERDICT

# `DEMO_READY_WITH_LIMITATIONS`

### Justification:
1. **Recorded Mode (Both Local Engine & AWS Cloud):** Fully validated, robust against corrupt/missing data, resilient against browser refreshes, and mathematically verified.
2. **Deterministic Offline Fallback:** Fully operational on-device using frozen `models/fog_model.pkl` with identical JSON contract.
3. **Known Limitation:** Gate 7B live physical hardware (MacBook webcam & phone IMU) remains intentionally frozen and blocked per project instructions.
