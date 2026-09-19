# NeuroGait External Real-World Gait Data Validation Evidence

## 1. Overview
This audit document records the empirical findings of testing the NeuroGait Phase 1 pipeline against real gait datasets obtained from public, openly licensed sources.

- **Objective**: Adversarial pipeline robustness assessment across diverse video resolutions, orientations, viewpoints, and frame rates.
- **Model State**: Unchanged (`models/fog_model.pkl` remains frozen). No retraining was performed.
- **Contract Boundary**: 8 canonical features, classification decision bands, and safety disclaimers remain frozen.

---

## 2. Ingested Sources & Manifest Metadata

| Source ID | Dataset Name | Organization / Provider | Source URL / DOI | License | Classification | File Size | Resolution | Measured FPS | Duration |
|---|---|---|---|---|---|---|---|---|---|
| `toronto_OAW01_bottom` | Toronto Older Adults Gait Archive | Univ. of Toronto / KITE Research | [10.6084/m9.figshare.19929893](https://doi.org/10.6084/m9.figshare.19929893) | CC0 (Public Domain) | `VIDEO_ONLY` | 95.43 MB | 1080x1920 | 29.00 FPS | 75.14s |
| `toronto_OAW01_top` | Toronto Older Adults Gait Archive | Univ. of Toronto / KITE Research | [10.6084/m9.figshare.19929893](https://doi.org/10.6084/m9.figshare.19929893) | CC0 (Public Domain) | `VIDEO_ONLY` | 82.33 MB | 1080x1920 | 26.00 FPS | 78.27s |
| `toronto_OAW02_bottom` | Toronto Older Adults Gait Archive | Univ. of Toronto / KITE Research | [10.6084/m9.figshare.19929893](https://doi.org/10.6084/m9.figshare.19929893) | CC0 (Public Domain) | `VIDEO_ONLY` | 86.22 MB | 1080x1920 | 30.00 FPS | 68.67s |
| `wellcome_typical_gaits` | Typical Gaits & Foot Exercises | Wellcome Library / Archive.org | [archive.org/details/Typicalgaits...](https://archive.org/details/Typicalgaitsandfootexercises-wellcome) | CC BY-NC 3.0 US | `VIDEO_ONLY` | 36.38 MB | 320x240 | 25.00 FPS | 475.40s |

---

## 3. Video-Only Kinematic Processing Results

All videos were processed using `src/pose.PoseFeatureExtractor` without modifying the underlying MediaPipe Pose Landmarker or kinematic calculations:

1. **`wellcome_typical_gaits.mp4` (Low-resolution 320x240 stationary clinical camera)**:
   - **Valid Pose Detection Rate**: **69.0%** (414 / 600 frames).
   - **Kinematic Feature Generation**: 600 / 600 feature rows successfully generated via online forward-fill imputation.
   - **Effective Extraction Speed**: **69.6 FPS** (real-time capable).
   - **Kinematic Ranges**: Knee angle range $[6.2^\circ, 179.9^\circ]$, velocity mean $0.79 \pm 2.05$, stride width mean $0.049 \pm 0.033$.

2. **`toronto_OAW01_bottom.mp4` & `toronto_OAW02_bottom.mp4` (High-definition portrait 1080x1920)**:
   - **Default Orientation Detection Rate**: **0.0%** (`OAW01`) and **5.3%** (`OAW02`).
   - **Root Cause**: The raw video was captured with an inverted ceiling-mounted camera. Rotating the frame $180^\circ$ immediately restored MediaPipe pose detection to **69.7%** (209 / 300 frames).
   - **Finding**: MediaPipe Pose Landmarker requires heads to be oriented upright; inverted camera installations cause detection failure without rotation normalization.

3. **`toronto_OAW01_top.mp4` (Coronal upper-body view)**:
   - **Detection Rate**: **0.0%**.
   - **Root Cause**: Upper-body perspective view severely truncates lower extremities (ankles and feet below frame edge), preventing knee angle and ankle velocity calculation.

---

## 4. Modality Boundary & Model Inference Analysis

1. **Modality Boundary**:
   - The 4 public sources are strictly classified as `VIDEO_ONLY`.
   - In accordance with Section 3, **no synthetic or random IMU data was fabricated**.
   - Because the Phase 1 RandomForest classifier requires the canonical 8-feature representation ($X \in \mathbb{R}^{N \times 8}$ including 3 inertial features: `accel_rms`, `gyro_x_var`, `gyro_z_var`), multimodal inference cannot be executed on video-only sources without violating data integrity contracts.
2. **Ground Truth Labels**:
   - `labels_available: False` across all ingested sources.
   - Accurately recorded as `GROUND_TRUTH_UNAVAILABLE`. No accuracy claims are made.

---

## 5. Independent Verification Evidence

Executable verification via `scripts/verify_external_validation.py`:
- All 4 downloaded files verified with SHA256 checksums matching `manifest.json`.
- Video metadata and dimensions independently measured.
- Model artifact `models/fog_model.pkl` verified unchanged.
- Verdict: **PASS**.
