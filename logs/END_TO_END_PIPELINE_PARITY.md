# NeuroGait Production Runtime Canonicalization & Parity Report

**Execution Date**: 2026-09-20  
**Target Recording**: `PDFE31_1` (Video: `PDFE31_1.mp4`, IMU: `SUB31_1.txt`)  
**Deployment Revision**: AWS ECS `neurogait-task:2` (`neurogait-ml:parity-v1`)  
**Production Reference Artifact**: `tests/fixtures/pdfe31_1_production_reference.json`  
**Investigator**: Antigravity Diagnostic & Deployment Agent  

---

## Executive Status Verdict

```
PRODUCTION RUNTIME PARITY VERIFIED
```

> [!IMPORTANT]
> **Production Canonical Runtime Invariant**:  
> $$\mathbf{\text{Local Docker (Linux aarch64)} \equiv \text{AWS ECS Fargate} \equiv \text{Backend Canonical Output} \equiv \text{Frontend Rendered Presentation}}$$
> 
> Cross-platform exact parity between native macOS Darwin and Linux ARM64 is neither claimed nor required. Local macOS execution is explicitly designated as **development-only**. The deployed Linux ARM64 container is the sole authoritative production reference.

---

## 1. Input Parity Verification

Byte-level verification confirmed 100% byte-identity across all input artifacts:

| Asset | Local Path | S3 Object Key (`neurogait-artifacts-955519187785`) | SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Video** | `/Users/shriram/Documents/GAIT videos/PDFE31_1.mp4` | `inputs/0afb1001-b57b-48b7-b4ed-e70a1847e435/video.mp4` | `631eda97ded7c42d8be66220ffe0eeb7fc778aca5b225383338002203d0ab7a1` | **BYTE-IDENTICAL** |
| **IMU** | `data/raw/imu/SUB31_1.txt` | `inputs/0afb1001-b57b-48b7-b4ed-e70a1847e435/imu.txt` | `01961610728deaa4bb6a97424d241da686a0f6f03019a385be15feacbb56c1c8` | **BYTE-IDENTICAL** |

Both AWS input objects were confirmed to have been created directly from the authoritative local raw files with zero modification.

---

## 2. Model Parity Verification

- **Model Artifact**: `models/fog_model.pkl`
- **Expected SHA-256**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **Local SHA-256**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **ECR Image SHA-256** (`neurogait-ml:parity-v1` in `neurogait-task:2`):
  `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **MediaPipe Pose Model**: `models/pose_landmarker_full.task`
  - Local SHA-256: `4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad`
  - Container SHA-256: `4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad`

Status: **FROZEN & 100.00% UNMODIFIED**.

---

## 3. Pinned Production Runtime Environment

The production container explicitly pins all ML and inference dependencies:

| Component | Pinned Version in Production Container (`neurogait-ml:parity-v1`) | Execution Role |
| :--- | :--- | :--- |
| **Base OS** | Debian 12 (Bookworm) `glibc 2.41` on Linux aarch64 | Container runtime |
| **Python** | `3.11.16` (GCC 14.2.0) | Language runtime |
| **MediaPipe** | `1.0.1` | TensorFlow Lite XNNPACK CPU Delegate |
| **OpenCV** | `5.0.0.93` (`opencv-python-headless`) | Linux ffmpeg libavcodec YUV420p decoding |
| **scikit-learn** | `1.9.1` | Random Forest classifier inference |
| **NumPy** | `2.4.6` | Numerical linear algebra |
| **Pandas** | `3.0.6` | Data framing & time-series rolling operations |
| **SciPy** | `1.17.1` | Scientific routines |
| **Joblib** | `1.6.0` | Model artifact deserialization |

---

## 4. Container → AWS ECS Determinism

The canonical inference pipeline was executed inside the local Docker container (`neurogait-ml:parity-v1`) and through the live deployed AWS ECS Fargate task (`neurogait-task:2`):

| Episode Attribute | Local Docker Container (`parity-v1`) | AWS ECS Fargate (`neurogait-task:2`) | Parity Status |
| :--- | :--- | :--- | :--- |
| **Total Episodes** | 76 | 76 | **100% BIT-EXACT MATCH** |
| **FoG Episodes** | 27 | 27 | **100% BIT-EXACT MATCH** |
| **Borderline Intervals** | 24 | 24 | **100% BIT-EXACT MATCH** |
| **Normal Segments** | 25 | 25 | **100% BIT-EXACT MATCH** |
| **Pred 1 Boundary** | `55.508s – 57.608s` (FoG) | `55.508s – 57.608s` (FoG) | **100% BIT-EXACT MATCH** |
| **Pred 1 Confidence** | 0.9018 (90.18%) | 0.9018 (90.18%) | **100% BIT-EXACT MATCH** |
| **Pred 1 Primary Cue**| `gyro_z_var` | `gyro_z_var` | **100% BIT-EXACT MATCH** |
| **Pred 2 Boundary** | `58.008s – 61.208s` (FoG) | `58.008s – 61.208s` (FoG) | **100% BIT-EXACT MATCH** |
| **Pred 2 Confidence** | 0.8898 (88.98%) | 0.8898 (88.98%) | **100% BIT-EXACT MATCH** |
| **Pred 2 Primary Cue**| `gyro_z_var` | `gyro_z_var` | **100% BIT-EXACT MATCH** |
| **Data Mode** | `real` | `real` | **100% BIT-EXACT MATCH** |

Zero discrepancies across all 76 episodes and all canonical attributes:
$$\max |X_{\text{Docker}} - X_{\text{AWS}}| = 0.000000$$

---

## 5. Documented Cross-Platform Numerical Divergence (macOS vs Linux)

Local macOS execution produces 75 intervals with first FoG onset at `55.408s`, whereas the production Linux container produces 76 intervals with first FoG onset at `55.508s`.

### Diagnostic Intermediate Analysis:
1. **Video Metadata (Stage A)**: Exact match (FPS = 29.97834, 3606 frames, 120.287s).
2. **IMU Rolling Features (Stage D)**: Bit-identical across all 1,190 rows ($\Delta \le 7.1 \times 10^{-15}$).
3. **Synchronization (Stage E)**: Bit-identical timestamps ($t_0 = 1.0078125s, \dots, t_{1189} = 119.9078125s$, 0 dropped rows).
4. **Scaler (Stage G)**: Exact match across all means and scales.
5. **Pose Extraction (Stage B)**:
   - macOS Darwin executes MediaPipe `0.10.35` utilizing Apple's Metal GPU delegate (`GL 2.1 Metal`) and AVFoundation video decoding.
   - Linux aarch64 executes MediaPipe `1.0.1` utilizing TensorFlow Lite XNNPACK CPU instructions and Linux ffmpeg decoding.
   - Subtle RGB pixel decoding variations ($\Delta \le 3$ levels) and GPU shader vs CPU SIMD floating-point accumulations produce small coordinate variations ($\Delta \approx 0.01$–$0.05$).
6. **Focus Region First Divergence ($t_{\text{end}} = 56.408s$)**:
   - Spans $[55.408s, 56.408s]$.
   - In Local macOS: $p = 0.8209 \ge 0.60 \rightarrow$ `FoG`. Elementary interval $[55.408s, 55.508s]$ is classified as FoG, beginning the episode at `55.408s`.
   - In Linux / AWS: $p = 0.4032 < 0.60 \rightarrow$ `Borderline`. Elementary interval $[55.408s, 55.508s]$ is classified as Borderline, delaying the FoG onset to `55.508s` where window $56.508s$ starts ($p = 0.9803$, FoG).
7. **The +1 Normal Interval ($50.208s – 50.608s$)**:
   - In Local macOS: Window $50.908s$ ($p=0.4944$, Borderline) bridges the span into a single Borderline episode `[50.008, 50.608s]`.
   - In Linux / AWS: Windows $50.308s$–$50.608s$ are all low-probability Normal windows ($p \le 0.1564$), and window $50.908s$ is Normal ($p=0.0300$). As a result, the span $[50.208s, 50.608s]$ forms an independent Normal interval, giving 25 Normal intervals in AWS vs 24 locally.

**Conclusion**: This divergence is a deterministic property of cross-platform MediaPipe / OpenCV execution. It does not affect deployed AWS determinism because the AWS production runtime is fixed to the pinned Linux ARM64 container.

---

## 6. Production Reference Fixture

Generated directly from the verified container execution:
- **Fixture Path**: [`tests/fixtures/pdfe31_1_production_reference.json`](file:///Users/shriram/Documents/Projects/NeuroGait/tests/fixtures/pdfe31_1_production_reference.json)
- **Metadata Path**: [`tests/fixtures/pdfe31_1_production_reference.meta.json`](file:///Users/shriram/Documents/Projects/NeuroGait/tests/fixtures/pdfe31_1_production_reference.meta.json)
- **Provenanced Digests**:
  - Image Tag: `955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:parity-v1`
  - Image Digest: `sha256:9ef0154fbd342c85d29a9e09f9ca7b6375dd6eeeb0046d2409c9ee1e768993f9`
  - Model SHA-256: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
  - Pose Model SHA-256: `4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad`
  - Video SHA-256: `631eda97ded7c42d8be66220ffe0eeb7fc778aca5b225383338002203d0ab7a1`
  - IMU SHA-256: `01961610728deaa4bb6a97424d241da686a0f6f03019a385be15feacbb56c1c8`

---

## 7. Frontend Presentation Fidelity

Inspected live via browser subagent on [http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com/](http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com/):

- **Total Intervals Rendered**: **76** (Matches AWS Canonical)
- **FoG Count**: **27** (Matches AWS Canonical)
- **Borderline Count**: **24** (Matches AWS Canonical)
- **Normal Count**: **25** (Matches AWS Canonical)
- **Longest FoG Episode**: `106.71s – 112.81s` (6.10s duration, 79.4% confidence)
- **Dominant Model Cue**: `gyro_z_var` (Matches AWS Canonical)
- **Target Episodes Rendered**:
  - `55.51s – 57.61s` (FoG, 90.2% confidence, cue: `gyro_z_var`)
  - `58.01s – 61.21s` (FoG, 89.0% confidence, cue: `gyro_z_var`)
- **Rendered Clinical Narrative**:
  > *"The recording contained 76 non-overlapping classified intervals. The model classified 27 intervals as FoG, 24 as Borderline, and 25 as Normal. Total FoG duration was 69.10 seconds (57.6% burden). The longest FoG interval spanned from 106.71s to 112.81s (6.10s duration, confidence 79.4%). The dominant model-derived cue across FoG intervals was `gyro_z_var`. These model-derived feature cues represent statistical associations within the model output and do not imply clinical causation or diagnosis."*

The frontend strictly preserves the backend's canonical episodes without recomputing probabilities, reclassifying intervals, or adjusting boundaries.

---

## 8. Verification & Regression Test Summary

1. **Python End-to-End Parity Tests** ([`tests/test_end_to_end_parity.py`](file:///Users/shriram/Documents/Projects/NeuroGait/tests/test_end_to_end_parity.py)):
   - `test_frozen_model_hash_integrity`: **PASSED**
   - `test_frozen_pose_model_hash_integrity`: **PASSED**
   - `test_canonical_episode_serialization_parity`: **PASSED**
   - `test_json_roundtrip_fidelity`: **PASSED**
   - `test_production_reference_fixture_schema`: **PASSED**
   - `test_aws_output_matches_production_reference`: **PASSED**
   - `test_container_output_matches_production_reference`: **PASSED**
   - `test_cross_platform_numerical_divergence_documented`: **PASSED**
   - Local: `8/8 PASSED` in 0.03s.
   - Container (`neurogait-ml:parity-v1` on Linux aarch64): `8/8 PASSED` in 0.03s.

2. **Frontend Timeline Aggregator Tests** ([`tests/test_timeline_aggregator.js`](file:///Users/shriram/Documents/Projects/NeuroGait/tests/test_timeline_aggregator.js)):
   - Empty input handling: **PASSED**
   - Canonical field preservation: **PASSED**
   - Chronological sorting: **PASSED**
   - Local cached baseline parity: **PASSED**
   - Production reference fixture parity (76 intervals, Pred 1: 55.508s, Pred 2: 58.008s): **PASSED**
   - `5/5 PASSED`.

3. **Baseline ML Validation Tests**:
   - `pytest tests/test_ground_truth_validation.py tests/test_pipeline.py -v`: `13/13 PASSED` in 9.26s.

---

## 9. Final Architecture Invariant

```
========================================================================================
PRODUCTION CANONICAL PIPELINE INVARIANT:

  PDFE31_1 (mp4 + imu)
         │
         ▼
  AWS ECS Fargate Task (neurogait-task:2)
  [Linux aarch64 / Python 3.11 / MediaPipe 1.0.1 / XNNPACK CPU]
         │
         ▼
  Canonical Predictions JSON (outputs/0afb1001-b57b-48b7-b4ed-e70a1847e435/predictions.json)
  [76 total intervals | 27 FoG | 24 Borderline | 25 Normal | Pred 1: 55.508–57.608s]
         │
         ▼ (100% Exact Match)
  Local Docker Container (neurogait-ml:parity-v1)
         │
         ▼ (100% Exact Match)
  Production Reference Fixture (tests/fixtures/pdfe31_1_production_reference.json)
         │
         ▼ (100% Exact Match)
  Frontend Presentation (S3 Web Client)
  [76 non-overlapping classified intervals displayed | Zero client-side reclassification]
========================================================================================
```

Final Status:
```
PRODUCTION RUNTIME PARITY VERIFIED
```
