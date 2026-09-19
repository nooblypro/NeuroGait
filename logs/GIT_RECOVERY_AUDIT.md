# NeuroGait — Safe Git Backup & Repository Recovery Audit

**Audit Date:** 2026-09-19
**Branch:** `main`
**Current HEAD:** `c7cf7b7 Initial commit`
**Remote:** `https://github.com/nooblypro/NeuroGait.git` (GitHub)
**Audit Objective:** Comprehensive inventory and classification of all untracked files, secret scanning, large-asset auditing, and recovery strategy for demo-day resilience without touching application behavior or prematurely staging unverified files.

---

## 1. Current Git State Reconnaissance

| Property | Value / Status | Verification Command |
|---|---|---|
| **Current Branch** | `main` | `git branch -vv` |
| **Tracking Remote** | `origin/main` (GitHub) | `git branch -vv` |
| **Current Commit** | `c7cf7b7` ("Initial commit") | `git log --oneline -20` |
| **Remote URL** | `https://github.com/nooblypro/NeuroGait.git` (fetch & push) | `git remote -v` |
| **Tracked Files in HEAD** | Exactly 1 file: `README.md` | `git ls-files` |
| **Modified Files** | `README.md` (modified from 1-line stub to full Phase 1 documentation) | `git status` |
| **Deleted Files** | None | `git status` |
| **Ignored Files** | `.pytest_cache/`, `.venv/`, `__pycache__/` trees | `git status --ignored` |
| **Untracked Entries** | 14 top-level directories/files (expanding to **330 untracked files**) | `git ls-files --others --exclude-standard` |

### Critical Finding
A clean clone of `https://github.com/nooblypro/NeuroGait.git` currently contains **only the initial 1-line `README.md`**. None of the source code (`src/`), tests (`tests/`), scripts (`scripts/`), UI (`app.py`), contracts (`ML_CONTRACT.md`), or gate audit reports (`logs/`) have ever been committed. **If this development machine suffered hardware loss, the entire project implementation would be lost.**

---

## 2. Complete Untracked File Classification

A total of 330 untracked files were analyzed and categorized according to the audit rubric:
- **A. MUST COMMIT:** Core source code required to execute the application and ML pipeline.
- **B. SHOULD COMMIT:** Tests, build definitions, requirements, contracts, scripts, and audit evidence.
- **C. GENERATED — IGNORE:** Ephemeral outputs, cached predictions, intermediate tensors, build zips.
- **D. LARGE DATA — IGNORE / EXTERNAL:** Raw video recordings, raw clinical IMU captures (>10MB).
- **E. SECRET / SENSITIVE — NEVER COMMIT:** Credentials, tokens, private keys, environment configs.
- **F. LOCAL ENVIRONMENT — IGNORE:** Virtual environments, IDE settings, OS caches.

### Classification Table

| Path / Pattern | Count | Category | Reason | Recommended Action |
|---|---|---|---|---|
| `app.py` | 1 | **A. MUST COMMIT** | Primary Streamlit UI application for Recorded Mode and Live PoC | Stage & Commit |
| `src/__init__.py` | 1 | **A. MUST COMMIT** | Package initialization | Stage & Commit |
| `src/contract.py` | 1 | **A. MUST COMMIT** | Strict schema validation, threshold definitions, canonical JSON contract | Stage & Commit |
| `src/episodes.py` | 1 | **A. MUST COMMIT** | Episode aggregation, window-to-episode fusion, gap bridging | Stage & Commit |
| `src/features.py` | 1 | **A. MUST COMMIT** | 8 canonical feature extraction algorithms (5 kinematic + 3 inertial) | Stage & Commit |
| `src/imu.py` | 1 | **A. MUST COMMIT** | 128Hz IMU parser, calibration, rolling window aggregation | Stage & Commit |
| `src/live_pipeline.py` | 1 | **A. MUST COMMIT** | Sliding-window live processing pipeline | Stage & Commit |
| `src/model.py` | 1 | **A. MUST COMMIT** | Model wrapper, probability calibrator, threshold inferencer | Stage & Commit |
| `src/pipeline.py` | 1 | **A. MUST COMMIT** | End-to-end recorded mode inference pipeline orchestrator | Stage & Commit |
| `src/pose.py` | 1 | **A. MUST COMMIT** | MediaPipe Tasks Python vision landmark extractor | Stage & Commit |
| `src/sync.py` | 1 | **A. MUST COMMIT** | Temporal timestamp synchronization (±0.1s tolerance) | Stage & Commit |
| `src/control_plane/lambda_handler.py` | 1 | **A. MUST COMMIT** | AWS Lambda REST API control plane implementation | Stage & Commit |
| `src/explanation/__init__.py` | 1 | **A. MUST COMMIT** | Explanation package init | Stage & Commit |
| `src/explanation/base.py` | 1 | **A. MUST COMMIT** | Base abstract explanation provider contract | Stage & Commit |
| `src/explanation/bedrock_provider.py` | 1 | **A. MUST COMMIT** | AWS Bedrock Claude 3 Haiku clinical narrative generator | Stage & Commit |
| `src/explanation/orchestrator.py` | 1 | **A. MUST COMMIT** | Fallback-aware explanation orchestrator (Bedrock $\to$ Rule) | Stage & Commit |
| `src/explanation/rule_provider.py` | 1 | **A. MUST COMMIT** | Deterministic offline clinical rule-based explanation provider | Stage & Commit |
| `src/state/__init__.py` | 1 | **A. MUST COMMIT** | State package init | Stage & Commit |
| `src/state/dynamo_store.py` | 1 | **A. MUST COMMIT** | DynamoDB conditional state transitions & concurrency control | Stage & Commit |
| `src/state/models.py` | 1 | **A. MUST COMMIT** | Pydantic data models for session state and records | Stage & Commit |
| `src/ui/__init__.py` | 1 | **A. MUST COMMIT** | UI package init | Stage & Commit |
| `src/ui/api_client.py` | 1 | **A. MUST COMMIT** | HTTP API client for AWS control plane communication | Stage & Commit |
| `src/ui/components.py` | 1 | **A. MUST COMMIT** | Streamlit UI presentation components & clinical disclaimer banner | Stage & Commit |
| `.dockerignore` | 1 | **B. SHOULD COMMIT** | ECS Docker build context exclusion rules | Stage & Commit |
| `.gitignore` | 1 | **B. SHOULD COMMIT** | Repository file exclusion rules | Stage & Commit (after update) |
| `Dockerfile` | 1 | **B. SHOULD COMMIT** | ECS Fargate container image build definition | Stage & Commit |
| `ML_CONTRACT.md` | 1 | **B. SHOULD COMMIT** | Formal contract for 8 features, thresholds, and output schema | Stage & Commit |
| `pytest.ini` | 1 | **B. SHOULD COMMIT** | Pytest runner configuration | Stage & Commit |
| `requirements.txt` | 1 | **B. SHOULD COMMIT** | Application and ML dependency manifest | Stage & Commit |
| `README.md` (modified) | 1 | **B. SHOULD COMMIT** | System overview, architecture diagram, usage instructions | Stage & Commit |
| `tests/*.py` (16 files) | 16 | **B. SHOULD COMMIT** | Full test suite (88 passing tests guaranteeing zero regression) | Stage & Commit |
| `scripts/*.py` (16 files) | 16 | **B. SHOULD COMMIT** | Verification scripts, training pipelines, stress tests | Stage & Commit |
| `logs/*.md` (20 files) | 20 | **B. SHOULD COMMIT** | Gate 0–7 audit reports, Polish, Acceptance Test reports | Stage & Commit |
| `data/external_validation/manifest.json` | 1 | **B. SHOULD COMMIT** | Provenance manifest with SHA256 checksums & URLs for external data | Stage & Commit |
| `models/fog_model.pkl` | 1 | **B. SHOULD COMMIT** | Verified ML model artifact (996 KB, SHA256 verified) | Stage & Commit (see Section 7) |
| `models/pose_landmarker_full.task` | 1 | **D. LARGE DATA / EXTERNAL** | MediaPipe model (9.0 MB, public Google asset) | Add to `.gitignore`, download script |
| `outputs/*` (24 files) | 24 | **C. GENERATED — IGNORE** | Test outputs, debug arrays, sample JSONs, `lambda_deployment.zip` | Add `outputs/*` to `.gitignore` |
| `data/raw/videos/*.mp4` (3 files) | 3 | **D. LARGE DATA — IGNORE** | Clinical patient videos (80MB, 77MB, 47MB = 204MB) | Add to `.gitignore`, external backup |
| `data/raw/imu/*.csv, *.txt` (212 files) | 212 | **D. LARGE DATA — IGNORE** | Clinical IMU files (326MB total) | Add to `.gitignore`, external backup |
| `data/raw/PDFEinfo.csv` | 1 | **D. LARGE DATA — IGNORE** | Raw Figshare clinical metadata sheet (12KB) | Add to `.gitignore`, external backup |
| `data/external_validation/*.mp4` (4 files) | 4 | **D. LARGE DATA — IGNORE** | Validation videos (95MB, 86MB, 82MB, 36MB = 299MB) | Add to `.gitignore`, external backup |
| `data/external_validation/xsens/*` (2 files) | 2 | **D. LARGE DATA — IGNORE** | Kinematic BVH (5.1MB) & CSV (1.5MB) | Add to `.gitignore`, external backup |
| `.venv/`, `.pytest_cache/`, `__pycache__/` | N/A | **F. LOCAL ENVIRONMENT** | Local Python virtualenv, compiler caches | Already ignored |

---

## 3. `.gitignore` Audit & Proposed Minimal Diff

### Deficiencies in Current `.gitignore`
1. `data/raw/Videos.zip` and `data/raw/IMU.zip` are ignored, but the unzipped directories (`data/raw/videos/`, `data/raw/imu/`, `data/external_validation/`) are **NOT ignored**! This exposes 837 MB of binary media to accidental staging.
2. `outputs/` is **NOT ignored** in git (only in `.dockerignore`). All generated run JSONs, debug numpy arrays (`.npy`), debug CSVs, and `lambda_deployment.zip` are currently untracked candidates.
3. No defensive ignores exist for secrets (`.env`, `.env.*`, `.streamlit/secrets.toml`, AWS credentials, private keys).
4. `models/*.task` (9MB MediaPipe binary) is not explicitly ignored.

### Proposed Minimal `.gitignore` (Diff View)

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -35,6 +35,27 @@ htmlcov/
 *.swp
 *.swo
 .DS_Store
+.gemini/

-# Large Raw Datasets (Raw 5GB Videos.zip, keeping small sample videos for tests)
-data/raw/Videos.zip
-data/raw/IMU.zip
+# Secrets & Local Credentials (Defensive)
+.env
+.env.*
+!.env.example
+.streamlit/secrets.toml
+*credentials*.json
+service-account*.json
+*.pem
+*.key
+
+# Large Raw Datasets & Clinical Media
+data/raw/
+data/external_validation/
+!data/external_validation/manifest.json
+data/*.zip
+
+# Public Third-Party Task Models
+models/*.task
+
+# Generated Run Outputs & Build Artifacts
+outputs/*
+!outputs/.gitkeep
```

---

## 4. Secret Scan Results

An exhaustive multi-pattern regex scan was performed across the entire repository (excluding `.git` and `.venv`).

### Scan Patterns Executed:
- AWS Access Key IDs (`AKIA[0-9A-Z]{16}`)
- AWS Secret Keys (`aws_secret_access_key = "[A-Za-z0-9/+=]{40}"`)
- Generic API keys, bearer tokens, private keys (standard PEM header patterns)
- Plaintext passwords and database credentials
- `.env` files, Streamlit secrets (`secrets.toml`), service account JSONs

### Findings:
**ZERO hardcoded secrets found.** (Findings: 0).

### Clarification on Resource ARNs in Code:
- The AWS Account ID (`955519187785`), S3 Bucket Name (`neurogait-artifacts-955519187785`), Subnet ID (`subnet-0ed8b6b6255d19fbe`), and API Gateway URL (`https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com`) appear in `src/control_plane/lambda_handler.py` as default fallback configurations.
- These are AWS resource identifiers and public API endpoints, **not credentials**.
- The Streamlit frontend client (`src/ui/api_client.py`) requires zero AWS credentials and communicates exclusively over HTTPS using signed requests handled server-side.

---

## 5. Large File Audit (> 10 MB)

All files exceeding 10 MB in size were identified and cataloged:

| Path | File Size | Data Type | Recommendation |
|---|---|---|---|
| `data/external_validation/toronto_OAW01_bottom.mp4` | **95 MB** | Video (H.264) | **DO NOT COMMIT.** External artifact; documented in `manifest.json`. |
| `data/external_validation/toronto_OAW02_bottom.mp4` | **86 MB** | Video (H.264) | **DO NOT COMMIT.** External artifact; documented in `manifest.json`. |
| `data/external_validation/toronto_OAW01_top.mp4` | **82 MB** | Video (H.264) | **DO NOT COMMIT.** External artifact; documented in `manifest.json`. |
| `data/raw/videos/PDFE01_1.mp4` | **80 MB** | Video (H.264) | **DO NOT COMMIT.** Primary demo trial. Back up externally (see Section 8). |
| `data/raw/videos/PDFE03_1.mp4` | **77 MB** | Video (H.264) | **DO NOT COMMIT.** Figshare secondary trial. Re-downloadable via script. |
| `data/raw/videos/PDFE09_1.mp4` | **47 MB** | Video (H.264) | **DO NOT COMMIT.** Figshare secondary trial. Re-downloadable via script. |
| `data/external_validation/wellcome_typical_gaits.mp4` | **36 MB** | Video (H.264) | **DO NOT COMMIT.** Internet Archive video; documented in `manifest.json`. |

### Notable Files Near 10 MB Threshold:
- `models/pose_landmarker_full.task` (**9.0 MB**): MediaPipe pose model binary.
- `data/external_validation/xsens/Xsens/OAW01.bvh` (**5.1 MB**): Motion capture skeleton file.
- `data/raw/imu/SUB01_1.txt` (**1.8 MB**): Primary demo IMU trial.
- `models/fog_model.pkl` (**996 KB**): Core scikit-learn model weight file.

---

## 6. Demo Recoverability Matrix

To determine what a fresh machine needs to reconstruct the demo if this Mac were lost:

### A. Recorded Local Demo (Offline Inference)

| Component | Role | File / Target | Status Today | Recovery Mechanism |
|---|---|---|---|---|
| Python Environment | Runtime | Python 3.10–3.13 | EXTERNAL | `brew install python@3.13 && pip install -r requirements.txt` |
| Application UI | Frontend | `app.py`, `src/ui/` | **UNTRACKED** | **MUST COMMIT to Git** |
| Inference Engine | Backend | `src/pipeline.py`, `src/` | **UNTRACKED** | **MUST COMMIT to Git** |
| FoG Model Artifact | Weights | `models/fog_model.pkl` | **UNTRACKED** | **COMMIT to Git (996KB)** or fetch from S3 |
| MediaPipe Model | Vision Task | `models/pose_landmarker_full.task` | **UNTRACKED** | Download via `curl` from Google Storage |
| Demo Video File | Input | `data/raw/videos/PDFE01_1.mp4` | **UNTRACKED** | Fetch from Figshare or S3 backup bucket |
| Demo IMU File | Input | `data/raw/imu/SUB01_1.txt` | **UNTRACKED** | Fetch from Figshare or S3 backup bucket |
| Clinical Narrative | Explanation | `src/explanation/rule_provider.py` | **UNTRACKED** | **MUST COMMIT to Git** (offline rule engine) |

### B. Recorded AWS Demo (Cloud Inference)

| Component | Role | File / Target | Status Today | Recovery Mechanism |
|---|---|---|---|---|
| Python Environment | Frontend Host | Python + `streamlit`, `requests` | EXTERNAL | `pip install streamlit requests pydantic` |
| Application UI | Frontend | `app.py`, `src/ui/` | **UNTRACKED** | **MUST COMMIT to Git** |
| API Gateway Endpoint | REST Ingress | `https://xwncaenjbd...` | **DEPLOYED IN AWS** | Persistent cloud resource (no local files needed) |
| Lambda Control Plane | Session Manager | `neurogait-control-plane` | **DEPLOYED IN AWS** | Source in `src/control_plane/lambda_handler.py` (COMMIT) |
| DynamoDB Table | State Machine | `neurogait-sessions` | **DEPLOYED IN AWS** | Persistent cloud resource |
| S3 Storage Bucket | Artifact Store | `neurogait-artifacts-955519187785` | **DEPLOYED IN AWS** | Persistent cloud resource |
| ECS Fargate Cluster | Batch Inference | `neurogait-cluster` / `neurogait-task:1` | **DEPLOYED IN AWS** | Docker image in AWS ECR (`neurogait-ml:gate2`) |
| Bedrock LLM | Clinical Narrative | `anthropic.claude-3-haiku` | **DEPLOYED IN AWS** | Managed AWS Bedrock foundation model |
| Demo Inputs | Upload Data | `PDFE01_1.mp4` + `SUB01_1.txt` | **UNTRACKED** | Fetch from S3 or local backup |

---

## 7. Model Recovery Analysis (`models/fog_model.pkl`)

- **File Path:** `models/fog_model.pkl`
- **File Size:** 996 KB (1,020,011 bytes)
- **Measured SHA256:** `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **Expected SHA256:** `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **Integrity Status:** **VERIFIED EXACT MATCH.**

### Storage Strategy Evaluation:
1. **Direct Git Commit (Recommended):**
   At only 996 KB, this model is well below GitHub's 50 MB warning threshold and 100 MB hard limit. Committing it directly guarantees zero-friction cloning on a clean presenter laptop with no third-party Git LFS requirements or cloud credentials needed.
2. **Git LFS:**
   Unnecessary overhead for a sub-megabyte file. Git LFS requires extra client tooling and bandwidth limits.
3. **External S3 Storage:**
   The file should also be mirrored to `s3://neurogait-artifacts-955519187785/models/fog_model.pkl` as an off-site cloud backup.
4. **Regeneration from Scratch:**
   Not recommended for demo recovery. Full retraining on Figshare data requires downloading 5GB and may produce minor floating-point divergence on different CPU architectures.

### Pose Landmarker Model (`models/pose_landmarker_full.task`)
- **File Size:** 9.0 MB
- **SHA256:** `4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad`
- **Recovery:** Public canonical asset maintained by Google:
  ```bash
  curl -o models/pose_landmarker_full.task \
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
  ```

---

## 8. Demo Sample Recovery Analysis

The primary demo pair consists of Subject 1 Trial 1:

| Artifact | File Path | Size | Verified SHA256 Checksum |
|---|---|---|---|
| **Demo Video** | `data/raw/videos/PDFE01_1.mp4` | 80 MB | `3981fe78d3f2ec50dc2c840bfbd3133d688817bb171c0aae374afd9a7e958c53` |
| **Demo IMU** | `data/raw/imu/SUB01_1.txt` | 1.8 MB | `43367dec5a2bb59cc6f828b6396630d50ceed12da6533bdec00f6f11e53c9acf` |

### Recovery Plan:
1. **Do NOT commit `PDFE01_1.mp4` to Git:** At 80 MB, committing video binaries permanently pollutes git history and risks rejection or slow clones.
2. **Authoritative Source:** Public Figshare dataset (DOI: `10.6084/m9.figshare.14984667`).
3. **Presenter Offline Backup:**
   Prior to demo day, copy `PDFE01_1.mp4` and `SUB01_1.txt` to:
   - A dedicated folder on an external USB flash drive.
   - S3 Demo Bucket:
     ```bash
     aws s3 cp data/raw/videos/PDFE01_1.mp4 s3://neurogait-artifacts-955519187785/demo_assets/PDFE01_1.mp4
     aws s3 cp data/raw/imu/SUB01_1.txt s3://neurogait-artifacts-955519187785/demo_assets/SUB01_1.txt
     ```

---

## 9. Source Completeness Check

The following minimal source tree is required and sufficient to rebuild, test, and run the entire NeuroGait system:

```
NeuroGait/
├── .dockerignore
├── .gitignore
├── Dockerfile
├── ML_CONTRACT.md
├── README.md
├── app.py
├── pytest.ini
├── requirements.txt
├── models/
│   └── fog_model.pkl
├── data/
│   └── external_validation/
│       └── manifest.json
├── src/
│   ├── __init__.py
│   ├── contract.py
│   ├── episodes.py
│   ├── features.py
│   ├── imu.py
│   ├── live_pipeline.py
│   ├── model.py
│   ├── pipeline.py
│   ├── pose.py
│   ├── sync.py
│   ├── control_plane/
│   │   └── lambda_handler.py
│   ├── explanation/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── bedrock_provider.py
│   │   ├── orchestrator.py
│   │   └── rule_provider.py
│   ├── state/
│   │   ├── __init__.py
│   │   ├── dynamo_store.py
│   │   └── models.py
│   └── ui/
│       ├── __init__.py
│       ├── api_client.py
│       └── components.py
├── tests/
│   ├── conftest.py
│   ├── test_contract.py
│   ├── test_control_plane.py
│   ├── test_episodes.py
│   ├── test_explanation_provider.py
│   ├── test_features.py
│   ├── test_imu.py
│   ├── test_live_pipeline.py
│   ├── test_live_pipeline_edge_cases.py
│   ├── test_model.py
│   ├── test_pipeline.py
│   ├── test_pose.py
│   ├── test_start_inference_concurrency.py
│   ├── test_state_machine.py
│   ├── test_sync.py
│   └── test_ui_api_client.py
├── scripts/
│   ├── download_dataset.py
│   ├── e2e_gate3_test.py
│   ├── e2e_gate5_test.py
│   ├── independent_gate7a_parity.py
│   ├── independent_gate7b_verification.py
│   ├── predict.py
│   ├── run_external_video_stress_test.py
│   ├── stress_test_ml_pipeline.py
│   ├── test_gate7b_hardware.py
│   ├── train.py
│   ├── verify_complete_recorded_pipeline.py
│   ├── verify_external_fog_dataset.py
│   ├── verify_external_fog_dataset_adversarial.py
│   ├── verify_external_validation.py
│   ├── verify_external_video_stress.py
│   └── verify_gate6_ui.py
└── logs/
    ├── DEMO_ACCEPTANCE_TEST_REPORT.md
    ├── EXTERNAL_DATA_VALIDATION.md
    ├── EXTERNAL_FOG_DATASET_ADVERSARIAL_AUDIT.md
    ├── EXTERNAL_FOG_DATASET_SEARCH.md
    ├── EXTERNAL_VIDEO_STRESS_TEST.md
    ├── FINAL_DEMO_AUDIT.md
    ├── FINAL_DEMO_POLISH.md
    ├── FINAL_OPUS_SYSTEM_AUDIT.md
    ├── GATE_1_CONTAINERIZATION.md
    ├── GATE_2_AWS_ML.md
    ├── GATE_3_CONTROL_PLANE_S3.md
    ├── GATE_4_EXPLANATION_PROVIDER.md
    ├── GATE_5_DYNAMODB_STATE.md
    ├── GATE_6_RECORDED_UI.md
    ├── GATE_7A_LOCAL_LIVE_POC.md
    ├── GATE_7A_REMEDIATION.md
    ├── GATE_7B_REAL_HARDWARE.md
    ├── GIT_RECOVERY_AUDIT.md
    ├── LOCAL_AWS_CONSISTENCY_AUDIT.md
    ├── PHASE_0_ML_FOUNDATION.md
    └── PRE_DEMO_HARDENING.md
```

All items listed above are present on disk, intact, and pass all 88 unit and integration tests.

---

## 10. Exact Staging & Execution Plan

### A. Proposed Commit Set (Total: 80 files)
- **Root Configurations & Entrypoints (8 files):**
  `README.md`, `app.py`, `Dockerfile`, `.dockerignore`, `.gitignore`, `ML_CONTRACT.md`, `pytest.ini`, `requirements.txt`
- **Core Production Source (22 files):**
  All files in `src/`
- **Comprehensive Test Suite (16 files):**
  All files in `tests/`
- **Automation & Verification Scripts (16 files):**
  All files in `scripts/`
- **Architectural & Gate Audit Reports (21 files):**
  All files in `logs/` (including this recovery audit)
- **Model Weight Artifact (1 file):**
  `models/fog_model.pkl` (996 KB)
- **External Dataset Provenance (1 file):**
  `data/external_validation/manifest.json`

### B. Explicitly Ignored Set
- `data/raw/` (all 204 MB videos, 326 MB IMU files, metadata)
- `data/external_validation/*.mp4`, `*.bvh`, `*.csv`
- `models/pose_landmarker_full.task` (9.0 MB Google asset)
- `outputs/*` (all 24 generated output JSONs, debug numpy traces, CSVs, build zips)
- `.venv/`, `.pytest_cache/`, `__pycache__/`, `.DS_Store`

### C. External Backup Required
1. `data/raw/videos/PDFE01_1.mp4` (SHA256: `3981fe78...`)
2. `data/raw/imu/SUB01_1.txt` (SHA256: `43367dec...`)
3. `models/fog_model.pkl` (SHA256: `02a87b0a...` — also committed to Git)

### D. Do NOT Commit
- Any raw MP4 video files under `data/`
- Any ephemeral run files under `outputs/`
- `outputs/lambda_deployment.zip`
- `outputs/debug/`

---

## 11. Remote Safety Check

- **Remote Alias:** `origin`
- **Fetch URL:** `https://github.com/nooblypro/NeuroGait.git`
- **Push URL:** `https://github.com/nooblypro/NeuroGait.git`
- **Hosting Provider:** GitHub
- **Safety Status:** Configured correctly. No foreign or unexpected remotes detected. Pushing is currently withheld until user confirmation.

---

## 12. Residual Risks & Recommended Next Sequence

### Residual Risks
1. **Risk of Accidental `git add .`:**
   If a user executes `git add .` before updating `.gitignore`, 837 MB of media will be staged into git index, causing git lockup and potential rejection on GitHub push.
2. **Model Missing on Fresh Clone if Ignored:**
   If `models/fog_model.pkl` is not committed, a fresh clone cannot run Local Mode without a separate manual download step. Committing it (996KB) completely mitigates this.
3. **Presentation Failure due to Missing Sample Data:**
   If the presenter forgets to copy `PDFE01_1.mp4` and `SUB01_1.txt` to the presentation laptop, neither local nor remote upload can be demonstrated live.

### Recommended Next Command Sequence (FOR USER REVIEW ONLY)

```bash
# 1. Update .gitignore with proposed additions
# (Edit .gitignore as specified in Section 3)

# 2. Verify git status respects ignore rules
git status

# 3. Stage verified source code, tests, scripts, logs, and core model
git add README.md .dockerignore .gitignore Dockerfile ML_CONTRACT.md app.py pytest.ini requirements.txt
git add src/ tests/ scripts/ logs/
git add models/fog_model.pkl
git add data/external_validation/manifest.json

# 4. Confirm staged files match the 80 intended files
git status --short

# 5. Commit with atomic audit description
git commit -m "feat: complete NeuroGait system implementation, tests, contracts, and gate audits"

# 6. (Optional / When Ready) Push to origin
# git push origin main
```

**STOPPED.** No `git add`, `git commit`, or `git push` has been executed. Staging plan is awaiting your explicit review and approval.
