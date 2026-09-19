# NeuroGait Phase 1 — Gate 2: AWS ML Deployment Evidence

**Execution Date**: 2026-09-18
**Status**: COMPLETE / VERIFIED

---

## 1. AWS Account Identity & Reconnaissance

- **AWS Account ID**: `955519187785`
- **Authenticated Identity**: `arn:aws:iam::955519187785:root`
- **AWS CLI Version**: `aws-cli/2.36.48 Python/3.14.7 Darwin/25.6.0 source/arm64` (installed at `/opt/homebrew/bin/aws`)
- **Configured Region**: `ap-south-1` (Asia Pacific - Mumbai)
- **VPC & Subnet**: Default VPC `vpc-08ead17fe8f2e6b25` (Subnet `subnet-0ed8b6b6255d19fbe` in `ap-south-1a`)

---

## 2. ECR Repository & Container Image Identity

- **ECR Repository Name**: `neurogait-ml`
- **ECR Repository ARN**: `arn:aws:ecr:ap-south-1:955519187785:repository/neurogait-ml`
- **ECR Repository URI**: `955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml`
- **Image Tag**: `gate2`
- **Image Manifest Digest (Linux ARM64)**: `sha256:44a2000a3890ef32c74df3c75f1043b23386554aef44665ff45f3e4dd362e343`
- **Image Index Digest**: `sha256:5d134dc9565f1649a06e76e20f056540181c0dd873a512d8e66ae5d4ee649c63`
- **Image Size**: 755,876,808 bytes (~756 MB compressed)
- **Push Result**: All layers pushed successfully with exit code `0`.

---

## 3. ECS & Fargate Infrastructure

### IAM Roles & Policies
- **Role Name**: `ecsTaskExecutionRole`
- **Role ARN**: `arn:aws:iam::955519187785:role/ecsTaskExecutionRole`
- **Trust Relationship**: `ecs-tasks.amazonaws.com`
- **Attached Policies**: `arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy` (grants ECR pull and CloudWatch logging permissions only)

### CloudWatch Log Group
- **Log Group**: `/ecs/neurogait-ml`
- **Region**: `ap-south-1`

### ECS Cluster
- **Cluster Name**: `neurogait-cluster`
- **Cluster ARN**: `arn:aws:ecs:ap-south-1:955519187785:cluster/neurogait-cluster`
- **Capacity Provider**: FARGATE

### ECS Task Definition
- **Family**: `neurogait-task`
- **Task Definition ARN**: `arn:aws:ecs:ap-south-1:955519187785:task-definition/neurogait-task:1`
- **Launch Type**: FARGATE
- **Network Mode**: `awsvpc`
- **vCPU Allocation**: `1024` (1 vCPU)
- **Memory Allocation**: `2048` (2048 MB)
- **Runtime Platform**: `{"cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX"}` (AWS Graviton)
- **Container Name**: `neurogait-container`
- **Image**: `955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:gate2`

---

## 4. Remote Real Inference Execution

### Execution Request
- **Task ARN**: `arn:aws:ecs:ap-south-1:955519187785:task/neurogait-cluster/f5fa7b632ed748b691fec38e2943416b`
- **Task ID**: `f5fa7b632ed748b691fec38e2943416b`
- **Command Override**:
  ```bash
  python3 scripts/predict.py \
    --video data/raw/videos/PDFE01_1.mp4 \
    --imu data/raw/imu/SUB01_1.txt \
    --model models/fog_model.pkl \
    --output outputs/aws_prediction.json
  ```
- **Task Exit Code**: `0` (Success)
- **Container Execution Timing**:
  - `startedAt`: `2026-09-18T21:23:13.797Z`
  - `stoppedAt`: `2026-09-18T21:26:02.230Z`
  - Total container execution time: ~168.4 s (on 1 vCPU Fargate ARM64 Graviton)

### CloudWatch Inference Output Log
```
==================================================
DATASET SUMMARY
---------------
Video duration: 120.02 s
Video FPS: 29.98
IMU sampling rate: 128.0 Hz
Pose rows (pre-drop): 3598
Fused rows: 1190
FoG labeled windows: 1138
Normal labeled windows: 24
Label source: MODEL PREDICTION (RandomForest)
Subject pairing: INFERENCE on PDFE01_1.mp4 + SUB01_1.txt

FEATURE SUMMARY
---------------
Feature count: 8
Feature names:
1. left_ankle_velocity
2. right_ankle_velocity
3. left_knee_angle
4. right_knee_angle
5. stride_width
6. accel_rms
7. gyro_x_var
8. gyro_z_var

Model input shape: (1190, 8)
Model artifact path: models/fog_model.pkl
==================================================

Canonical JSON output successfully written to: outputs/aws_prediction.json

Inference Output Summary:
[
  {
    "start": 0.008,
    "end": 1.308,
    "confidence": 0.0511,
    "type": "Normal",
    "primary_cue": "accel_rms",
    "data_mode": "real"
  },
  {
    "start": 0.408,
    "end": 1.608,
    "confidence": 0.4889,
    "type": "Borderline",
    "primary_cue": "accel_rms",
    "data_mode": "real"
  },
  {
    "start": 0.708,
    "end": 17.808,
    "confidence": 0.9677,
    "type": "FoG",
    "primary_cue": "stride_width",
    "data_mode": "real"
  },
  {
    "start": 16.908,
    "end": 17.908,
    "confidence": 0.5879,
    "type": "Borderline",
    "primary_cue": "stride_width",
    "data_mode": "real"
  },
  {
    "start": 17.008,
    "end": 35.708,
    "confidence": 0.9567,
    "type": "FoG",
    "primary_cue": "accel_rms",
    "data_mode": "real"
  }
]
... and 43 more episodes.
```

---

## 5. Gate 1 Linux Docker Baseline vs. AWS ECS Fargate Comparison

| Metric | Gate 1 Linux Docker Baseline | Gate 2 AWS ECS Fargate Remote | Match Status |
|---|---|---|---|
| **Input Shape** | `(1190, 8)` | `(1190, 8)` | **100% Exact Match** |
| **Synchronized Windows** | 1,190 | 1,190 | **100% Exact Match** |
| **FoG Windows** | 1,138 | 1,138 | **100% Exact Match** |
| **Normal Windows** | 24 | 24 | **100% Exact Match** |
| **Total Episode Count** | 48 | 48 | **100% Exact Match** |
| **Episode 1** | `0.008–1.308s`, `conf: 0.0511`, `Normal`, `accel_rms` | `0.008–1.308s`, `conf: 0.0511`, `Normal`, `accel_rms` | **100% Exact Match** |
| **Episode 2** | `0.408–1.608s`, `conf: 0.4889`, `Borderline`, `accel_rms` | `0.408–1.608s`, `conf: 0.4889`, `Borderline`, `accel_rms` | **100% Exact Match** |
| **Episode 3** | `0.708–17.808s`, `conf: 0.9677`, `FoG`, `stride_width` | `0.708–17.808s`, `conf: 0.9677`, `FoG`, `stride_width` | **100% Exact Match** |
| **Episode 4** | `16.908–17.908s`, `conf: 0.5879`, `Borderline`, `stride_width` | `16.908–17.908s`, `conf: 0.5879`, `Borderline`, `stride_width` | **100% Exact Match** |
| **Episode 5** | `17.008–35.708s`, `conf: 0.9567`, `FoG`, `accel_rms` | `17.008–35.708s`, `conf: 0.9567`, `FoG`, `accel_rms` | **100% Exact Match** |
| **Canonical JSON Schema** | Valid | Valid | **100% Exact Match** |

*Conclusion*: The AWS Fargate remote inference output matches the Gate 1 Linux Docker baseline **bit-for-bit to 4 decimal places**.

---

## 6. Remote Failure-Path Verification

### Failure Test Configuration
- **Task ID**: `4718f75767ef47f0b7c8dc941218445e`
- **Command**: `python3 scripts/predict.py --video data/raw/videos/NONEXISTENT.mp4 ...`
- **Task Result**: Stopped with `exitCode: 1` (`EssentialContainerExited`).

### CloudWatch Failure Log
```
Traceback (most recent call last):
  File "/app/scripts/predict.py", line 64, in <module>
    main()
  File "/app/scripts/predict.py", line 49, in main
    results = predict_fog(
              ^^^^^^^^^^^^
  File "/app/src/pipeline.py", line 341, in predict_fog
    raise FileNotFoundError(f"Video file not found: {v_path}")
FileNotFoundError: Video file not found: data/raw/videos/NONEXISTENT.mp4
```
*Conclusion*: Invalid input paths fail explicitly with informative error logging and non-zero exit code rather than silently producing corrupt outputs.

---

## 7. Non-Negotiables Compliance Matrix

| Requirement | Status | Verification Note |
|---|---|---|
| Phase 1 ML Behavior Unchanged | PASSED | Zero source code modifications in `src/` |
| 8 Features & Ordering Preserved | PASSED | Model input shape `(1190, 8)` verified in ECS |
| Thresholds Preserved (`0.40 / 0.60`) | PASSED | `0.40 / 0.60` executed in Fargate |
| Model Retraining Avoided | PASSED | `models/fog_model.pkl` deployed unchanged |
| No Temporal Smoothing / Compensations | PASSED | Post-processing untouched |
| No GPU Infrastructure | PASSED | Executed on Fargate CPU (Graviton ARM64) |
| No Lambda Heavy ML | PASSED | Executed on ECS Fargate container |
| No API Gateway | PASSED | 0 API Gateway resources created |
| No DynamoDB | PASSED | 0 DynamoDB tables created |
| No S3 Orchestration | PASSED | 0 S3 pipelines created |
| No Bedrock | PASSED | 0 Bedrock calls or models configured |
| No Streamlit | PASSED | 0 UI components created |
| No Live Mode | PASSED | Recorded batch mode only |
| No EKS / Kubernetes | PASSED | Standard serverless ECS Fargate |
| Least-Privilege IAM | PASSED | Execution role granted only ECR pull + CloudWatch logs |
