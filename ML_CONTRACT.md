Status: DRAFT — derived from Phase 0 implementation.
Date: 2026-09-18

# NeuroGait Machine Learning Contract (Phase 1 Baseline)

## 1. Overview
This contract defines the verified interface, data contracts, feature specifications, classification thresholds, and output representations for the NeuroGait Freezing of Gait (FoG) detection model.

## 2. Modality Specifications

### Video Kinematics
- **Framework**: MediaPipe Pose (`mediapipe.tasks.python.vision.PoseLandmarker`, `pose_landmarker_full.task`).
- **Coordinate Space**: Normalized 2D coordinates $(x, y) \in [0.0, 1.0]$.
- **Frame Rate**: Empirically measured per trial via video container metadata (`cap.get(cv2.CAP_PROP_FPS)`). In the public Figshare turning-task dataset, actual FPS is **29.98 FPS** (NTSC standard 30000/1001). Never assumed to be a fixed constant.
- **Landmarks Monitored**:
  - Left Ankle (Landmark 27)
  - Right Ankle (Landmark 28)
  - Left Knee (Landmark 25)
  - Right Knee (Landmark 26)
  - Left Hip (Landmark 23)
  - Right Hip (Landmark 24)
  - Neck: Midpoint between Left Shoulder (11) and Right Shoulder (12).
- **Raw Landmark Boundary**: Raw landmark coordinates are intermediate data only. Model inputs MUST NOT contain raw landmarks.

### IMU Inertial Sensors
- **Sampling Rate**: Derived dynamically from median timestamp deltas ($1.0 / \text{median}(\Delta t)$). In the Figshare dataset, actual rate is **128.0 Hz** ($\Delta t = 0.0078125\text{ s}$).
- **Sensor Mapping**:
  - `accel_y`: Anteroposterior linear acceleration (`ACC AP [g]`).
  - `gyro_x`: Mediolateral angular velocity (`GYR ML [deg/s]`).
  - `gyro_z`: Superior-inferior angular velocity (`GYR SI [deg/s]`).
- **Windowing**: 1.0-second rolling window labeled strictly by window END timestamp.
- **Missing Data**: No forward-fill for IMU data.

## 3. The 8 Canonical Features (Immutable Ordering)

The model input feature vector $X$ MUST contain exactly these 8 features in this immutable sequence:

| Index | Feature Name | Description | Mathematical Formulation |
|---|---|---|---|
| 1 | `left_ankle_velocity` | Rate of displacement of left ankle | $\frac{\sqrt{(x_t - x_{t-1})^2 + (y_t - y_{t-1})^2}}{\Delta t}$ |
| 2 | `right_ankle_velocity` | Rate of displacement of right ankle | $\frac{\sqrt{(x_t - x_{t-1})^2 + (y_t - y_{t-1})^2}}{\Delta t}$ |
| 3 | `left_knee_angle` | Angle at left knee joint | $\arccos\left(\frac{\vec{v}_{\text{hip}\to\text{knee}} \cdot \vec{v}_{\text{ankle}\to\text{knee}}}{\|\vec{v}_{\text{hip}\to\text{knee}}\| \|\vec{v}_{\text{ankle}\to\text{knee}}\|}\right) \times \frac{180^\circ}{\pi}$ |
| 4 | `right_knee_angle` | Angle at right knee joint | $\arccos\left(\frac{\vec{v}_{\text{hip}\to\text{knee}} \cdot \vec{v}_{\text{ankle}\to\text{knee}}}{\|\vec{v}_{\text{hip}\to\text{knee}}\| \|\vec{v}_{\text{ankle}\to\text{knee}}\|}\right) \times \frac{180^\circ}{\pi}$ |
| 5 | `stride_width` | Distance between ankles | $\sqrt{(x_{\text{left\_ankle}} - x_{\text{right\_ankle}})^2 + (y_{\text{left\_ankle}} - y_{\text{right\_ankle}})^2}$ |
| 6 | `accel_rms` | Root mean square of AP acceleration | $\sqrt{\frac{1}{M}\sum_{i=1}^M \text{accel\_y}_i^2}$ |
| 7 | `gyro_x_var` | Unbiased sample variance of ML gyro | $\frac{1}{M-1}\sum_{i=1}^M (\text{gyro\_x}_i - \overline{\text{gyro\_x}})^2$ |
| 8 | `gyro_z_var` | Unbiased sample variance of SI gyro | $\frac{1}{M-1}\sum_{i=1}^M (\text{gyro\_z}_i - \overline{\text{gyro\_z}})^2$ |

Input shape: $(N, 8)$.

## 4. Temporal Synchronization
- Rolling IMU window end timestamps are aligned to the nearest video pose frame timestamp.
- **Matching Tolerance**: $\pm 0.1\text{ second}$.
- Unmatched rows are dropped.
- **Safety Gate**: If total fused rows $< 10$, execution fails with `SyncError("SYNC ERROR: Only X rows fused (< 10 required)")`.

## 5. Model Architecture & Preprocessing
- **Classifier**: `sklearn.ensemble.RandomForestClassifier(n_estimators=50, max_depth=10, class_weight="balanced", random_state=42)`.
- **Preprocessor**: `sklearn.preprocessing.StandardScaler()`.
- **Target Variable**: Binary classification:
  - `0 = Normal`
  - `1 = FoG`
- **Output**: Class-1 posterior probability $p = P(\text{FoG}=1 \mid X) \in [0.0, 1.0]$.
- **Artifact Serialization**: Persisted as tuple `(model, scaler)` via `joblib.dump(..., "models/fog_model.pkl")`.

## 6. Classification & Post-Processing Bands
- $p \ge 0.60 \implies \mathbf{FoG}$
- $0.40 \le p < 0.60 \implies \mathbf{Borderline}$
- $p < 0.40 \implies \mathbf{Normal}$
- *Rule*: "Borderline" is a post-processing decision band, NOT a separate trained class.

## 7. Episode Aggregation
1. Group contiguous windows of identical classification type.
2. Merge same-type episodes when the gap between the end of the previous episode and start of the next episode $\le 1.0\text{ second}$.
3. Episode confidence: $\text{mean}(p)$ across all constituent windows in that episode.
4. Preserves actual millisecond-resolution timestamps (`start`, `end`).

## 8. Primary Cue Attribution
For each episode:
1. Compute episode feature means: $\bar{\mu}_j = \frac{1}{|E|}\sum_{i \in E} X_{i, j}$.
2. Compute subject overall feature median: $\tilde{m}_j = \text{median}_{i=1\dots N} X_{i, j}$.
3. Compute standardized absolute deviation using the training scaler scale:
   $$z_j = \frac{|\bar{\mu}_j - \tilde{m}_j|}{\sigma_{j,\text{scaler}}}$$
4. Features with zero variance ($\sigma_j \le 10^{-9}$ or NaN) are ignored.
5. Primary cue is the canonical feature name with $\arg\max_j z_j$.
6. *Rule*: This is a model-derived feature cue, NOT a clinical root cause.

## 9. Canonical JSON Schema
Outputs must adhere strictly to the JSON schema:
```json
[
  {
    "start": 5.2,
    "end": 6.8,
    "confidence": 0.92,
    "type": "FoG",
    "primary_cue": "left_ankle_velocity",
    "data_mode": "real"
  }
]
```
- `type`: one of `["FoG", "Borderline", "Normal"]`.
- `data_mode`: `"real"` for actual clinical trial data, `"synthetic_demo"` only if synthetic fallback was forced.

## 10. Production Canonical Runtime Environment & Cross-Platform Invariant

### Authoritative Runtime: Linux ARM64 Container
- **Canonical Definition**: **AWS / Linux ARM64 Container = Production Canonical Inference Environment**.
- **Execution Target**: Deployed AWS ECS Fargate tasks (`neurogait-task:2`) running the immutable container image `955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:parity-v1`.
- **Runtime Dependencies**:
  - Python: `3.11.16` (Debian 12 Bookworm, glibc 2.41)
  - MediaPipe: `1.0.1` (TensorFlow Lite XNNPACK CPU delegate)
  - OpenCV: `5.0.0.93` (Linux libavcodec / ffmpeg YUV420p decoding)
  - scikit-learn: `1.9.1`
  - pandas: `3.0.6`
  - numpy: `2.4.6`
  - scipy: `1.17.1`
  - joblib: `1.6.0`
- **Authoritative Status**: AWS ECS Fargate output is the authoritative truth for deployed clinical inference. All production assertions and reference fixtures are derived strictly from this container environment.

### Local macOS Execution: Development & Debugging Only
- **Non-Canonical**: Local macOS execution (`.venv` on Darwin Apple Silicon) is for development, rapid local debugging, and integration testing only.
- **Cross-Platform Numerical Divergence**:
  - macOS Darwin executes MediaPipe `0.10.35` utilizing Apple's Metal GPU delegate (`GL 2.1 Metal`) and AVFoundation/Darwin video decoding.
  - Linux aarch64 executes MediaPipe `1.0.1` utilizing TensorFlow Lite XNNPACK CPU instructions and Linux ffmpeg decoding.
  - Due to differing video color space conversion matrices and GPU shader vs. CPU SIMD floating-point accumulations, MediaPipe landmark coordinates differ slightly across platforms (e.g. for `PDFE31_1`, this shifts onset of FoG prediction 1 from `55.408s` to `55.508s` and yields 75 vs. 76 total intervals).
- **Invariant Guarantee**:
  $$\text{Local Docker (Linux aarch64)} \equiv \text{AWS ECS Fargate} \equiv \text{Backend Canonical Output} \equiv \text{Frontend Rendered Presentation}$$
  Local macOS native output is NOT required to be numerically identical to AWS production output.

