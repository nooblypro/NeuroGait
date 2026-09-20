# NeuroGait — Multimodal Freezing of Gait (FoG) Detection

> **AI-powered detection of Parkinson's Disease gait episodes** using synchronized video and wearable sensor data, deployed as a full-stack web application on AWS.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Online-brightgreen)](http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)

---

## What Is This?

**Freezing of Gait (FoG)** is a disabling symptom of Parkinson's Disease where a person's feet suddenly feel "glued to the floor" while walking. It leads to falls and significantly reduces quality of life.

**NeuroGait** is a research prototype that automatically detects and timestamps FoG episodes in a video recording. You upload a patient's walking video alongside data from a wrist/waist sensor (IMU), and the system returns a second-by-second breakdown — which moments were normal walking, which were borderline transitions, and which were FoG episodes.

**🌐 Try it live:** [neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com](http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com/)

> ⚠️ **This is a research tool, not a clinical product.** Outputs are ML model predictions, not medical diagnoses.

---

## How It Works — Plain English

```
You upload:
  📹 A video of the patient walking (MP4)
  📡 IMU sensor data file (TXT/CSV from a wrist/waist sensor)

The pipeline does:
  1. Extracts pose keypoints from every video frame   (MediaPipe AI)
  2. Reads raw accelerometer + gyroscope signals       (IMU processing)
  3. Synchronizes both streams to the same timestamps  (±0.1s tolerance)
  4. Computes 8 movement features per 1-second window
  5. Runs a Random Forest classifier on every window
  6. Assigns each second: FoG / Borderline / Normal
  7. Merges adjacent same-class windows into episodes
  8. Returns a JSON timeline + web dashboard

You see:
  📊 A color-coded timeline bar (red=FoG, yellow=Borderline, green=Normal)
  📋 An episode-by-episode table with timestamps and FoG probability
  📈 FoG Burden % (how much of the recording was FoG)
  🧠 A model-grounded narrative explanation
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (S3)                            │
│  Vite + Vanilla JS — Cinematic scroll UI + Assessment dashboard  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ REST API (API Gateway)
┌──────────────────────────────▼──────────────────────────────────┐
│                    CONTROL PLANE (Lambda)                        │
│  POST /sessions         → DynamoDB (session state)              │
│  PUT  /confirm-upload   → S3 (video + IMU files)                │
│  POST /inference/start  → ECS Fargate task dispatch             │
│  GET  /inference/status → DynamoDB polling                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                   ML WORKER (ECS Fargate)                        │
│  Docker container: neurogait-ml:parity-v1 (Linux ARM64)         │
│                                                                  │
│  Video → MediaPipe Pose → 5 kinematic features                  │
│  IMU   → 1s rolling window → 3 inertial features                │
│  Sync  → 8-feature matrix → StandardScaler → RandomForest       │
│  Thresholds → Episode aggregation → JSON output → S3            │
└─────────────────────────────────────────────────────────────────┘
```

### Infrastructure summary

| Component | Technology |
|-----------|-----------|
| Frontend | Vite + Vanilla JS/CSS, hosted on **AWS S3** |
| API | **AWS API Gateway** (REST) |
| Session state | **AWS DynamoDB** |
| File storage | **AWS S3** (presigned upload URLs) |
| ML worker | **AWS ECS Fargate** (Docker, Linux ARM64) |
| ML model | scikit-learn **RandomForest** + MediaPipe |
| Local dev | Python 3.11+, FastAPI |

---

## Repository Structure

```
NeuroGait/
├── src/
│   ├── pipeline.py          # Core ML pipeline (features → classification)
│   ├── api.py               # FastAPI local backend
│   └── contract.py          # JSON output schema validation
│
├── scripts/
│   ├── train.py             # Train the RandomForest model
│   ├── predict.py           # CLI inference on a single trial
│   └── download_dataset.py  # Download the Figshare dataset
│
├── frontend/
│   ├── index.html           # Cinematic 6-beat scroll UI
│   └── src/
│       ├── main.js          # Scroll engine + assessment controller
│       ├── timeline_aggregator.js  # Canonical timeline renderer
│       └── style.css        # Design system
│
├── models/
│   ├── fog_model.pkl        # ✅ Frozen production model (RandomForest)
│   └── pose_landmarker_full.task  # MediaPipe pose model weights
│
├── tests/                   # pytest + node unit/integration tests
├── data/raw/                # Dataset files (downloaded separately)
├── logs/                    # Audit trails and experiment reports
├── Dockerfile               # Production Linux ARM64 ML worker
├── app.py                   # Streamlit local demo UI
├── ML_CONTRACT.md           # Formal ML feature/output specification
└── requirements.txt         # Pinned production dependencies
```

---

## The ML Model — How It Detects FoG

### What the model sees

The Random Forest sees exactly **8 numerical features** per 1-second window:

| # | Feature | Source | What it captures |
|---|---------|--------|-----------------|
| 1 | `left_ankle_velocity` | Video | Left foot movement speed |
| 2 | `right_ankle_velocity` | Video | Right foot movement speed |
| 3 | `left_knee_angle` | Video | Left knee bend (0°–180°) |
| 4 | `right_knee_angle` | Video | Right knee bend (0°–180°) |
| 5 | `stride_width` | Video | Distance between ankles |
| 6 | `accel_rms` | IMU | Body acceleration intensity |
| 7 | `gyro_x_var` | IMU | Side-to-side rotation variability |
| 8 | `gyro_z_var` | IMU | Vertical-axis rotation variability |

### Classification thresholds

```
FoG probability ≥ 0.60          →  🔴 FoG
0.40 ≤ FoG probability < 0.60   →  🟡 Borderline (uncertain)
FoG probability < 0.40           →  🟢 Normal
```

### Model details
- **Algorithm**: `RandomForestClassifier(n_estimators=50, max_depth=10, class_weight="balanced", random_state=42)`
- **Preprocessor**: `StandardScaler` (fitted on training data, frozen with the model)
- **Training data**: Figshare Parkinson's turning-task dataset (35 subjects)
- **Evaluation**: Nested subject-level cross-validation (leakage-free)
- **Model SHA256** (frozen): `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- `ffmpeg` available (used by OpenCV for video decoding)
- Node.js 18+ (only if building the frontend locally)

### 1. Clone and install

```bash
git clone https://github.com/nooblypro/NeuroGait.git
cd NeuroGait

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Download the dataset

The model was trained on the public [Figshare Parkinson's turning-task dataset](https://doi.org/10.6084/m9.figshare.14984667). Download a verified subset:

```bash
python3 scripts/download_dataset.py
```

This creates:
```
data/raw/
├── PDFEinfo.csv          # Subject info + ground truth FoG timestamps
├── imu/
│   ├── SUB01_1.txt       # IMU data for subject 1, trial 1
│   └── ...
└── videos/
    ├── PDFE01_1.mp4      # Video for subject 1, trial 1
    └── ...
```

### 3. Run inference on a single trial

```bash
python3 scripts/predict.py \
  --video data/raw/videos/PDFE01_1.mp4 \
  --imu   data/raw/imu/SUB01_1.txt \
  --model models/fog_model.pkl \
  --output outputs/prediction.json
```

This creates a JSON file with timestamped FoG/Borderline/Normal intervals.

### 4. (Optional) Launch the local web UI

```bash
# FastAPI backend (leave running in a terminal)
uvicorn src.api:app --reload --port 8000

# Then open frontend/index.html in your browser, or:
streamlit run app.py   # Streamlit demo alternative
```

### 5. Run the test suite

```bash
# Python tests (unit + integration)
pytest

# JavaScript tests (timeline/aggregator)
node tests/test_timeline_aggregator.js
```

---

## Output Format

Every inference run returns a JSON array of classified episodes:

```json
[
  {
    "start": 55.508,
    "end": 57.608,
    "confidence": 0.847,
    "type": "FoG",
    "primary_cue": "gyro_z_var",
    "data_mode": "real"
  },
  {
    "start": 57.608,
    "end": 58.008,
    "confidence": 0.512,
    "type": "Borderline",
    "primary_cue": "accel_rms",
    "data_mode": "real"
  }
]
```

| Field | Meaning |
|-------|---------|
| `start` / `end` | Episode timestamps in seconds from recording start |
| `confidence` | Model's FoG class probability (0.0–1.0) |
| `type` | `FoG`, `Borderline`, or `Normal` |
| `primary_cue` | Feature with highest deviation from the patient's baseline |
| `data_mode` | `"real"` for live inference |

---

## Training Your Own Model

If you have additional data and want to retrain:

```bash
python3 scripts/train.py \
  --dataset-dir data \
  --output models/my_model.pkl
```

> ⚠️ Do not overwrite `models/fog_model.pkl` — this is the frozen, verified production model. Use a new filename.

---

## Platform Notes — Why Results Differ Between macOS and Linux

The production canonical environment is **Linux ARM64 (AWS ECS Fargate)**.

If you run inference locally on macOS, you may see minor differences (e.g., a ±0.1s episode boundary shift). This is documented and expected:

- **Linux**: MediaPipe uses TensorFlow Lite XNNPACK CPU delegate → fully deterministic
- **macOS**: MediaPipe uses Apple Metal GPU shader → small floating-point differences in pose landmarks

These differences only appear near classification threshold boundaries (probabilities close to 0.40 or 0.60). The production verification tests assert exact parity against the Linux container.

### Pinned production dependencies

| Package | Version |
|---------|---------|
| `mediapipe` | 1.0.1 |
| `opencv-python-headless` | 5.0.0.93 |
| `scikit-learn` | 1.9.1 |
| `numpy` | 2.4.6 |
| `pandas` | 3.0.6 |
| `scipy` | 1.17.1 |

---

## Dataset

This project uses the **public Figshare Parkinson's turning-task dataset**:

> Mancini, M. et al. (2021). *A public dataset of video, acceleration, angular velocity, and clinical scales in individuals with Parkinson's disease during the turning-in-place task.*
> DOI: [10.6084/m9.figshare.14984667](https://doi.org/10.6084/m9.figshare.14984667)

- **35 subjects** with Parkinson's Disease
- **106 IMU trials** at 128 Hz (3-axis accelerometer + 3-axis gyroscope)
- **73 video trials** at ~29.98 FPS (1280×720)
- **Millisecond-accurate FoG ground truth** annotations per trial

The dataset is publicly available and not redistributed in this repository.

---

## Known Limitations

1. **Research prototype only** — Not validated for clinical use. Do not use for medical decisions.

2. **Occlusion sensitivity** — If the patient is obscured in the video (e.g., furniture, extreme turns), pose detection may fail. The pipeline handles short gaps but not prolonged occlusions.

3. **"Borderline" is not a clinical label** — It means the model's FoG probability fell in the uncertain 0.40–0.60 zone. It is not an independently validated gait state.

4. **Primary cue is statistical, not clinical** — It identifies which of the 8 features had the largest deviation from the patient's rolling baseline. It is a model interpretation aid, not a confirmed neurological cause.

5. **FoG burden is not a severity score** — The percentage shown reflects model-classified time, not clinical FoG severity. It is not a diagnosis or prognostic measure.

6. **Specific IMU format required** — The pipeline expects the Figshare dataset's sensor column names (`ACC AP [g]`, `GYR ML [deg/s]`, `GYR SI [deg/s]`). Other sensor formats require a preprocessing adapter.

---

## Contributing

Contributions, issues, and experiment ideas are welcome.

For any ML changes, please:
- Never overwrite `models/fog_model.pkl` without a clearly versioned replacement
- Run `pytest` and `node tests/test_timeline_aggregator.js` before opening a PR
- Document evaluation methodology and results in `logs/`

---

*Built for Parkinson's Disease gait research. Not a medical device.*
