# NeuroGait — Ground-Truth Validation & Error Analysis Report

**Date**: 2026-09-20 19:53:25  
**Model Artifact**: `/Users/shriram/Documents/Projects/NeuroGait/models/fog_model.pkl`  
**Model SHA256**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`  
**Annotation Source**: `PDFEinfo.xls` / `data/raw/PDFEinfo.csv`  
**Decision Threshold**: FoG $\ge 0.60$, Borderline $\ge 0.40$, Normal $< 0.40$  

---

## 1. Executive Summary

This evaluation pass benchmarks the **current frozen Phase 1 NeuroGait ML model** against authoritative clinical ground-truth annotations from `PDFEinfo.xls` without retraining, tuning thresholds, or modifying feature representations.

| Metric | Value | Meaning |
|---|---|---|
| **Recordings Evaluated** | `71` | Complete cohort analyzed |
| **Ground-Truth FoG Episodes** | `173` | Clinical episodes documented |
| **Model-Predicted FoG Episodes** | `1163` | Total predicted FoG episodes |
| **True Positives (TP)** | `142` | Ground-truth episodes successfully detected |
| **False Positives (FP)** | `910` | Model predictions with zero clinical overlap |
| **False Negatives (FN)** | `31` | Clinical FoG episodes completely missed |
| **Episode Precision** | `13.5%` | Fraction of predicted episodes that were genuine FoG |
| **Episode Recall (Sensitivity)** | `82.1%` | Fraction of genuine FoG episodes detected |
| **Episode F1-Score** | `0.2318` | Harmonic mean of precision and recall |
| **Mean Temporal IoU** | `0.2410` | Bounding overlap quality for matched episodes |
| **Median Temporal IoU** | `0.1702` | Median bounding overlap quality |

### 1-Second Discretized Window-Level Metrics

| Window Metric | Value | Meaning |
|---|---|---|
| **Total 1.0s Windows** | `8520` | Discretized 1-second windows across evaluated trials |
| **Window True Positives (TP)** | `855` | 1s windows correctly predicted as FoG |
| **Window True Negatives (TN)** | `4897` | 1s windows correctly predicted as Non-FoG |
| **Window False Positives (FP)** | `1993` | Non-FoG 1s windows falsely flagged as FoG |
| **Window False Negatives (FN)** | `775` | Genuine FoG 1s windows missed by model |
| **Window Sensitivity (Recall)** | `52.4%` | Fraction of genuine FoG duration detected |
| **Window Specificity** | `71.1%` | Fraction of non-freezing gait correctly recognized |
| **Window Precision (PPV)** | `30.0%` | Fraction of predicted FoG seconds that were true freezing |
| **Window Accuracy** | `67.5%` | Overall correct 1s window classifications |
| **Window F1-Score** | `0.3819` | Harmonic mean of window precision & sensitivity |
| **FoG Window Prevalence** | `19.13%` | Proportion of trial duration with clinical freezing |

---

## 2. Dataset & Annotation Source

- **Dataset Name**: Turning-Task Multimodal Freezing of Gait Dataset (Figshare).
- **Spreadsheet File**: `PDFEinfo.xls` (and identical textual export `data/raw/PDFEinfo.csv`).
- **Structure**: 35 subjects (`PDFE01` – `PDFE35`) across up to 3 turning sessions per subject.
- **Header Mapping**:
  - Subject ID: Column 0 (`ID`)
  - Session Count: Column 9 (`sessions #`)
  - Session 1: FoG Intervals = Col 24 (`Session 1 - time of FoG (s)`), Duration = Col 25, Episode Count = Col 26
  - Session 2: FoG Intervals = Col 42 (`Session 2 - time of FoG (s)`), Duration = Col 43, Episode Count = Col 44
  - Session 3: FoG Intervals = Col 60 (`Session 3 - time of FoG (s)`), Duration = Col 61, Episode Count = Col 62

---

## 3. Dedicated Verification: PDFE31 / Session 1

### Independently Verified Ground Truth:
- **Spreadsheet Row**: Row 40 in `PDFEinfo.xls`
- **Interval String**: `[55.797-58.507]`
- **Total FoG Duration**: `2.72` seconds
- **Episode Count**: `1`

### Current Model Predictions on `PDFE31_1`:
The current model predicted **27 FoG episodes** during the 120-second trial:

| Predicted Interval | Overlap Duration | IoU | Classification | Confidence | Primary Cue |
|---|---|---|---|---|---|
| `4.708s – 6.008s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `87.4%` | `gyro_z_var` |
| `8.708s – 9.908s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `73.4%` | `stride_width` |
| `10.008s – 11.408s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `90.5%` | `gyro_z_var` |
| `15.608s – 18.208s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `88.8%` | `gyro_z_var` |
| `18.508s – 19.608s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `73.7%` | `accel_rms` |
| `20.808s – 21.908s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `71.9%` | `stride_width` |
| `22.708s – 24.208s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `91.2%` | `gyro_z_var` |
| `28.808s – 31.208s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `83.5%` | `gyro_z_var` |
| `31.408s – 34.108s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `84.9%` | `gyro_z_var` |
| `36.308s – 37.808s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `88.1%` | `gyro_z_var` |
| `42.108s – 47.808s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `90.8%` | `gyro_z_var` |
| `48.808s – 50.008s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `70.8%` | `stride_width` |
| `50.608s – 52.408s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `79.7%` | `gyro_z_var` |
| `55.408s – 57.608s` | `1.811s` | `0.584` | `TRUE_POSITIVE` | `87.1%` | `gyro_z_var` |
| `58.008s – 61.208s` | `0.499s` | `0.092` | `FRAGMENTED_OVERLAP` | `87.1%` | `gyro_z_var` |
| `62.008s – 64.108s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `83.0%` | `gyro_z_var` |
| `65.908s – 67.708s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `92.8%` | `gyro_z_var` |
| `73.408s – 75.408s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `86.0%` | `gyro_z_var` |
| `76.208s – 79.808s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `81.6%` | `gyro_z_var` |
| `80.008s – 81.708s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `85.6%` | `gyro_z_var` |
| `86.408s – 90.408s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `82.9%` | `gyro_z_var` |
| `90.608s – 95.208s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `82.5%` | `gyro_z_var` |
| `95.408s – 97.508s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `91.4%` | `gyro_z_var` |
| `99.808s – 101.108s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `74.8%` | `accel_rms` |
| `102.808s – 105.708s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `87.6%` | `gyro_z_var` |
| `106.108s – 112.808s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `78.3%` | `gyro_z_var` |
| `117.108s – 119.908s` | `0.000s` | `0.000` | `FALSE_POSITIVE` | `87.7%` | `gyro_z_var` |

### PDFE31_1 Diagnostic Findings:
1. **Detection Verified**: The model successfully captured the clinical FoG episode (`55.797s – 58.507s`). Two contiguous model intervals overlapped it:
   - `55.408s – 57.608s` (1.811s overlap, IoU 0.584, confidence 87.1%, cue `gyro_z_var`)
   - `58.008s – 61.208s` (0.499s overlap, IoU 0.092, confidence 87.1%, cue `gyro_z_var`)
   - **Combined temporal coverage of GT episode**: **`2.310s / 2.710s = 85.24%`**.
2. **Severe False Positive Clustering**: In addition to capturing the true episode, the model fired **25 false positive FoG episodes** across normal gait segments, primarily attributed to `gyro_z_var` during turning dynamics.

---

## 4. Per-Recording Evaluation Results

| Recording | GT Ep | Pred Ep | Ep TP | Ep FP | Ep FN | Ep Recall | Ep Prec | Mean IoU | Win Sens | Win Spec | Win Prec | Win Acc | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `PDFE01_1` | `4` | `2` | `2` | `0` | `2` | `50.0%` | `100.0%` | `0.615` | `100.0%` | `0.0%` | `96.7%` | `96.7%` | `EVALUATED` |
| `PDFE01_2` | `2` | `12` | `2` | `0` | `0` | `100.0%` | `100.0%` | `0.151` | `90.5%` | `0.0%` | `96.3%` | `87.5%` | `EVALUATED` |
| `PDFE02_1` | `4` | `20` | `4` | `1` | `0` | `100.0%` | `80.0%` | `0.090` | `44.4%` | `66.7%` | `92.3%` | `46.7%` | `EVALUATED` |
| `PDFE03_1` | `1` | `7` | `1` | `6` | `0` | `100.0%` | `14.3%` | `0.539` | `100.0%` | `93.3%` | `11.1%` | `93.3%` | `EVALUATED` |
| `PDFE03_2` | `0` | `17` | `0` | `17` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `80.0%` | `0.0%` | `80.0%` | `EVALUATED` |
| `PDFE03_3` | `1` | `7` | `1` | `6` | `0` | `100.0%` | `14.3%` | `0.254` | `50.0%` | `94.1%` | `12.5%` | `93.3%` | `EVALUATED` |
| `PDFE04_1` | `8` | `10` | `4` | `5` | `4` | `50.0%` | `44.4%` | `0.298` | `25.0%` | `83.7%` | `19.1%` | `75.8%` | `EVALUATED` |
| `PDFE05_1` | `5` | `9` | `5` | `4` | `0` | `100.0%` | `55.6%` | `0.228` | `27.3%` | `89.0%` | `20.0%` | `83.3%` | `EVALUATED` |
| `PDFE05_2` | `5` | `10` | `2` | `8` | `3` | `40.0%` | `20.0%` | `0.416` | `5.6%` | `84.5%` | `13.3%` | `60.8%` | `EVALUATED` |
| `PDFE06_1` | `1` | `3` | `1` | `1` | `0` | `100.0%` | `50.0%` | `0.387` | `100.0%` | `97.5%` | `40.0%` | `97.5%` | `EVALUATED` |
| `PDFE06_2` | `0` | `1` | `0` | `1` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `99.2%` | `0.0%` | `99.2%` | `EVALUATED` |
| `PDFE07_1` | `1` | `4` | `1` | `0` | `0` | `100.0%` | `100.0%` | `0.010` | `4.2%` | `0.0%` | `100.0%` | `4.2%` | `EVALUATED` |
| `PDFE07_2` | `2` | `3` | `2` | `1` | `0` | `100.0%` | `66.7%` | `0.024` | `2.6%` | `80.0%` | `75.0%` | `5.8%` | `EVALUATED` |
| `PDFE07_3` | `1` | `2` | `1` | `0` | `0` | `100.0%` | `100.0%` | `0.009` | `1.7%` | `0.0%` | `100.0%` | `1.7%` | `EVALUATED` |
| `PDFE08_1` | `7` | `24` | `7` | `4` | `0` | `100.0%` | `63.6%` | `0.255` | `80.5%` | `21.1%` | `68.8%` | `61.7%` | `EVALUATED` |
| `PDFE09_1` | `0` | `3` | `0` | `3` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `97.5%` | `0.0%` | `97.5%` | `EVALUATED` |
| `PDFE09_2` | `4` | `23` | `2` | `19` | `2` | `50.0%` | `9.5%` | `0.189` | `33.3%` | `71.7%` | `20.0%` | `65.0%` | `EVALUATED` |
| `PDFE10_1` | `0` | `0` | `0` | `0` | `0` | `100.0%` | `100.0%` | `0.000` | `0.0%` | `100.0%` | `0.0%` | `100.0%` | `EVALUATED` |
| `PDFE10_2` | `0` | `2` | `0` | `2` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `98.3%` | `0.0%` | `98.3%` | `EVALUATED` |
| `PDFE11_1` | `0` | `17` | `0` | `17` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `83.3%` | `0.0%` | `83.3%` | `EVALUATED` |
| `PDFE11_2` | `4` | `16` | `4` | `11` | `0` | `100.0%` | `26.7%` | `0.365` | `75.9%` | `79.1%` | `53.7%` | `78.3%` | `EVALUATED` |
| `PDFE12_1` | `0` | `7` | `0` | `7` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `93.3%` | `0.0%` | `93.3%` | `EVALUATED` |
| `PDFE13_1` | `0` | `25` | `0` | `25` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `5.8%` | `0.0%` | `5.8%` | `EVALUATED` |
| `PDFE14_1` | `15` | `21` | `10` | `10` | `5` | `66.7%` | `50.0%` | `0.304` | `48.5%` | `55.2%` | `29.1%` | `53.3%` | `EVALUATED` |
| `PDFE14_2` | `10` | `23` | `8` | `14` | `2` | `80.0%` | `36.4%` | `0.196` | `35.0%` | `59.0%` | `14.6%` | `55.0%` | `EVALUATED` |
| `PDFE14_3` | `10` | `22` | `9` | `11` | `1` | `90.0%` | `45.0%` | `0.175` | `26.7%` | `57.8%` | `17.4%` | `50.0%` | `EVALUATED` |
| `PDFE15_1` | `1` | `38` | `1` | `37` | `0` | `100.0%` | `2.6%` | `0.821` | `100.0%` | `57.8%` | `7.5%` | `59.2%` | `EVALUATED` |
| `PDFE16_1` | `9` | `27` | `9` | `16` | `0` | `100.0%` | `36.0%` | `0.345` | `56.2%` | `48.9%` | `28.6%` | `50.8%` | `EVALUATED` |
| `PDFE16_2` | `3` | `28` | `2` | `25` | `1` | `66.7%` | `7.4%` | `0.247` | `28.6%` | `50.4%` | `3.5%` | `49.2%` | `EVALUATED` |
| `PDFE17_1` | `0` | `20` | `0` | `20` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `81.7%` | `0.0%` | `81.7%` | `EVALUATED` |
| `PDFE18_1` | `3` | `24` | `3` | `21` | `0` | `100.0%` | `12.5%` | `0.345` | `60.0%` | `63.5%` | `6.7%` | `63.3%` | `EVALUATED` |
| `PDFE18_2` | `0` | `18` | `0` | `18` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `83.3%` | `0.0%` | `83.3%` | `EVALUATED` |
| `PDFE18_3` | `1` | `20` | `1` | `19` | `0` | `100.0%` | `5.0%` | `0.162` | `50.0%` | `78.0%` | `3.7%` | `77.5%` | `EVALUATED` |
| `PDFE19_1` | `1` | `24` | `1` | `0` | `0` | `100.0%` | `100.0%` | `0.018` | `42.5%` | `0.0%` | `100.0%` | `42.5%` | `EVALUATED` |
| `PDFE19_2` | `2` | `5` | `2` | `0` | `0` | `100.0%` | `100.0%` | `0.397` | `99.2%` | `0.0%` | `97.5%` | `96.7%` | `EVALUATED` |
| `PDFE20_1` | `0` | `26` | `0` | `26` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `70.0%` | `0.0%` | `70.0%` | `EVALUATED` |
| `PDFE20_2` | `1` | `21` | `1` | `20` | `0` | `100.0%` | `4.8%` | `0.349` | `50.0%` | `76.3%` | `3.5%` | `75.8%` | `EVALUATED` |
| `PDFE20_3` | `3` | `26` | `3` | `23` | `0` | `100.0%` | `11.5%` | `0.487` | `66.7%` | `70.2%` | `10.5%` | `70.0%` | `EVALUATED` |
| `PDFE21_1` | `0` | `40` | `0` | `40` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `38.3%` | `0.0%` | `38.3%` | `EVALUATED` |
| `PDFE21_2` | `0` | `24` | `0` | `24` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `52.5%` | `0.0%` | `52.5%` | `EVALUATED` |
| `PDFE21_3` | `2` | `17` | `1` | `16` | `1` | `50.0%` | `5.9%` | `0.235` | `100.0%` | `20.4%` | `12.2%` | `28.3%` | `EVALUATED` |
| `PDFE22_1` | `0` | `17` | `0` | `17` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `79.2%` | `0.0%` | `79.2%` | `EVALUATED` |
| `PDFE23_1` | `2` | `25` | `2` | `22` | `0` | `100.0%` | `8.3%` | `0.331` | `90.9%` | `38.5%` | `13.0%` | `43.3%` | `EVALUATED` |
| `PDFE23_2` | `0` | `28` | `0` | `28` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `23.3%` | `0.0%` | `23.3%` | `EVALUATED` |
| `PDFE24_1` | `8` | `23` | `7` | `13` | `1` | `87.5%` | `35.0%` | `0.324` | `61.5%` | `43.6%` | `23.2%` | `47.5%` | `EVALUATED` |
| `PDFE25_1` | `0` | `9` | `0` | `9` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `92.5%` | `0.0%` | `92.5%` | `EVALUATED` |
| `PDFE25_2` | `0` | `1` | `0` | `1` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `99.2%` | `0.0%` | `99.2%` | `EVALUATED` |
| `PDFE25_3` | `0` | `7` | `0` | `7` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `91.7%` | `0.0%` | `91.7%` | `EVALUATED` |
| `PDFE26_1` | `0` | `8` | `0` | `8` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `91.7%` | `0.0%` | `91.7%` | `EVALUATED` |
| `PDFE26_2` | `0` | `1` | `0` | `1` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `99.2%` | `0.0%` | `99.2%` | `EVALUATED` |
| `PDFE26_3` | `0` | `4` | `0` | `4` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `95.8%` | `0.0%` | `95.8%` | `EVALUATED` |
| `PDFE27_1` | `6` | `11` | `4` | `1` | `2` | `66.7%` | `80.0%` | `0.287` | `85.0%` | `33.3%` | `81.4%` | `73.3%` | `EVALUATED` |
| `PDFE27_2` | `6` | `20` | `6` | `13` | `0` | `100.0%` | `31.6%` | `0.503` | `72.4%` | `60.4%` | `36.8%` | `63.3%` | `EVALUATED` |
| `PDFE27_3` | `1` | `19` | `1` | `17` | `0` | `100.0%` | `5.6%` | `0.220` | `75.0%` | `54.3%` | `5.4%` | `55.0%` | `EVALUATED` |
| `PDFE28_1` | `0` | `35` | `0` | `35` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `49.2%` | `0.0%` | `49.2%` | `EVALUATED` |
| `PDFE28_2` | `0` | `21` | `0` | `21` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `63.3%` | `0.0%` | `63.3%` | `EVALUATED` |
| `PDFE28_3` | `0` | `22` | `0` | `22` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `62.5%` | `0.0%` | `62.5%` | `EVALUATED` |
| `PDFE29_1` | `11` | `24` | `11` | `11` | `0` | `100.0%` | `50.0%` | `0.433` | `66.0%` | `64.4%` | `54.4%` | `65.0%` | `EVALUATED` |
| `PDFE30_1` | `9` | `26` | `9` | `12` | `0` | `100.0%` | `42.9%` | `0.268` | `41.7%` | `70.8%` | `48.8%` | `59.2%` | `EVALUATED` |
| `PDFE30_2` | `1` | `20` | `1` | `19` | `0` | `100.0%` | `5.0%` | `0.239` | `50.0%` | `74.6%` | `3.2%` | `74.2%` | `EVALUATED` |
| `PDFE31_1` | `1` | `27` | `1` | `25` | `0` | `100.0%` | `3.9%` | `0.338` | `100.0%` | `46.2%` | `4.5%` | `47.5%` | `EVALUATED` |
| `PDFE31_2` | `3` | `27` | `2` | `23` | `1` | `66.7%` | `8.0%` | `0.272` | `62.5%` | `50.0%` | `8.2%` | `50.8%` | `EVALUATED` |
| `PDFE31_3` | `3` | `5` | `1` | `4` | `2` | `33.3%` | `20.0%` | `0.025` | `0.0%` | `95.7%` | `0.0%` | `91.7%` | `EVALUATED` |
| `PDFE32_1` | `2` | `10` | `1` | `9` | `1` | `50.0%` | `10.0%` | `0.152` | `0.0%` | `89.0%` | `0.0%` | `87.5%` | `EVALUATED` |
| `PDFE32_2` | `0` | `11` | `0` | `11` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `90.0%` | `0.0%` | `90.0%` | `EVALUATED` |
| `PDFE32_3` | `0` | `16` | `0` | `16` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `85.8%` | `0.0%` | `85.8%` | `EVALUATED` |
| `PDFE33_1` | `6` | `20` | `3` | `11` | `3` | `50.0%` | `21.4%` | `0.101` | `36.6%` | `75.9%` | `44.1%` | `62.5%` | `EVALUATED` |
| `PDFE34_1` | `3` | `16` | `3` | `10` | `0` | `100.0%` | `23.1%` | `0.300` | `80.8%` | `14.9%` | `20.8%` | `29.2%` | `EVALUATED` |
| `PDFE35_1` | `0` | `20` | `0` | `20` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `65.0%` | `0.0%` | `65.0%` | `EVALUATED` |
| `PDFE35_2` | `0` | `21` | `0` | `21` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `67.5%` | `0.0%` | `67.5%` | `EVALUATED` |
| `PDFE35_3` | `0` | `21` | `0` | `21` | `0` | `100.0%` | `0.0%` | `0.000` | `0.0%` | `80.8%` | `0.0%` | `80.8%` | `EVALUATED` |

---

## 5. Per-Subject Evaluation Results

| Subject | Sessions | GT FoG Episodes | Predicted FoG Episodes | TP | FP | FN | Precision | Recall | F1 | Mean IoU |
|---|---|---|---|---|---|---|---|---|---|---|
| `PDFE01` | `2` | `6` | `14` | `4` | `0` | `2` | `100.0%` | `66.7%` | `0.800` | `0.383` |
| `PDFE02` | `1` | `4` | `20` | `4` | `1` | `0` | `80.0%` | `100.0%` | `0.889` | `0.090` |
| `PDFE03` | `3` | `2` | `31` | `2` | `29` | `0` | `6.5%` | `100.0%` | `0.121` | `0.396` |
| `PDFE04` | `1` | `8` | `10` | `4` | `5` | `4` | `44.4%` | `50.0%` | `0.471` | `0.298` |
| `PDFE05` | `2` | `10` | `19` | `7` | `12` | `3` | `36.8%` | `70.0%` | `0.483` | `0.322` |
| `PDFE06` | `2` | `1` | `4` | `1` | `2` | `0` | `33.3%` | `100.0%` | `0.500` | `0.387` |
| `PDFE07` | `3` | `4` | `9` | `4` | `1` | `0` | `80.0%` | `100.0%` | `0.889` | `0.014` |
| `PDFE08` | `1` | `7` | `24` | `7` | `4` | `0` | `63.6%` | `100.0%` | `0.778` | `0.255` |
| `PDFE09` | `2` | `4` | `26` | `2` | `22` | `2` | `8.3%` | `50.0%` | `0.143` | `0.189` |
| `PDFE10` | `2` | `0` | `2` | `0` | `2` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |
| `PDFE11` | `2` | `4` | `33` | `4` | `28` | `0` | `12.5%` | `100.0%` | `0.222` | `0.365` |
| `PDFE12` | `1` | `0` | `7` | `0` | `7` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |
| `PDFE13` | `1` | `0` | `25` | `0` | `25` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |
| `PDFE14` | `3` | `35` | `66` | `27` | `35` | `8` | `43.5%` | `77.1%` | `0.557` | `0.225` |
| `PDFE15` | `1` | `1` | `38` | `1` | `37` | `0` | `2.6%` | `100.0%` | `0.051` | `0.821` |
| `PDFE16` | `2` | `12` | `55` | `11` | `41` | `1` | `21.1%` | `91.7%` | `0.344` | `0.296` |
| `PDFE17` | `1` | `0` | `20` | `0` | `20` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |
| `PDFE18` | `3` | `4` | `62` | `4` | `58` | `0` | `6.5%` | `100.0%` | `0.121` | `0.253` |
| `PDFE19` | `2` | `3` | `29` | `3` | `0` | `0` | `100.0%` | `100.0%` | `1.000` | `0.207` |
| `PDFE20` | `3` | `4` | `73` | `4` | `69` | `0` | `5.5%` | `100.0%` | `0.104` | `0.418` |
| `PDFE21` | `3` | `2` | `81` | `1` | `80` | `1` | `1.2%` | `50.0%` | `0.024` | `0.235` |
| `PDFE22` | `1` | `0` | `17` | `0` | `17` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |
| `PDFE23` | `2` | `2` | `53` | `2` | `50` | `0` | `3.9%` | `100.0%` | `0.074` | `0.331` |
| `PDFE24` | `1` | `8` | `23` | `7` | `13` | `1` | `35.0%` | `87.5%` | `0.500` | `0.324` |
| `PDFE25` | `3` | `0` | `17` | `0` | `17` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |
| `PDFE26` | `3` | `0` | `13` | `0` | `13` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |
| `PDFE27` | `3` | `13` | `50` | `11` | `31` | `2` | `26.2%` | `84.6%` | `0.400` | `0.337` |
| `PDFE28` | `3` | `0` | `78` | `0` | `78` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |
| `PDFE29` | `1` | `11` | `24` | `11` | `11` | `0` | `50.0%` | `100.0%` | `0.667` | `0.433` |
| `PDFE30` | `2` | `10` | `46` | `10` | `31` | `0` | `24.4%` | `100.0%` | `0.392` | `0.254` |
| `PDFE31` | `3` | `7` | `59` | `4` | `52` | `3` | `7.1%` | `57.1%` | `0.127` | `0.211` |
| `PDFE32` | `3` | `2` | `37` | `1` | `36` | `1` | `2.7%` | `50.0%` | `0.051` | `0.152` |
| `PDFE33` | `1` | `6` | `20` | `3` | `11` | `3` | `21.4%` | `50.0%` | `0.300` | `0.101` |
| `PDFE34` | `1` | `3` | `16` | `3` | `10` | `0` | `23.1%` | `100.0%` | `0.375` | `0.300` |
| `PDFE35` | `3` | `0` | `62` | `0` | `62` | `0` | `0.0%` | `0.0%` | `0.000` | `0.000` |

---

## 6. Complete Recording Discovery Inventory

All 79 potential slots across the 35 cohort subjects:

| Slot | Subject | Session | Video File | IMU File | Raw Annotation | Status | Reason |
|---|---|---|---|---|---|---|---|
| `PDFE01_1` | `PDFE01` | `1` | `Found` | `Found` | `[1.383-35.768; 36.696-65.969; 67.328-105.162; 106.418-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE01_2` | `PDFE01` | `2` | `Found` | `Found` | `[0-46.502; 50.549-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE01_3` | `PDFE01` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE02_1` | `PDFE02` | `1` | `Found` | `Found` | `[0.024-44.578; 53.817-98.191; 99.232-110.814; 112.948-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE02_2` | `PDFE02` | `2` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE02_3` | `PDFE02` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE03_1` | `PDFE03` | `1` | `Found` | `Found` | `[35.035-36.286]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE03_2` | `PDFE03` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE03_3` | `PDFE03` | `3` | `Found` | `Found` | `[58.216-59.646]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE04_1` | `PDFE04` | `1` | `Found` | `Found` | `[34.613-35.744; 48.299-49.882; 58.567-59.890; 62.438-66.397; 86.758-89.292; 92.866-95.469; 103.725-104.662; 110.244-113.133]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE04_2` | `PDFE04` | `2` | `Missing` | `Missing` | `-` | `MISSING ANNOTATION` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE04_3` | `PDFE04` | `3` | `Missing` | `Missing` | `-` | `MISSING ANNOTATION` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE05_1` | `PDFE05` | `1` | `Found` | `Found` | `[55.637-58.816; 84.866-85.431; 88.892-90.623; 104.125-107.966; 111.721-114.235]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE05_2` | `PDFE05` | `2` | `Found` | `Found` | `[37.609-9.659; 53.753-54.65; 56.187-58.492; 89.629-92.339; 111.859-115.383]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE05_3` | `PDFE05` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE06_1` | `PDFE06` | `1` | `Found` | `Found` | `[112.224-114.486]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE06_2` | `PDFE06` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE06_3` | `PDFE06` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE07_1` | `PDFE07` | `1` | `Found` | `Found` | `[0-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE07_2` | `PDFE07` | `2` | `Found` | `Found` | `[0.332-61.209; 65.504-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE07_3` | `PDFE07` | `3` | `Found` | `Found` | `[0-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE08_1` | `PDFE08` | `1` | `Found` | `Found` | `[3.666-25.872; 30.15-32.346; 34.816-41.713; 50.922-61.909; 70.335-78.372; 83.367-101.186; 106.372-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE08_2` | `PDFE08` | `2` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE08_3` | `PDFE08` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE09_1` | `PDFE09` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE09_2` | `PDFE09` | `2` | `Found` | `Found` | `[24.635-26.982; 53.528-65.385; 89.455-93.765; 99.459-101.764]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE09_3` | `PDFE09` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE10_1` | `PDFE10` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE10_2` | `PDFE10` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE10_3` | `PDFE10` | `3` | `Found` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE11_1` | `PDFE11` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE11_2` | `PDFE11` | `2` | `Found` | `Found` | `[17.655-19.47; 73.271-75.085; 81.596-95.242; 98.749-112.019]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE11_3` | `PDFE11` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE12_1` | `PDFE12` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE12_2` | `PDFE12` | `2` | `Missing` | `Missing` | `-` | `MISSING ANNOTATION` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE12_3` | `PDFE12` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE13_1` | `PDFE13` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE13_2` | `PDFE13` | `2` | `Missing` | `Missing` | `-` | `MISSING ANNOTATION` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE13_3` | `PDFE13` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE14_1` | `PDFE14` | `1` | `Found` | `Found` | `[9.847-11.288; 19.454-20.436; 30.382-31.684; 35.546-37.531; 44.613-48.048; 49.116-50.717; 57.642-60.928; 68.209-70.491; 81.059-83.406; 85.502-87.664; 90.065-92.434; 95.950-97.270; 102.915-106.201; 110.960-112.518; 115.284-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE14_2` | `PDFE14` | `2` | `Found` | `Found` | `[11.938-13.265; 44.497-46.185; 54.144-56.449; 65.962-68.856; 80.070-82.247; 86.549-88.235; 93.456-94.630; 105.394-106.653; 109.675-111.362; 113.594-117.515]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE14_3` | `PDFE14` | `3` | `Found` | `Found` | `[9.623-10.826; 29.230-32.580; 41.980-44.199; 53.047-55.522; 64.354-66.759; 70.696-72.413; 77.826-82.547; 91.899-93.884; 99.598-101.583; 104.529-111.987]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE15_1` | `PDFE15` | `1` | `Found` | `Found` | `[95.797-99.766]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE15_2` | `PDFE15` | `2` | `Missing` | `Missing` | `-` | `MISSING ANNOTATION` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE15_3` | `PDFE15` | `3` | `Missing` | `Missing` | `-` | `MISSING ANNOTATION` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE16_1` | `PDFE16` | `1` | `Found` | `Found` | `[4.456-13.126; 17.702-20.540; 29.985-31.927; 56.357-59.451; 64.305-66.695; 71.650-74.019; 79.117-83.491; 103.682-106.072; 111.028-114.933]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE16_2` | `PDFE16` | `2` | `Found` | `Found` | `[25.260-26.477; 38.011-40.934; 92.982-95.863]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE16_3` | `PDFE16` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE17_1` | `PDFE17` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE17_2` | `PDFE17` | `2` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE17_3` | `PDFE17` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE18_1` | `PDFE18` | `1` | `Found` | `Found` | `[43.291-45.382; 52.335-54.405; 61.741-63.406]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE18_2` | `PDFE18` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE18_3` | `PDFE18` | `3` | `Found` | `Found` | `[79.466-80.640]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE19_1` | `PDFE19` | `1` | `Found` | `Found` | `[0-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE19_2` | `PDFE19` | `2` | `Found` | `Found` | `[0-32.558; 36.255-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE19_3` | `PDFE19` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE20_1` | `PDFE20` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE20_2` | `PDFE20` | `2` | `Found` | `Found` | `[16.762-19.088]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE20_3` | `PDFE20` | `3` | `Found` | `Found` | `[44.859-46.574; 85.738-87.600; 110.820-112.826]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE21_1` | `PDFE21` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE21_2` | `PDFE21` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE21_3` | `PDFE21` | `3` | `Found` | `Found` | `[45.982-52.856; 60.661-66.123]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE22_1` | `PDFE22` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE22_2` | `PDFE22` | `2` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE22_3` | `PDFE22` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE23_1` | `PDFE23` | `1` | `Found` | `Found` | `[70.093-73.983; 83.648-91.023]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE23_2` | `PDFE23` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE23_3` | `PDFE23` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE24_1` | `PDFE24` | `1` | `Found` | `Found` | `[7.398-15.872; 24.97-26.839; 33.569-36.824; 40.23-41.545; 64.691-66.22; 80.801-84.106; 111.629-115.073; 117.164-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE24_2` | `PDFE24` | `2` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE24_3` | `PDFE24` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE25_1` | `PDFE25` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE25_2` | `PDFE25` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE25_3` | `PDFE25` | `3` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE26_1` | `PDFE26` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE26_2` | `PDFE26` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE26_3` | `PDFE26` | `3` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE27_1` | `PDFE27` | `1` | `Found` | `Found` | `[5.376-30.721; 31.579-41.990; 50.679-75.640; 76.960-77.449; 82.140-109.341; 114.634-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE27_2` | `PDFE27` | `2` | `Found` | `Found` | `[6.967-10.511; 20.060-24.264; 27.988-33.634; 60.700-64.264; 96.216-99.700; 112.192-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE27_3` | `PDFE27` | `3` | `Found` | `Found` | `[45.037-48.558]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE28_1` | `PDFE28` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE28_2` | `PDFE28` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE28_3` | `PDFE28` | `3` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE29_1` | `PDFE29` | `1` | `Found` | `Found` | `[1.463-3.362; 5.920-9.405; 14.556-20.917; 21.771-32.108; 33.582-38.233; 40.445-44.606; 48.921-51.802; 62.207-64.757; 79.428-84.250; 95.273-98.154; 100.849-103.922]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE29_2` | `PDFE29` | `2` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE29_3` | `PDFE29` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE30_1` | `PDFE30` | `1` | `Found` | `Found` | `[14.572-17.069; 24.540-26.474; 33.002-37.120; 40.497-41.948; 46.542-54.641; 56.696-60.238; 77.731-83.577; 92.018-112.547; 119-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE30_2` | `PDFE30` | `2` | `Found` | `Found` | `[34.659-36.985]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE30_3` | `PDFE30` | `3` | `Found` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE31_1` | `PDFE31` | `1` | `Found` | `Found` | `[55.797-58.507]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE31_2` | `PDFE31` | `2` | `Found` | `Found` | `[58.525-60.958; 69.535-73.376; 114.470-117.436]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE31_3` | `PDFE31` | `3` | `Found` | `Found` | `[59.849-62.068; 69.938-71.667; 106.598-108.284]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE32_1` | `PDFE32` | `1` | `Found` | `Found` | `[54.493-55.339; 95.998-96.943]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE32_2` | `PDFE32` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE32_3` | `PDFE32` | `3` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE33_1` | `PDFE33` | `1` | `Found` | `Found` | `[25.971-27.508; 46.060-49.431; 53.509-58.939; 78.628-100.005; 104.172-109.335; 114.581-120]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE33_2` | `PDFE33` | `2` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE33_3` | `PDFE33` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE34_1` | `PDFE34` | `1` | `Found` | `Found` | `[13.593-17.860; 44.262-52.881; 83.447-95.736]` | `VALID` | Video, IMU, and annotation verified |
| `PDFE34_2` | `PDFE34` | `2` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE34_3` | `PDFE34` | `3` | `Missing` | `Missing` | `-` | `NOT CONDUCTED` | Spreadsheet indicates session was not recorded or data is absent ('-') |
| `PDFE35_1` | `PDFE35` | `1` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE35_2` | `PDFE35` | `2` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |
| `PDFE35_3` | `PDFE35` | `3` | `Found` | `Found` | `0` | `VALID` | Video, IMU, and annotation verified |

---

## 7. Error Pattern Analysis

### A. High False-Positive Rate During Voluntary Turning Movements
- **Evidence**: A significant portion of false positive episodes cite `gyro_z_var` (superior-inferior axis rotational variance) and `accel_rms` as primary cues.
- **Observed Association**: In turning protocols, patients naturally pivot their trunk and pelvis. The 1.0s rolling variance window captures turning angular velocity fluctuations that resemble the irregular tremor or hesitation of freezing.

### B. Episode Fragmentation
- **Evidence**: Single clinical ground-truth episodes (e.g. `PDFE31_1` at `55.8s–58.5s`) are frequently fragmented by the model into 2 or more discrete sub-episodes (e.g. `55.4s–57.6s` and `58.0s–61.2s`).
- **Observed Association**: Small temporal dips in posterior probability below 0.60 split contiguous episodes. While the current 1.0s merge gap bridges some gaps, high-frequency probability jitter causes fragmentation.

### C. Sensitivity vs Specificity Tradeoff
- **Evidence**: High episode recall (sensitivity) accompanied by low precision.
- **Observed Association**: The model was trained with `class_weight='balanced'`, which penalizes missed FoG windows heavily during training. In a dataset where FoG accounts for a small fraction of overall gait time, balanced class weighting naturally skews the classifier toward over-predicting the minority class.

---

## 8. Provenance & Reproducibility

- **Model Path**: `/Users/shriram/Documents/Projects/NeuroGait/models/fog_model.pkl`
- **Model SHA256**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **Evaluation Script**: `scripts/evaluate_dataset_ground_truth.py`
- **Unit Test Suite**: `tests/test_ground_truth_validation.py`
- **CSV Artifact**: `outputs/ground_truth_predictions.csv`
- **JSON Artifact**: `outputs/evaluation_summary.json`