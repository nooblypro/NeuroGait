# NeuroGait — Adversarial Verification of External Multimodal FoG Dataset Search

**Date**: 2026-09-19
**Audit Type**: Independent Adversarial Audit & Verification
**Auditor**: NeuroGait Adversarial Verification Agent

---

## 1. Executive Summary & Statement of Objective

This report constitutes an **independent, adversarial audit** of the external Freezing of Gait (FoG) dataset search conducted for the NeuroGait system.

### Prior Claim Under Audit:
> "No publicly accessible external dataset meeting all conditions for complete multimodal (Video + IMU + FoG Labels) validation was identified."

### Audit Methodology:
- **Null Assumption**: The prior conclusion was treated as unverified and potentially flawed.
- **Verification Rule**: No previous AGY report was accepted as evidence. Every dataset candidate, claim, and modality was independently researched, cross-referenced against original peer-reviewed literature, repository API file manifests, dataset documentation, and downloadable sample ranges where accessible.
- **Privacy vs Nonexistence Distinction**: Video absence was rigorously categorized into:
  - (A) Video never collected
  - (B) Video collected in study but intentionally withheld from public release (e.g., GDPR/HIPAA/ethics)
  - (C) Video publicly available
  - (D) Video under controlled access / Data Use Agreement (DUA)
  - (E) Video available via companion dataset

---

## 2. Repositories and Archives Searched

The following 13 data repositories and publication archives were independently audited:
1. **Zenodo** (`zenodo.org`) — Direct REST API queries for FoG-STAR (`16989602`, `17838806`) and Kuopio (`10559504`).
2. **Figshare** (`figshare.com` / `api.figshare.com`) — Direct REST API queries for baseline turning-in-place (`14984667`), Toronto Archive (`19929893`), and overground kinematics (`14896881`).
3. **PhysioNet** (`physionet.org`) — Audited for tDCS-FOG, DeFOG, and Gait in Parkinson's Disease (`gaitpdb`).
4. **Mendeley Data** (`data.mendeley.com`) — Audited for Li et al. multimodal datasets (`10.17632/r8gmbtv7w2.3`, `10.17632/t8j8v4hnm4.1`, SenseFOG).
5. **UCI Machine Learning Repository** (`archive.ics.uci.edu`) — Audited for Daphnet FoG (Dataset ID 245).
6. **Synapse / Sage Bionetworks** (`synapse.org`) — Audited for WearGait-PD (`syn52540892`).
7. **4TU.ResearchData** (`data.4tu.nl`) — Audited for Delgado-Terán ankle sensor dataset (`10.4121/40e06061-f441-43b5-9235-006829206509`).
8. **IEEE DataPort** (`ieee-dataport.org`) — Audited for `10.21227/5ch0-8b29` (EEG/EMG) and `10.21227/g2g8-1503` (Adams et al. accelerometry).
9. **OpenNeuro** (`openneuro.org`) — Audited for `ds003505` and general Parkinson datasets.
10. **Dryad Digital Repository** (`datadryad.org`) — Audited for Parkinson FoG collections.
11. **Harvard Dataverse** (`dataverse.harvard.edu`) — Audited for multimodal gait archives.
12. **Kaggle** (`kaggle.com`) — Audited for TLVMC Parkinson's Freezing of Gait Prediction competition data.
13. **PubMed Central / NLM / Publisher Sites** (`ncbi.nlm.nih.gov/pmc`, `journals.sagepub.com`, `frontiersin.org`) — Inspected Data Availability and Methods sections of primary publications.

---

## 3. Independent Audit of Previous 7 Candidates

### Candidate 1: FoG-STAR
- **DATASET**: FoG-STAR: Freezing of Gait Severity, Tasks, Activities, and Ratings
- **SOURCE**: Zenodo
- **DOI**: [10.5281/zenodo.16989602](https://doi.org/10.5281/zenodo.16989602) / [10.5281/zenodo.17838806](https://doi.org/10.5281/zenodo.17838806) (Version 3.0)
- **OFFICIAL LANDING PAGE**: https://zenodo.org/records/17838806
- **PAPER**: Borzì, L. et al. (2025). "Freezing of gait detection: The effect of sensor type, position, activities, datasets, and machine learning model." *Journal of Parkinson's Disease*, 15(1), 163-181. DOI: [10.1177/1877718X241302766](https://doi.org/10.1177/1877718X241302766).
- **LICENSE**: CC BY 4.0
- **ACCESS REQUIREMENTS**: Open Access (no login or DUA required for sensor files).
- **VIDEO**: **NO** in public distribution (Category B: collected in clinic at 10 fps to produce ground truth annotations, but withheld from repository distribution).
- **RAW ACCELEROMETER**: **YES** (Tri-axial accelerometer in g at left ankle, right ankle, lower back, wrist @ 60 Hz).
- **RAW GYROSCOPE**: **YES** (Tri-axial gyroscope in deg/s at left ankle, right ankle, lower back, wrist @ 60 Hz).
- **TIMESTAMPS**: **YES** (Millisecond resolution float timestamps in `timestamp` column).
- **VIDEO/IMU SYNCHRONIZATION**: **NO** for validation (IMUs were synchronized with each other and with clinical video during labeling, but video files are withheld, making end-to-end multimodal video-IMU sync impossible for outside users).
- **FoG GROUND TRUTH**: **YES** (`fog`: 0/1 binary, and `fog_severity`: 1=Shuffling, 2=Trembling, 3=Akinesia).
- **FOG LABEL FORMAT**: **WINDOW / SAMPLE** (Sample-level annotation at 60 Hz).
- **PARKINSON'S SUBJECTS**: **YES** (22 individuals with Parkinson's disease).
- **PUBLIC RAW DATA**: **RESTRICTED / SENSOR ONLY** (Raw sensor CSV is public; raw video is absent).
- **EVIDENCE**:
  - Zenodo API record query for `17838806` confirms exact file listing:
    1. `clinical_data.csv` (698 bytes)
    2. `sensor_data.csv` (119,629,580 bytes)
    3. `fogstar_environment.yaml` (138 bytes)
    4. `FoG_Star_Analytics.ipynb` (115,520 bytes)
    5. `README.txt` (4,734 bytes)
  - `README.txt` line 26 explicitly states: *"Annotations derived from synchronized video (10 fps) include FoG episodes, FoG severity scores, activity labels, and task identifiers."*
  - HTTP Range header byte inspection of `sensor_data.csv` header confirms raw sensor channels: `timestamp,ankleL_acc_x,ankleL_acc_y,ankleL_acc_z,ankleL_gyro_x,ankleL_gyro_y,ankleL_gyro_z,ankleR_acc_x,ankleR_acc_y,ankleR_acc_z,ankleR_gyro_x,ankleR_gyro_y,ankleR_gyro_z,back_acc_x,back_acc_y,back_acc_z,back_gyro_x,back_gyro_y,back_gyro_z,wrist_acc_x,wrist_acc_y,wrist_acc_z,wrist_gyro_x,wrist_gyro_y,wrist_gyro_z,activity,fog,fog_severity,subjectID,sessionID,taskID`.
  - No separate controlled-access video repo exists.
- **QUALIFICATION**: **Class B** (Missing Raw Video).

---

### Candidate 2: Kaggle FoG Prediction (tDCS-FOG & DeFOG)
- **DATASET**: TLVMC Parkinson's Freezing of Gait Prediction (tDCS-FOG & DeFOG)
- **SOURCE**: PhysioNet / Kaggle / Tel Aviv Sourasky Medical Center
- **DOI / URL**: [kaggle.com/competitions/tlvmc-parkinsons-freezing-gait-prediction](https://www.kaggle.com/competitions/tlvmc-parkinsons-freezing-gait-prediction)
- **PAPER**: Hausdorff et al. / Weiss et al. (Clinical trials on tDCS and home-based FoG monitoring).
- **LICENSE**: Competition Rules & Academic Research Data Use Agreement.
- **ACCESS REQUIREMENTS**: Kaggle account registration and agreement to competition terms.
- **VIDEO**: **NO** in public distribution (Category B: recorded in lab/home during protocol, annotated frame-by-frame by clinical experts, but video files withheld to protect patient privacy).
- **RAW ACCELEROMETER**: **YES** (3D accelerometer worn on lower back: `AccV`, `AccML`, `AccAP` @ 100 Hz for DeFOG, 128 Hz for tDCS-FOG).
- **RAW GYROSCOPE**: **NO** (Accelerometers only; no angular velocity sensors).
- **TIMESTAMPS**: **YES** (`Time` column in samples/milliseconds).
- **VIDEO/IMU SYNCHRONIZATION**: **NO** for external pipeline (annotated from video, but no public video stream).
- **FoG GROUND TRUTH**: **YES** (Binary flags: `StartHesitation`, `Turn`, `Walking`).
- **FOG LABEL FORMAT**: **WINDOW / SAMPLE** (Sample-by-sample binary indicators).
- **PARKINSON'S SUBJECTS**: **YES** (Clinical Parkinson's cohort experiencing freezing).
- **PUBLIC RAW DATA**: **RESTRICTED / SENSOR ONLY** (Accelerometer CSVs only; no video).
- **EVIDENCE**:
  - Kaggle competition data page shows files: `train/tdcsfog/*.csv`, `train/defog/*.csv`, `train/notype/*.csv`, `metadata.csv`.
  - Column schema: `Time, AccV, AccML, AccAP, StartHesitation, Turn, Walking`. No gyro columns, no video files.
- **QUALIFICATION**: **Class C** (Missing Video AND Missing Gyroscope).

---

### Candidate 3: Mendeley Multimodal FoG
- **DATASET**: Multimodal Dataset of Freezing of Gait in Parkinson's Disease
- **SOURCE**: Mendeley Data
- **DOI**: [10.17632/r8gmbtv7w2.3](https://doi.org/10.17632/r8gmbtv7w2.3) (Filtered) / [10.17632/t8j8v4hnm4.1](https://doi.org/10.17632/t8j8v4hnm4.1) (Raw)
- **OFFICIAL LANDING PAGE**: https://data.mendeley.com/datasets/r8gmbtv7w2/3
- **PAPER**: Li, H. et al. (2021/2022). Multimodal dataset of freezing of gait in Parkinson's disease.
- **LICENSE**: CC BY 4.0
- **ACCESS REQUIREMENTS**: Open Access.
- **VIDEO**: **NO** in public release (Category B: video captured in clinic for neurologist annotations, but video files withheld under medical ethics / patient privacy regulations).
- **RAW ACCELEROMETER**: **YES** (Triaxial acceleration).
- **RAW GYROSCOPE**: **NO** (Includes EEG, EMG, ECG, Skin Conductance, and Accelerometer; lacks Gyroscope).
- **TIMESTAMPS**: **YES**.
- **VIDEO/IMU SYNCHRONIZATION**: **NO** for external pipeline.
- **FoG GROUND TRUTH**: **YES** (Onset and offset annotated by qualified physicians).
- **FOG LABEL FORMAT**: **TIMESTAMP / EPISODE**.
- **PARKINSON'S SUBJECTS**: **YES** (12 patients with Parkinson's disease).
- **PUBLIC RAW DATA**: **RESTRICTED / SENSOR ONLY** (No video).
- **EVIDENCE**:
  - Mendeley data repository file list contains `.mat` / `.csv` arrays of EEG, EMG, ACC.
  - Published research papers utilizing this dataset note that raw video is excluded due to hospital clinical data protection rules.
- **QUALIFICATION**: **Class C** (Missing Video AND Missing Gyroscope).

---

### Candidate 4: Daphnet FoG
- **DATASET**: Daphnet Freezing of Gait Data Set
- **SOURCE**: UCI Machine Learning Repository
- **DOI / URL**: [archive.ics.uci.edu/dataset/245](https://archive.ics.uci.edu/dataset/245/daphnet+freezing+of+gait)
- **OFFICIAL LANDING PAGE**: https://archive.ics.uci.edu/dataset/245/daphnet+freezing+of+gait
- **PAPER**: Bächlin, M. et al. (2010). "Wearable Assistant for Parkinson's Disease Patients With the Freezing of Gait Symptom." *IEEE Transactions on Information Technology in Biomedicine*, 14(2), 436–446.
- **LICENSE**: Open Access (Academic citation).
- **ACCESS REQUIREMENTS**: Open Access.
- **VIDEO**: **NO** (Category B: 25 Hz digital camera recorded trials to establish gold standard, but video files were never uploaded or released in the archive).
- **RAW ACCELEROMETER**: **YES** (3 tri-axial accelerometers: shank/ankle, thigh, trunk @ 64 Hz).
- **RAW GYROSCOPE**: **NO** (Accelerometers only; no angular velocity sensors).
- **TIMESTAMPS**: **YES** (Timestamp in milliseconds in column 1).
- **VIDEO/IMU SYNCHRONIZATION**: **NO** for external pipeline.
- **FoG GROUND TRUTH**: **YES** (0=Not experiment, 1=No freeze, 2=Freeze).
- **FOG LABEL FORMAT**: **WINDOW / SAMPLE** (Sample-level at 64 Hz).
- **PARKINSON'S SUBJECTS**: **YES** (10 PD patients, 8 exhibiting FoG).
- **PUBLIC RAW DATA**: **YES for Accel / NO for Video**.
- **EVIDENCE**:
  - UCI dataset archive contains raw `.txt` files (`S01R01.txt` ... `S10R01.txt`).
  - 10 sensor columns + 1 label column: Time (ms), Shank Acc (x,y,z), Thigh Acc (x,y,z), Trunk Acc (x,y,z), Label. No gyro channels, no video files.
- **QUALIFICATION**: **Class C** (Missing Video AND Missing Gyroscope).

---

### Candidate 5: Kuopio Gait Dataset
- **DATASET**: Kuopio gait dataset: motion capture, inertial measurement and video-based sagittal-plane keypoint data from walking trials
- **SOURCE**: Zenodo
- **DOI**: [10.5281/zenodo.10559504](https://doi.org/10.5281/zenodo.10559504)
- **OFFICIAL LANDING PAGE**: https://zenodo.org/records/10559504
- **PAPER**: Lavikainen, J. et al. (2024). University of Eastern Finland HUMEA Laboratory.
- **LICENSE**: CC BY 4.0
- **ACCESS REQUIREMENTS**: Open Access.
- **VIDEO**: **NO** (Category B: sagittal-plane video recorded, but converted to OpenPose BODY_25 JSON keypoint files; raw video `.mp4`/`.avi` is withheld from the archive).
- **RAW ACCELEROMETER**: **YES** (Movella Xsens MTw Awinda on pelvis, thighs, shanks, feet @ 100 Hz).
- **RAW GYROSCOPE**: **UNCLEAR / DERIVED ONLY** (`rotationMatrix` and `quaternion` provided; raw angular velocity deg/s not directly in extracted structs).
- **TIMESTAMPS**: **YES** (100 Hz frame time stamps).
- **VIDEO/IMU SYNCHRONIZATION**: **YES** (Synchronized in laboratory capture setup).
- **FoG GROUND TRUTH**: **NO** (No FoG events, no freezing protocol).
- **FOG LABEL FORMAT**: **N/A** (No FoG).
- **PARKINSON'S SUBJECTS**: **NO** (51 healthy voluntary participants).
- **PUBLIC RAW DATA**: **RESTRICTED** (Kinematics and OpenPose JSON public; raw video withheld).
- **EVIDENCE**:
  - Zenodo record inspects `readme.txt` line 3: *"The data is from 51 willing participants... Excel file has ID, Age, Gender, Leg, Height... knee width, ankle width, thigh length... Mass."*
  - `readme.txt` explicitly documents: *"openpose: Trajectories of the keypoints identified from sagittal plane video frames, saved as json files."*
  - No Parkinson's patients, no FoG events.
- **QUALIFICATION**: **Class D** (Irrelevant: Healthy subjects, No Parkinson's, No FoG, No raw video).

---

### Candidate 6: Toronto Older Adults Gait Archive
- **DATASET**: Walking videos / The Toronto Older Adults Gait Archive (TOAGA)
- **SOURCE**: Figshare
- **DOI**: [10.6084/m9.figshare.19929893](https://doi.org/10.6084/m9.figshare.19929893)
- **OFFICIAL LANDING PAGE**: https://doi.org/10.6084/m9.figshare.19929893
- **PAPER**: Mehdizadeh, S., Nabavi, H., Sabo, A., Arora, T., Iaboni, A., Taati, B. (2022). "The Toronto older adults gait archive: video and 3D inertial motion capture data of older adults' walking." *Scientific Data*, 9, 398.
- **LICENSE**: CC0 (Public Domain)
- **ACCESS REQUIREMENTS**: Open Access.
- **VIDEO**: **YES** (Category C: `Videos.zip`, 2.35 GB, dual-camera 1080x1920 MP4 walking recordings).
- **RAW ACCELEROMETER**: **NO** (Xsens MVN biomechanical skeleton coordinates / BVH files; no raw triaxial accelerometer time-series in this archive).
- **RAW GYROSCOPE**: **NO** (No angular velocity time-series).
- **TIMESTAMPS**: **YES** (Video container timestamps).
- **VIDEO/IMU SYNCHRONIZATION**: **N/A** (No raw IMU in archive).
- **FoG GROUND TRUTH**: **NO** (General walking and balance assessments: BBS, FES-I; no FoG episodes).
- **FOG LABEL FORMAT**: **N/A** (No FoG).
- **PARKINSON'S SUBJECTS**: **NO** (14 older adults with and without cognitive impairment/dementia; not a PD FoG cohort).
- **PUBLIC RAW DATA**: **YES for Video / NO for Raw IMU**.
- **EVIDENCE**:
  - Figshare API shows single file `Videos.zip` (2,351,609,541 bytes).
  - Mehdizadeh et al. (2022) confirm participant cohort: 14 older adults, 60-second overground walking trials.
- **QUALIFICATION**: **Class C** (Missing Raw IMU AND Missing FoG Labels).

---

### Candidate 7: WearGait-PD
- **DATASET**: WearGait-PD: A Multimodal Dataset for Gait and Balance in Parkinson's Disease
- **SOURCE**: Synapse (Sage Bionetworks) / FDA / VA / Johns Hopkins University
- **DOI / URL**: [synapse.org/Synapse:syn52540892](https://www.synapse.org/Synapse:syn52540892)
- **OFFICIAL LANDING PAGE**: https://www.synapse.org/Synapse:syn52540892/wiki/
- **PAPER**: FDA / VA multi-center study on wearable sensors for Parkinson's disease (medRxiv / clinical reports 2024).
- **LICENSE**: Open Access via Synapse Data Use Terms.
- **ACCESS REQUIREMENTS**: Synapse registered account.
- **VIDEO**: **NO** in public distribution (Category B: trials recorded with synchronized video cameras to generate frame-by-frame activity annotations; raw video excluded due to HIPAA/patient privacy requirements).
- **RAW ACCELEROMETER**: **YES** (13 Opal/APDM IMUs + sensorized insoles).
- **RAW GYROSCOPE**: **YES** (Triaxial gyroscope on 13 body segments).
- **TIMESTAMPS**: **YES** (Synchronized to GAITRite walkway reference).
- **VIDEO/IMU SYNCHRONIZATION**: **NO** for external pipeline (video withheld).
- **FoG GROUND TRUTH**: **PARTIAL / ACTIVITY ANNOTATIONS** (Frame-by-frame activity labels: walk, turn, sit, stand; occasional FoG events observed, but lacks standardized millisecond episode boundaries across standard FoG-provoking protocols).
- **PARKINSON'S SUBJECTS**: **YES** (100 individuals with PD, 85 age-matched controls).
- **PUBLIC RAW DATA**: **RESTRICTED / SENSOR ONLY** (Raw sensor files on Synapse; no raw video).
- **EVIDENCE**:
  - Synapse file schema and medRxiv preprint confirm raw sensor arrays and frame-by-frame activity CSVs.
  - Video files withheld for privacy protection.
- **QUALIFICATION**: **Class B/C** (Missing Raw Video; Non-standardized FoG labels).

---

## 4. Independent Audit of New Candidates Discovered

### Candidate 8: 4TU Ankle Sensor Semi-Free Living FoG Dataset
- **SOURCE**: 4TU.ResearchData
- **DOI**: [10.4121/40e06061-f441-43b5-9235-006829206509](https://doi.org/10.4121/40e06061-f441-43b5-9235-006829206509)
- **PAPER**: Delgado-Terán, J.D. et al. (2025). "Ankle Sensor-Based Detection of Freezing of Gait in Parkinson's Disease in Semi-Free Living Environments." *Sensors*, 25(6), 1895. DOI: [10.3390/s25061895](https://doi.org/10.3390/s25061895).
- **MODALITIES**: Right ankle accelerometer and gyroscope tensors.
- **VIDEO**: **NO** (Category A/B: semi-free living inertial sensors; no public video).
- **FOG LABELS**: **YES** (Expert annotated).
- **PARKINSON'S**: **YES**.
- **QUALIFICATION**: **Class C** (Missing Video).

### Candidate 9: Figshare Parkinson Full-Body Kinematics (Overground Walking)
- **SOURCE**: Figshare
- **DOI**: [10.6084/m9.figshare.14896881](https://doi.org/10.6084/m9.figshare.14896881)
- **PAPER**: Full-body kinematics and kinetics signals of 26 PD individuals overground walking.
- **MODALITIES**: Optical motion capture (`C3Dfiles.zip`), force plates.
- **VIDEO**: **NO** (C3D marker coordinates only).
- **RAW IMU**: **NO** (No wearable accelerometer/gyroscope).
- **FOG LABELS**: **NO** (Steady overground walking ON/OFF medication; no freezing).
- **QUALIFICATION**: **Class D** (Irrelevant: MoCap only, no IMU, no video, no FoG).

### Candidate 10: IEEE DataPort Pd-biostamprc21
- **SOURCE**: IEEE DataPort
- **DOI**: [10.21227/g2g8-1503](https://doi.org/10.21227/g2g8-1503)
- **PAPER**: Adams, J.L. et al. (2020). Parkinson's disease accelerometry from 5 wearable sensors.
- **MODALITIES**: 5 MC10 BioStamp RC accelerometers.
- **VIDEO**: **NO**.
- **RAW GYROSCOPE**: **NO** (Accelerometers only).
- **FOG LABELS**: **NO** (Tremor and general gait measures).
- **QUALIFICATION**: **Class D** (Irrelevant).

### Candidate 11: PhysioNet Gait in Parkinson's Disease (gaitpdb)
- **SOURCE**: PhysioNet
- **DOI / URL**: [physionet.org/content/gaitpdb/1.0.0](https://physionet.org/content/gaitpdb/1.0.0/)
- **PAPER**: Hausdorff, J.M. et al. (Gait dynamics and stride-to-stride variability).
- **MODALITIES**: Vertical Ground Reaction Force (VGRF, 8 force sensors per foot).
- **VIDEO**: **NO**.
- **RAW IMU**: **NO** (Force plates/insoles only; no IMU).
- **FOG LABELS**: **NO** (Steady continuous walking; no freezing episodes).
- **QUALIFICATION**: **Class D** (Irrelevant).

---

## 5. Comprehensive Qualification Matrix

| # | Dataset | Video | Raw Accel | Raw Gyro | FoG Labels | Sync | Public Access | Qualification Category | Primary Limitation |
|---|---|---|---|---|---|---|---|---|---|
| **0** | **Figshare Turning-in-Place** *(Baseline/Train)* | **YES** | **YES** | **YES** | **YES** | **YES** | **Open (CC BY 4.0)** | **Class A** *(Baseline)* | *Already used for Phase 1 model training (`models/fog_model.pkl`)* |
| 1 | **FoG-STAR** (Zenodo) | **NO** *(B)* | **YES** | **YES** | **YES** | **NO** | **Restricted / Sensor only** | **Class B** | Video recorded at 10 fps for labeling but withheld from Zenodo |
| 2 | **Kaggle tDCS-FOG & DeFOG** | **NO** *(B)* | **YES** | **NO** | **YES** | **NO** | **Restricted / DUA** | **Class C** | Video withheld; lumbar accel only; lacks gyroscope |
| 3 | **Mendeley Multimodal FoG** | **NO** *(B)* | **YES** | **NO** | **YES** | **NO** | **Restricted / Sensor only** | **Class C** | Video withheld; lacks gyroscope; EEG/EMG/accel only |
| 4 | **Daphnet FoG** (UCI) | **NO** *(B)* | **YES** | **NO** | **YES** | **NO** | **Open (Sensor only)** | **Class C** | Video withheld; 3 accelerometers only; lacks gyroscope |
| 5 | **Kuopio Gait Dataset** | **NO** *(B)* | **YES** | **NO** *(Derived)* | **NO** | **YES** | **Open (Sensor/JSON)** | **Class D** | Healthy subjects only (no PD/FoG); OpenPose JSON only (no video) |
| 6 | **Toronto Older Adults Archive** | **YES** *(C)* | **NO** | **NO** | **NO** | **N/A** | **Open (CC0)** | **Class C** | Video only; lacks raw IMU; lacks PD FoG labels |
| 7 | **WearGait-PD** (Synapse) | **NO** *(B)* | **YES** | **YES** | **PARTIAL** | **NO** | **Restricted (Synapse)** | **Class B/C** | Video withheld; lacks standardized FoG episode ground truth |
| 8 | **4TU Ankle FoG** | **NO** *(A/B)* | **YES** | **YES** | **YES** | **N/A** | **Open** | **Class C** | Inertial only (tensors); no video |
| 9 | **Figshare PD Overground MoCap** | **NO** | **NO** | **NO** | **NO** | **N/A** | **Open** | **Class D** | Optical MoCap only; no video, no IMU, no FoG |
| 10| **IEEE DataPort Pd-biostamprc21** | **NO** | **YES** | **NO** | **NO** | **N/A** | **Open** | **Class D** | Accelerometer only; no video, no FoG |
| 11| **PhysioNet gaitpdb** | **NO** | **NO** | **NO** | **NO** | **N/A** | **Open** | **Class D** | VGRF force sensors only; no video, no IMU, no FoG |

*Legend*:
- **Class A**: Complete candidate meeting all requirements (Video + Raw Accel + Raw Gyro + FoG Labels + Public Synchronization).
- **Class B**: Missing exactly one critical requirement (e.g., video withheld).
- **Class C**: Missing multiple critical requirements.
- **Class D**: Irrelevant clinical task or population.
- Video Status: *(A)* Never collected; *(B)* Collected but withheld from public release; *(C)* Publicly available; *(D)* Controlled access; *(E)* Companion dataset.

---

## 6. Critical Analysis & Root Cause of Public Multimodal Absence

Why is there **no independent Category-A dataset** publicly downloadable outside the Figshare baseline?

1. **Biometric Privacy and Clinical Ethics (GDPR / HIPAA)**:
   - Full-body video of patients walking, turning, or experiencing debilitating freezing episodes reveals facial features, body habitus, and private clinical vulnerability.
   - Institutional Review Boards (IRBs) and hospital ethics committees routinely grant consent to share **de-identified numerical sensor streams** (accelerometry, gyroscopy, force plates) and **timestamped clinical event tables**.
   - Public sharing of unmasked raw patient video recordings is almost universally prohibited unless explicit, rare video-release consent is obtained.

2. **The Figshare Baseline Dataset Exception**:
   - The Figshare turning-in-place dataset ([10.6084/m9.figshare.14984667](https://doi.org/10.6084/m9.figshare.14984667)), published alongside *Frontiers in Neuroscience* (2022), remains an exceptional rarity where explicit patient consent and ethics approval allowed the public CC0 release of 35 patient videos alongside synchronized 128 Hz triaxial IMU streams and expert FoG annotations.
   - Because this dataset was already used to train and validate the NeuroGait Phase 1 baseline model (`models/fog_model.pkl`), using it again would violate the independence requirement.

3. **Inertial-Only vs Video-Only Divergence in Current Literature**:
   - Wearable sensor research groups publish rich IMU data (FoG-STAR, Daphnet, 4TU, Kaggle) but withhold the clinical reference video.
   - Computer vision research groups publish video archives (Toronto Older Adults) or derived skeletal keypoint JSONs (Kuopio), but omit synchronized raw IMU signals.

---

## 7. Audit of the Previous Search Conclusion

### Previous AGY Conclusion:
> *"No publicly accessible external dataset meeting all conditions for complete multimodal (Video + IMU + FoG Labels) validation was identified."*

### Adversarial Verdict:
**The previous conclusion is FACTUALLY SUPPORTED and CORRECT.**

However, the previous report oversimplified the status of video in several datasets as simply "video withheld" or "no video". The rigorous adversarial distinction established by this audit is:
1. **FoG-STAR (Borzì et al.)**: Video **was collected** in the clinical protocol at 10 fps and used to create the FoG ground truth, but **is withheld** from the Zenodo repository (Status B). The published dataset contains only `sensor_data.csv` (119 MB) and `clinical_data.csv` (698 bytes).
2. **Kaggle tDCS-FOG & DeFOG (Hausdorff et al.)**: Clinical trials were videotaped and rated, but the competition data provides **only lumbar accelerometer time-series** without video and without gyroscope.
3. **Kuopio Gait Dataset**: Raw video was withheld; only OpenPose JSON keypoint tables were released. Furthermore, subjects are healthy controls with zero FoG episodes.
4. **Toronto Older Adults Gait Archive**: Contains raw video (`Videos.zip`, 2.35 GB), but lacks raw IMU time series (only BVH biomechanical models) and contains healthy/dementia older adults without Parkinson's FoG.

---

## 8. Data Integrity & Pipeline Protection

In strict adherence to the NeuroGait operating protocol:
- **Zero Model Modification**: `models/fog_model.pkl` was not touched. SHA256 integrity was independently verified.
- **Zero Feature Modification**: Canonical 8-feature contract (`CANONICAL_FEATURES`) was not modified.
- **Zero Threshold Modification**: Classification bands ($p < 0.40$ Normal, $0.40 \le p < 0.60$ Borderline, $p \ge 0.60$ FoG) were not altered.
- **Zero Data Fabrication**: No synthetic IMU signals were generated; no synthetic video frames were created.
- **Zero External Training**: No external datasets were used to retrain or fine-tune the model.
