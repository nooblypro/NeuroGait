# NeuroGait — Phase 1 Local ML Foundation

Local Machine Learning foundation for multimodal Freezing of Gait (FoG) detection in Parkinson's Disease, integrating synchronized video pose kinematics and inertial (IMU) sensor streams.

---

## 1. Verified Architecture

```
DATASET (Figshare Parkinson's Turning Task)
  │
  ├── Video (.mp4 @ ~29.98 FPS) ──> MediaPipe Pose ──> 5 Kinematic Features
  │                                                      │
  └── IMU (.txt / .csv @ 128 Hz) ──> 1s Rolling Window ─> 3 Inertial Features
                                                         │
                                               Temporal Sync (±0.1s)
                                                         │
                                              8 Canonical Features (N, 8)
                                                         │
                                        StandardScaler + RandomForest (50 trees)
                                                         │
                                           FoG Class-1 Probabilities [0, 1]
                                                         │
                                           Post-Processing Thresholds:
                                           - p >= 0.60 -> FoG
                                           - 0.40 <= p < 0.60 -> Borderline
                                           - p < 0.40 -> Normal
                                                         │
                                           Episode Aggregation & Gap Merge (<= 1s)
                                                         │
                                           Primary Cue Attribution (Std Dev vs Median)
                                                         │
                                              Canonical JSON Output
```

---

## 2. Environment & Runtime Specifications

### Production Canonical Runtime (Authoritative)
- **Environment**: Linux aarch64 / ARM64 Docker Container (`neurogait-ml:parity-v1` deployed on AWS ECS Fargate)
- **Python**: `3.11.16` (Debian 12 Bookworm, glibc 2.41)
- **MediaPipe**: `1.0.1` (TensorFlow Lite XNNPACK CPU delegate)
- **OpenCV**: `5.0.0.93` (Linux libavcodec / ffmpeg)
- **Core ML Stack**: `scikit-learn==1.9.1`, `pandas==3.0.6`, `numpy==2.4.6`, `scipy==1.17.1`, `joblib==1.6.0`
- **Authoritative Status**: AWS ECS Fargate container execution is the canonical production truth. All production verification tests assert exact parity against this pinned container environment.

### Local Development Runtime (Non-Canonical)
- **Supported**: macOS Darwin (Apple Silicon arm64, tested on Apple M4) and Linux x86_64/aarch64
- **Python**: Python 3.10 – 3.13 (tested on Python 3.13.15)
- **MediaPipe**: `0.10.35` (Apple Metal GPU delegate)
- **Cross-Platform Numerical Divergence**: macOS native inference produces minor floating-point differences in pose landmarks due to GPU shaders and AVFoundation video decoding compared to Linux CPU XNNPACK. Local macOS execution is supported for rapid local development and smoke testing, but is not treated as authoritative production output.

### Local Setup
```bash
# Clone repository and navigate
cd NeuroGait

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```


---

## 3. Dataset Preparation

NeuroGait uses the public **Figshare Parkinson's turning-task dataset** (DOI: [10.6084/m9.figshare.14984667](https://doi.org/10.6084/m9.figshare.14984667)):
- `PDFEinfo.csv`: 35 subjects, clinical assessment scales and millisecond-accurate FoG episode intervals.
- `IMU.zip`: 106 acceleration & angular velocity files sampled at 128.0 Hz with synchronized `Freezing event [flag]`.
- `Videos.zip`: 73 synchronized video trials recorded at ~29.98 FPS (1280x720).

### Download Verified Subjects
```bash
# Downloads PDFEinfo.csv, IMU archive, and sample trial videos (PDFE01_1, PDFE03_1, PDFE09_1)
python3 scripts/download_dataset.py
```

Files will be structured as:
```
data/
└── raw/
    ├── PDFEinfo.csv
    ├── imu/
    │   ├── SUB01_1.txt
    │   ├── SUB03_1.txt
    │   └── SUB09_1.txt
    └── videos/
        ├── PDFE01_1.mp4
        ├── PDFE03_1.mp4
        └── PDFE09_1.mp4
```

---

## 4. The 8 Canonical Features

The model input is strictly validated to shape `(N, 8)` in this immutable order:

1. `left_ankle_velocity`: Rate of displacement of left ankle ($\text{norm\_units} / \text{s}$)
2. `right_ankle_velocity`: Rate of displacement of right ankle ($\text{norm\_units} / \text{s}$)
3. `left_knee_angle`: Interior joint angle at left knee ($0^\circ - 180^\circ$)
4. `right_knee_angle`: Interior joint angle at right knee ($0^\circ - 180^\circ$)
5. `stride_width`: Normalized 2D Euclidean distance between left and right ankles
6. `accel_rms`: Root-mean-square of Anteroposterior linear acceleration: $\sqrt{\frac{1}{M}\sum \text{accel\_y}^2}$
7. `gyro_x_var`: Unbiased sample variance of Mediolateral angular velocity
8. `gyro_z_var`: Unbiased sample variance of Superior-inferior angular velocity

---

## 5. Execution Commands

### Training
Train the Phase 1 RandomForest classifier on all verified dataset pairs:
```bash
python3 scripts/train.py --dataset-dir data --output models/fog_model.pkl
```

### Inference
Run inference on a patient trial:
```bash
python3 scripts/predict.py \
  --video data/raw/videos/PDFE01_1.mp4 \
  --imu data/raw/imu/SUB01_1.txt \
  --model models/fog_model.pkl \
  --output outputs/sample_prediction.json
```

### Run Streamlit UI (Gate 6 Recorded Mode)
Launch the Streamlit web application for Recorded Mode gait analysis:
```bash
# Configure custom backend URL if needed (defaults to deployed AWS API Gateway):
export NEUROGAIT_API_URL="https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com"

# Start Streamlit application
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### Run Tests
Execute the comprehensive test suite (76 verified unit and integration tests across Gates 1–6):
```bash
pytest
```

---

## 6. Canonical Output JSON Contract

Outputs conform to the strict JSON contract:
```json
[
  {
    "start": 0.408,
    "end": 35.708,
    "confidence": 0.9774,
    "type": "FoG",
    "primary_cue": "accel_rms",
    "data_mode": "real"
  },
  {
    "start": 35.008,
    "end": 36.008,
    "confidence": 0.4072,
    "type": "Borderline",
    "primary_cue": "gyro_x_var",
    "data_mode": "real"
  },
  {
    "start": 35.108,
    "end": 36.608,
    "confidence": 0.1294,
    "type": "Normal",
    "primary_cue": "gyro_x_var",
    "data_mode": "real"
  }
]
```

---

## 7. Known Limitations (Phase 1 Baseline)

1. **Occlusion Sensitivity**: In severe camera occlusions or extreme patient turning angles, pose detection may drop out; the pipeline forward-fills temporary dropouts up to the synchronization boundary.
2. **Post-Processing Bands**: "Borderline" is a thresholded decision band ($0.40 \le p < 0.60$) designed to surface ambiguous gait transitions; it is not an independently trained clinical label.
3. **Primary Cue Nature**: The primary cue identifies the feature exhibiting the maximum standardized deviation from the patient's median gait baseline; it represents an algorithmic statistical cue, not a confirmed clinical etiology.
4. **Scope Constraint**: Phase 1 is strictly a local ML foundation. Cloud infrastructure (AWS ECS, API Gateway, DynamoDB), streaming protocols (WebRTC), and graphical interfaces are intentionally omitted in this phase.