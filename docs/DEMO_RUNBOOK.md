# NeuroGait Demo Runbook

**Document Version:** 1.0.0
**Target Environment:** macOS (Local Inference) & AWS Cloud (`ap-south-1`)
**Primary Demo Mode:** Recorded Analysis Mode (Verified Patient Trial `PDFE01_1.mp4` + `SUB01_1.txt`)
**Repository Branch / Commit:** `main` @ `27d65b7`

---

## 1. Demo Objective

NeuroGait demonstrates an end-to-end multimodal machine learning assessment pipeline for detecting **Freezing of Gait (FoG)** episodes in Parkinson's Disease by integrating:
1. **Synchronized video-derived 2D pose kinematics** (MediaPipe Tasks Python, 29.98 FPS)
2. **Wearable inertial sensor streams** (Tri-axial accelerometer & gyroscope, 128 Hz)

### Scope & Clinical Framing
- **Investigational Prototype**: NeuroGait is an engineering prototype designed for objective clinical research assistance and temporal gait segment analysis.
- **Non-Diagnostic**: The system identifies statistical anomalies and feature deviations relative to patient baseline; it does **not** provide clinical diagnosis, disease staging, or prescriptive medical treatment recommendations.

---

## 2. Demo Architecture

The demonstration exercises the actual, verified production cloud architecture and its offline deterministic fallback:

```
                  ┌─────────────────────────────────────────┐
                  │          Streamlit Web Frontend         │
                  │                 (app.py)                │
                  └────────────────────┬────────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼ (Cloud Mode)                                ▼ (Offline Local Fallback)
  ┌───────────────────────────┐                 ┌───────────────────────────┐
  │   Amazon API Gateway      │                 │  Deterministic Local ML   │
  │     (HTTP REST API)       │                 │  (models/fog_model.pkl    │
  └─────────────┬─────────────┘                 │   scikit-learn Pipeline)  │
                ▼                               └─────────────┬─────────────┘
  ┌───────────────────────────┐                               │
  │  Lambda Control Plane     │                               │
  │(neurogait-control-plane)  │                               │
  └──────┬──────────────┬─────┘                               │
         │              │                                     │
         ▼              ▼                                     │
  ┌─────────────┐ ┌─────────────┐                             │
  │  Amazon S3  │ │ DynamoDB    │                             │
  │ (Artifacts) │ │ (Sessions)  │                             │
  └──────┬──────┘ └─────────────┘                             │
         │                                                    │
         ▼                                                    │
  ┌───────────────────────────┐                               │
  │   AWS ECS Fargate Task    │                               │
  │  (Docker Linux x86_64     │                               │
  │   neurogait-ml:gate2)     │                               │
  └─────────────┬─────────────┘                               │
                ▼                                             ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                           Canonical JSON Output                         │
  │          (FoG Episodes, Confidence Scores, Statistical Primary Cues)    │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       │
                                       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                     Clinical Narrative Explanation                      │
  │   AWS Bedrock (Claude 3 Haiku)  ──► Fallback: Deterministic Rule Engine │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Demo Assets

The primary demonstration evaluates patient trial **Subject 1, Trial 1** from the verified Figshare Parkinson's turning-task dataset (DOI: `10.6084/m9.figshare.14984667`).

| Asset File | Size | Verified SHA256 Checksum | Location / Role |
|---|---|---|---|
| `data/raw/videos/PDFE01_1.mp4` | **80 MB** | `3981fe78d3f2ec50dc2c840bfbd3133d688817bb171c0aae374afd9a7e958c53` | 120s patient video @ 29.98 FPS |
| `data/raw/imu/SUB01_1.txt` | **1.8 MB** | `43367dec5a2bb59cc6f828b6396630d50ceed12da6533bdec00f6f11e53c9acf` | 128 Hz accelerometer & gyro telemetry |
| `models/pose_landmarker_full.task` | **9.0 MB** | `4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad` | MediaPipe Tasks Python pose detector |

### Asset Storage Policy
- **Excluded from Git**: These binary artifacts are deliberately ignored in Git to prevent repository bloat (>90 MB total media).
- **Committed Model**: The verified classification model `models/fog_model.pkl` (996 KB, SHA256: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`) **is** tracked in Git and present upon clone.
- **S3 Mirror Target**: `s3://neurogait-artifacts-955519187785/demo_assets/`

---

## 4. Demo Flow (Step-by-Step Operator Guide)

Use the exact UI labels present in the Streamlit application:

1. **Start the Application**:
   ```bash
   .venv/bin/streamlit run app.py
   ```
   Open browser at `http://localhost:8501`.

2. **Verify Connectivity in Sidebar**:
   - Confirm sidebar displays: `🟢 Cloud Control Plane: Connected`
   - Region: `ap-south-1`, Service: `neurogait-control-plane`.

3. **Select Operating Mode**:
   - Ensure mode is set to: `📁 Recorded Analysis Mode (Primary Demo)`.
   - *(Do not select Live Mode; live streaming requires physical test bench hardware).*

4. **Select Trial Data Source**:
   - Select radio option: `⭐ Run Verified Demo Sample (PDFE01_1 Patient Trial)`.
   - *(Alternative for custom upload)*: Select `📤 Upload Custom Patient Video & IMU Files`, then drag-and-drop `PDFE01_1.mp4` into `1. Kinematic Video (.mp4)` and `SUB01_1.txt` into `2. Inertial IMU Sensor (.txt, .csv)`.

5. **Select Execution Environment**:
   - Select: `☁️ AWS Cloud Pipeline (Production: API Gateway + Lambda + S3 + ECS Fargate + DynamoDB)`.
   - *(If showcasing offline fallback, toggle to `💻 Local Deterministic Engine`).*

6. **Initiate Analysis**:
   - Click the primary action button: `🚀 Run Verified Demo Analysis`.

7. **Observe Cloud Pipeline Execution**:
   - Status transitions from `CREATED` $\to$ `UPLOADED` $\to$ `PROCESSING` (Fargate Task Dispatched).
   - Polling queries DynamoDB until state reaches `COMPLETE`.

8. **Review Results Dashboard**:
   - **Executive Metric Cards**: Total Duration (120s), Episodes Detected, Mean FoG Confidence, Latency.
   - **Clinical Disclaimer Banner**: Verify `⚠️ Investigational ML Prototype — Not for Primary Diagnostic Use`.
   - **State Distribution Breakdown**:
     - `FoG Episodes (p >= 0.60)`: High-probability freezing blocks.
     - `Borderline Episodes (0.40 <= p < 0.60)`: Ambiguous gait transitions.
     - `Normal Segments (p < 0.40)`: Fluid ambulatory locomotion.
   - **Primary Cue Attribution**: Identifies maximum standardized statistical deviation (e.g., `Acceleration RMS (accel_rms)` or `Mediolateral Gyro Variance (gyro_x_var)`).
   - **Clinical Narrative Explanation**: Displays synthesized breakdown with clear attribution.

---

## 5. Presentation Script (3–5 Minutes)

| Timing | Section | Spoken Script / Talking Track |
|---|---|---|
| **0:00–0:40** | **Clinical & Engineering Problem** | *"Freezing of Gait is one of the most disabling symptoms of Parkinson's Disease—patients suddenly feel their feet are glued to the floor, often triggering catastrophic falls. Clinicians currently rely on retrospective patient recall or subjective rating scales. Our goal with NeuroGait is to provide objective, millisecond-accurate temporal detection by pairing computer vision with wearable motion sensors."* |
| **0:40–1:20** | **Multimodal Input & Synchronization** | *"Single-modality systems fail in the real world: video alone suffers from occlusions, while IMU sensors alone miss subtle joint kinematics. NeuroGait synchronizes high-speed 29.98 FPS video pose tracking with 128 Hz tri-axial inertial sensor streams using nearest-timestamp alignment within a strict ±0.1-second boundary."* |
| **1:20–2:30** | **Live Application Demonstration** | *(Action: Click `🚀 Run Verified Demo Analysis`)*<br>*"Here in our Streamlit dashboard, we are analyzing a 120-second clinical turning task trial. When I trigger analysis, the client initializes a secure session with AWS API Gateway, uploads artifacts via presigned S3 URLs, and dispatches a serverless ECS Fargate task. The session progresses through our DynamoDB state machine from UPLOADED to PROCESSING to COMPLETE. Looking at the results, the model identifies discrete freezing episodes, distinct from borderline transition zones and normal walking."* |
| **2:30–3:20** | **ML Architecture & Canonical Contract** | *"Under the hood, our pipeline extracts exactly 8 immutable features: 5 kinematic joint velocities and knee angles, combined with 3 inertial features including Anteroposterior acceleration RMS and rotational variances. A trained Random Forest classifier produces calibrated probabilities. Episodes are merged across a 1.0-second temporal tolerance, outputting a strictly validated JSON contract."* |
| **3:20–4:00** | **AWS Cloud Architecture** | *"NeuroGait's cloud architecture is built for zero-trust clinical scale: the browser requires zero AWS credentials. Everything is authenticated through serverless Lambda control planes and IAM-scoped roles. Heavy MediaPipe and OpenCV computation runs isolated inside a hardened Docker container on ECS Fargate, while AWS Bedrock provides automated clinical narrative summaries with an immediate deterministic rule fallback."* |
| **4:00–5:00** | **Engineering Rigor, Safety & Limitations** | *"We hold ourselves to rigorous engineering standards: our codebase is protected by 97 automated tests with 100% pass rates across contracts, state machines, and concurrency limits. As an investigational prototype, we make no diagnostic claims: borderline bands represent statistical confidence thresholds, not medical diagnoses. NeuroGait demonstrates how multimodal cloud engineering can turn raw clinical sensor data into structured neurological insights."* |

---

## 6. Important Technical Talking Points

- **Temporal Synchronization**: Nearest-timestamp alignment pairing 29.98 FPS camera frames with 128.0 Hz IMU rows ($\Delta t \le 100\text{ ms}$).
- **The 8 Canonical Features**:
  1. `left_ankle_velocity` (displacement rate)
  2. `right_ankle_velocity` (displacement rate)
  3. `left_knee_angle` (joint angle degrees)
  4. `right_knee_angle` (joint angle degrees)
  5. `stride_width` (inter-ankle normalized Euclidean distance)
  6. `accel_rms` (root-mean-square of anteroposterior acceleration)
  7. `gyro_x_var` (mediolateral angular velocity variance)
  8. `gyro_z_var` (superior-inferior angular velocity variance)
- **Classifier & Calibration**: Scikit-Learn `RandomForestClassifier` (50 estimators) operating on `StandardScaler`-normalized features.
- **Threshold Decision Bands**:
  - $p \ge 0.60 \implies$ **FoG** (Freezing of Gait)
  - $0.40 \le p < 0.60 \implies$ **Borderline** *(decision confidence band, not a medical classification)*
  - $p < 0.40 \implies$ **Normal Gait**
- **Primary Cue Attribution**: Identifies the feature exhibiting maximum standardized deviation from the patient's median gait baseline *(statistical attribution heuristic, not clinical causality)*.
- **Explanation Fallback**: Orchestrator queries Bedrock Claude 3 Haiku; if network, credentials, or AWS quotas reject the call, it falls back within 0.15 ms to the deterministic clinical rule provider.

---

## 7. Verification Evidence & Audits

All claims are backed by executable audit reports stored in [`logs/`](file:///Users/shriram/Documents/Projects/NeuroGait/logs):
- **Automated Test Suite**: **97 passed / 0 failed** across all gates (`tests/`).
- **Container Parity**: `logs/GATE_1_CONTAINERIZATION.md` & `logs/GATE_2_AWS_ML.md` (Docker Linux x86_64 verified in ECR).
- **Control Plane & S3**: `logs/GATE_3_CONTROL_PLANE_S3.md` (Zero credential exposure, presigned URLs).
- **DynamoDB State Integrity**: `logs/GATE_5_DYNAMODB_STATE.md` (Strict state machine: `CREATED` $\to$ `UPLOADED` $\to$ `PROCESSING` $\to$ `COMPLETE`).
- **Clean-Room Demo Test**: `logs/DEMO_ACCEPTANCE_TEST_REPORT.md` (Full E2E verification of recorded demo).
- **Adversarial System Audit**: `logs/FINAL_OPUS_SYSTEM_AUDIT.md` (28-section exhaustive vulnerability audit).

---

## 8. Known Limitations (Honest Disclosure)

1. **Gate 7B Real Hardware**: Physical live streaming from a phone IMU + camera bench is **not** part of this demonstration. Gate 7B remains marked as BLOCKED due to macOS TCC camera gating and absence of a paired physical hardware stream.
2. **Platform Numerical Differences**: MediaPipe Tasks on macOS (Metal GPU delegate) produces slightly different landmark float coordinates than Linux x86_64 (CPU XNNPACK). AWS ECS Fargate is the authoritative production reference.
3. **Primary Cue Nature**: The primary cue is an algorithmic statistical deviation score, not a validated biological etiology.
4. **Borderline Band**: Borderline indicates model uncertainty ($0.40 \le p < 0.60$), not a distinct neurological gait state.

---

## 9. Failure Recovery Guide

| Symptom | Cause | Immediate Recovery Action |
|---|---|---|
| **Upload Rejected (HTTP 400)** | Invalid file extension or size | Verify video is `.mp4` ($\le 500\text{ MB}$) and IMU is `.txt`/`.csv` ($\le 50\text{ MB}$). |
| **AWS Processing Timeout (>3 min)** | ECS cold start or Fargate capacity delay | Click `🔄 Reset Assessment` in sidebar and switch to `💻 Local Deterministic Engine`. |
| **Bedrock Explanation Unavailable** | AWS Bedrock region authorization | Handled automatically: system silently uses deterministic rule explanation provider without error. |
| **UI Browser Refreshed** | Browser tab reloaded during inference | Paste original `session_id` into URL query parameters (`?session_id=...`) to resume polling. |
| **Control Plane Offline (Red Icon)** | API Gateway endpoint unreachable | Check local internet connection; fallback immediately to Local Mode. |

---

## 10. Emergency Fallback: Offline Local Mode

If internet or AWS connectivity fails entirely:
1. In the Streamlit UI, under **Execution Environment**, select:
   `💻 Local Deterministic Engine (Offline Demo Mode / models/fog_model.pkl)`
2. Click `🚀 Run Verified Demo Analysis`.
3. The local pipeline executes directly on-device using `models/fog_model.pkl` in ~58 seconds.
4. *Talking point*: Explain that NeuroGait was intentionally architected with complete dual-path execution—heavy cloud scale on AWS Fargate paired with an edge-capable local inference engine.

---

## 11. Pre-Demo Checklist

- [ ] Presentation laptop battery charged ($\ge 80\%$) and connected to power.
- [ ] Active Wi-Fi connection verified.
- [ ] Terminal opened to `/Users/shriram/Documents/Projects/NeuroGait`.
- [ ] Virtual environment activated: `source .venv/bin/activate`.
- [ ] Test suite verified clean: `.venv/bin/pytest -q` (97 passed).
- [ ] Demo assets verified on disk:
  - `data/raw/videos/PDFE01_1.mp4` exists (80 MB)
  - `data/raw/imu/SUB01_1.txt` exists (1.8 MB)
  - `models/pose_landmarker_full.task` exists (9.0 MB)
  - `models/fog_model.pkl` exists (996 KB)
- [ ] Streamlit launched: `.venv/bin/streamlit run app.py`.
- [ ] Browser opened to `http://localhost:8501`.
- [ ] Sidebar shows: `🟢 Cloud Control Plane: Connected`.
- [ ] Backup copy of `PDFE01_1.mp4` and `SUB01_1.txt` stored on USB drive or desktop.
