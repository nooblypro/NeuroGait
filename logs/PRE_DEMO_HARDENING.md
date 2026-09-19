# NeuroGait — Pre-Demo Hardening & External Validation Report
**Target**: Complete Hardening of Recorded Pipeline, ML Foundation, AWS Control Plane, and Streamlit Demo Prior to Live Hardware.
**Execution Date**: 2026-09-19
**Platform**: macOS Apple Silicon (Darwin 24.6.0 arm64, Python 3.13.15)

---

## 1. Classification & Trust Matrix

Every system claim is strictly categorized according to verified empirical execution:

| Classification | Meaning |
|:---|:---|
| **VERIFIED** | Directly executed and proven with reproducible commands, stdout, and independent verification scripts. |
| **AGY-REPORTED** | Claimed by an agent report but re-audited and cross-checked against actual code. |
| **NOT VERIFIED** | Deferred or cannot be evaluated without external dependencies/unmet conditions. |
| **BLOCKED** | Intentionally blocked due to hardware or security prerequisites (Gate 7B). |

---

## 2. Invariant Verification

### A. Frozen Model & Scaler Integrity: **[VERIFIED]**
- **Model Path**: `models/fog_model.pkl`
- **SHA256 Before**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **SHA256 After**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **Verdict**: Match (0 byte drift, zero retraining).

### B. Canonical 8-Feature Contract & Order: **[VERIFIED]**
Immutable ordering strictly enforced by `src/features.py`:
1. `left_ankle_velocity`
2. `right_ankle_velocity`
3. `left_knee_angle`
4. `right_knee_angle`
5. `stride_width`
6. `accel_rms`
7. `gyro_x_var`
8. `gyro_z_var`

### C. Decision Thresholds & Banding: **[VERIFIED]**
- $p < 0.40 \rightarrow$ `Normal`
- $0.40 \le p < 0.60 \rightarrow$ `Borderline`
- $p \ge 0.60 \rightarrow$ `FoG`

---

## 3. Phase-by-Phase Execution Results

### Phase 1 — Recon: **[VERIFIED]**
- Clean git status confirmed.
- Verified absence of secrets or patient health identifiers in committed logs.
- Discovered active remote AWS Control Plane at `https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com` responding with HTTP 200 and healthy DynamoDB/ECS configuration.

### Phase 2 — Adversarial Test Audit: **[VERIFIED]**
Audited all 14 test suites in `tests/`:
- Real implementations are exercised; tests assert on actual mathematical formulas (knee angle trigonometry, velocity calculation, rolling window variances, RMS).
- Boundary tests assert clean failure on NaNs, non-positive $\Delta t$, and illegal state machine transitions.
- Pytest suite: **88 passed in 135.04s**.

### Phase 3 — ML Pipeline Stress Test (16 Edge Cases): **[VERIFIED]**
Executed via `scripts/stress_test_ml_pipeline.py`:
- `[01/16]` Normal Window Threshold (p < 0.40) -> **PASS**
- `[02/16]` FoG Window Threshold (p >= 0.60) -> **PASS**
- `[03/16]` Borderline Confidence (0.40 <= p < 0.60) -> **PASS**
- `[04/16]` Missing Pose Landmarks Handling (blank frame -> NaNs) -> **PASS**
- `[05/16]` Leading NaNs in Pose Coordinates (bfill/ffill) -> **PASS**
- `[06/16]` Internal NaNs in Pose Coordinates (ffill) -> **PASS**
- `[07/16]` Malformed IMU Rows Handling (clean ValueError) -> **PASS**
- `[08/16]` Missing Timestamps in IMU (KeyError) -> **PASS**
- `[09/16]` Duplicated Timestamps in IMU (median dt rate recovery) -> **PASS**
- `[10/16]` Irregular IMU Sampling (jitter robust) -> **PASS**
- `[11/16]` Short Recordings (<10 Fused Rows -> SyncError) -> **PASS**
- `[12/16]` Empty Recordings (0 rows -> SyncError) -> **PASS**
- `[13/16]` Mismatched Video/IMU Duration (disjoint -> SyncError) -> **PASS**
- `[14/16]` Sync Outside $\pm 0.1$s Tolerance -> **PASS**
- `[15/16]` Fewer than 10 Fused Rows Safety Gate -> **PASS**
- `[16/16]` Corrupted Video File Handling (ValueError) -> **PASS**
- **Stress Test Summary**: **16/16 Cases Passed**.

### Phase 4 — External Video Stress Validation: **[VERIFIED]**
Executed via `scripts/run_external_video_stress_test.py` and independently verified via `scripts/verify_external_video_stress.py`:
- Tested 6 conditions across Toronto Older Adults Gait Archive and Wellcome Historical Archive:
  - `EXT-01`: Normal Orientation (Sagittal OAW01) -> Valid Detections: 0/300 (camera inverted in rig), Pipeline Crashed: False.
  - `EXT-02`: Upper-Body-Only / Partial (OAW01 top) -> Valid Detections: 0/300 (ankles occluded), Pipeline Crashed: False.
  - `EXT-03`: Sagittal Baseline (OAW02) -> Valid Detections: 16/300, Pipeline Crashed: False.
  - `EXT-04`: Low-Resolution & Long (Wellcome 320x240, 500 frames) -> Valid Detections: 346/500 (69.2%), Proc FPS: 74.6, Pipeline Crashed: False.
  - `EXT-05`: Inverted Orientation (180° flip) -> Valid Detections: 132/200 (66.0%), Pipeline Crashed: False.
  - `EXT-06`: Rotated Orientation (90° clockwise roll) -> Valid Detections: 0/200, Pipeline Crashed: False.
- **Independent Verifier**: `scripts/verify_external_video_stress.py` exited 0 with all quantitative bounds verified, zero model modification, and strictly zero synthetic IMU fabrication.

### Phase 5 — Complete Recorded Pipeline Audit (Scenarios A–N): **[VERIFIED]**
Executed via `scripts/verify_complete_recorded_pipeline.py`:
- `[A]` Known-Good Real Session (`PDFE01_1.mp4` + `SUB01_1.txt`) -> **PASS**
- `[B]` Missing Video File (`FileNotFoundError`) -> **PASS**
- `[C]` Missing IMU File (`FileNotFoundError`) -> **PASS**
- `[D]` Corrupt Video File (`ValueError`) -> **PASS**
- `[E]` Corrupt IMU File (Clean rejection) -> **PASS**
- `[F]` Mismatched Session Duration (`SyncError`) -> **PASS**
- `[G]` Synchronization Boundary Drift $> 0.1$s (`SyncError`) -> **PASS**
- `[H]` ML Feature Shape Defense ($<8$ features `ValueError`) -> **PASS**
- `[I]` Explanation Provider Safety & Fallback -> **PASS**
- `[J]` DynamoDB State Machine Conflict (`CREATED -> START` returns HTTP 409) -> **PASS**
- `[K]` S3 Missing Artifact Validation (HTTP 400 on unuploaded confirmation) -> **PASS**
- `[L]` Repeated Polling Idempotency -> **PASS**
- `[M]` Repeated Completion Idempotency -> **PASS**
- `[N]` Duplicate Start Rejection (HTTP 409) -> **PASS**
- **Pipeline Audit Summary**: **14/14 Scenarios Passed**.

### Phase 6 — AWS Path Verification: **[VERIFIED]**
- API Endpoint: `https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com`
- S3 Bucket: `neurogait-artifacts-955519187785`
- DynamoDB Table: `neurogait-sessions`
- State Machine Enforced: `CREATED -> UPLOADING -> UPLOADED -> PROCESSING -> ML_COMPLETE -> NARRATIVE_GENERATING -> COMPLETE`.
- No credentials exposed in logs or Streamlit UI.

### Phase 7 & 8 — Demo Hardening & Fallback: **[VERIFIED]**
1. **Browser Refresh Preservation**:
   - `st.query_params["session_id"]` automatically binds the session identifier to the browser URL.
   - Refreshing the browser (F5) reloads the active session via `get_status(session_id)` without creating duplicate sessions or re-triggering inference.
2. **Pre-Loaded Sample Patient Trial**:
   - Added a direct checkbox in the Recorded Mode UI: "📂 Use Pre-Loaded Verified Patient Trial (`PDFE01_1.mp4` + `SUB01_1.txt`)". Presenters do not need to manually locate or drag-and-drop files during live demonstrations.
3. **Deterministic Local Engine Fallback**:
   - Presenters can toggle execution between `☁️ AWS Cloud Pipeline` and `💻 Local Deterministic Engine (Offline / models/fog_model.pkl)`.
   - If WiFi or cloud connectivity is disrupted, the local engine runs `predict_fog` directly on-device, producing the identical canonical JSON schema and explanation narrative with explicit attribution banner.

### Phase 9 — Code Quality Defect Fixes: **[VERIFIED]**
- `src/pose.py`: Added `try...finally: cap.release()` around OpenCV video reading loop to eliminate unclosed file descriptor leaks when exceptions or dropouts occur.
- `app.py`: Hardened query parameter synchronization and added safe error boundaries.

---

## 4. Gate 7A Parity Verification Result: **[VERIFIED]**

Raw execution of `scripts/independent_gate7a_parity.py`:
```
Recorded episode count: 12
Live episode count: 12

Episode 0:
  Recorded: start=0.008, end=1.308, conf=0.012, type=Normal, cue=accel_rms
  Live:     start=0.008, end=1.308, conf=0.012, type=Normal, cue=accel_rms
  Verdict:  MATCH
Episode 1:
  Recorded: start=0.408, end=35.708, conf=0.9774, type=FoG, cue=accel_rms
  Live:     start=0.408, end=35.708, conf=0.9774, type=FoG, cue=accel_rms
  Verdict:  MATCH
Episode 11:
  Recorded: start=105.308, end=119.908, conf=0.9234, type=FoG, cue=accel_rms
  Live:     start=105.308, end=119.908, conf=0.9234, type=FoG, cue=accel_rms
  Verdict:  MATCH

Exact start matches: 12 / 12
Exact end matches: 12 / 12
Exact confidence matches: 12 / 12
Exact type matches: 12 / 12
Exact primary cue matches: 12 / 12

max confidence absolute difference: 0.000000
mean confidence absolute difference: 0.000000
max start difference: 0.000000
max end difference: 0.000000

OVERALL PARITY VERDICT:
>>> PASS: 100% INDEPENDENT PARITY CONFIRMED <<<
```

---

## 5. Gate 7B Status: **[BLOCKED]**

Raw execution of `scripts/independent_gate7b_verification.py`:
```
=================================================================
>>> INDEPENDENT VERIFICATION VERDICT: BLOCKED / FAILED (7 errors) <<<
  • HARDWARE_STATUS_NOT_SUCCESS: Status=BLOCKED, Blocker=CAMERA_ACCESS_BLOCKED
  • CAMERA_ZERO_FRAMES: Received 0 camera frames (CAMERA_ACCESS_BLOCKED).
  • CAMERA_ACCESS_NOT_GRANTED: macOS camera permission denied.
  • PHONE_ZERO_SAMPLES: Received 0 IMU samples (PHONE_IMU_UNAVAILABLE).
  • PHONE_IMU_NOT_CONNECTED: Physical phone IMU was not connected.
  • INSUFFICIENT_FUSED_ROWS: 0 fused rows (< 10 required).
  • INVALID_DATA_MODE: data_mode must be 'real' for Gate 7B, got 'none'.
=================================================================
```
- Hardware integration remains strictly frozen and blocked as requested.

---

## 6. Final Demo Readiness Assessment

**DEMO READINESS: READY WITH KNOWN LIMITATIONS**

### Verified Strengths:
1. **Recorded Pipeline 100% Verified**: End-to-end processing from raw video and IMU through MediaPipe pose extraction, rolling IMU filtering, temporal synchronization, frozen Random Forest inference, episode aggregation, and clinical explanation is verified with 0 failures across 14 adversarial scenarios.
2. **Cloud Control Plane Verified**: AWS API Gateway, DynamoDB conditional state transitions, and S3 presigned upload workflows are tested and reject invalid states with strict HTTP 400/409 codes.
3. **Demo Fail-Safe Fallbacks**: Both cloud execution and deterministic local on-device execution are supported in Streamlit, with browser refresh recovery and one-click verified sample loading.
4. **Zero Model Drift**: Model SHA256 (`02a87b0a...`), 8-feature order, and threshold bands remain 100% intact.

### Known Limitations:
1. **Gate 7B Real Hardware BLOCKED**: Physical camera and phone IMU streams are not attached; live monitoring is strictly limited to replayed demonstration mode.
2. **External Video Modality Boundary**: Publicly available external gait videos (Toronto, Wellcome) are strictly video-only; multimodal FoG evaluation is confined to the Figshare dataset where synchronized 128Hz IMU and clinical labels exist.
3. **Bedrock AI Fallback**: If AWS Bedrock Claude 3 model access is not authorized on the AWS account, explanations automatically and gracefully fall back to the deterministic rule-based clinical narrative provider.
