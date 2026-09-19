# NeuroGait — Gate 7B Real Hardware Validation Report
## Local Camera + Physical Phone IMU

**Execution Date:** 2026-09-19
**Audit & Validation Protocol:** Real Hardware Feasibility & Integration Test
**Final Status:** **BLOCKED**

---

## 1. Executive Summary

Gate 7B marks the transition from simulated/replay data emulation (Gate 7A) to **physical hardware integration**:
- Target: Physical laptop camera (MacBook Air Camera) + physical mobile device IMU (accelerometer/gyroscope) + real-time timestamps + real-time synchronization + frozen Phase 1 model (`models/fog_model.pkl`).
- Core Anti-Simulation Rule: **No prerecorded video, no replay files, no synthetic IMU fabrication.** If physical hardware cannot be accessed or authorization is withheld, the run must halt and report the exact blocker without creating a fake success path.

### Outcome:
Gate 7B is **BLOCKED** by two independent physical hardware constraints:
1. **`CAMERA_ACCESS_BLOCKED`**: macOS Transparency, Consent, and Control (TCC) subsystem denies camera access to the calling terminal/IDE process. Direct OpenCV invocation (`cv2.VideoCapture(0)`) fails immediately with `cap.isOpened() == False`.
2. **`PHONE_IMU_UNAVAILABLE`**: No active physical phone IMU bridge or streaming sensor listener was detected across local network interfaces (ports 8080, 8081, 5000, 3000, 9090, 8000, 4242).

In accordance with Section 14 and the Final Operating Rule, no synthetic or replay fallback was permitted. The hardware probe and independent verification script strictly fail with status `BLOCKED`.

---

## 2. Hardware Reconnaissance & Environment

- **Host Machine:** Apple Silicon (macOS arm64, Darwin 24.x)
- **Python Environment:** Python 3.13.15 (`/Users/shriram/Documents/Projects/NeuroGait/.venv`)
- **Camera Device Identified:**
  - Physical Device: `MacBook Air Camera` (System Profiler ID: `6C707041-05AC-0010-000C-000000000001`)
  - Target OpenCV Device Index: `0`
- **Phone Device Identified:** None connected over local subnet or serial bridge.
- **Local Network Listeners:** Scanned ports 8080, 8081, 5000, 3000, 9090, 8000, 4242. Ports 5000 and 3000 are active web services, but zero sensor streaming bridges are present.

---

## 3. Physical Camera Hardware Test

### Probe Command:
```bash
.venv/bin/python -c '
import cv2
cap = cv2.VideoCapture(0)
print("cap.isOpened():", cap.isOpened())
'
```

### Raw System Output:
```text
OpenCV: camera access has been denied. Either run 'tccutil reset Camera' command in same terminal to reset application authorization status, either modify 'System Preferences -> Security & Privacy -> Camera' settings for your application.
OpenCV: camera failed to properly initialize!
[ WARN:0@0.065] global cap_ffmpeg_impl.hpp:1240 open VIDEOIO/FFMPEG: Failed list devices for backend avfoundation
cap.isOpened(): False
Camera 0 could not be opened.
```

### Direct Measurements:
- `frames_received`: 0
- `elapsed_time`: 0.0 s
- `effective_fps`: 0.0
- `frame_dimensions`: None
- `timestamps_monotonic`: N/A
- `camera_access_granted`: False
- `blocker`: `CAMERA_ACCESS_BLOCKED`

---

## 4. Physical Phone IMU Test

### Probe Mechanism:
`scripts/test_gate7b_hardware.py` scanned standard local ports for active streaming endpoints (e.g., Sensor Logger, Phyphox, custom WebSocket/UDP stream).

### Direct Measurements:
- `active_ports`: `[5000, 3000]` (unrelated local HTTP web apps)
- `samples_received`: 0
- `sampling_rate`: 0.0 Hz
- `phone_connected`: False
- `blocker`: `PHONE_IMU_UNAVAILABLE`

---

## 5. Sensor Metadata & Canonical Axis Mapping Requirements

When physical mobile hardware is connected, the required canonical mapping into NeuroGait is:

| NeuroGait Canonical Field | Physical Quantity | Standard Units | Mobile Device Phone Orientation |
| :--- | :--- | :--- | :--- |
| `timestamp` | Elapsed session time | Seconds ($\text{s}$, float) | Common monotonic reference clock |
| `accel_y` | Anteroposterior linear acceleration | $\text{g}$ ($1\text{ g} = 9.80665\text{ m/s}^2$) | Aligned with direction of travel (AP axis) |
| `gyro_x` | Mediolateral angular velocity | $\text{deg/s}$ | Pitch / sagittal rotation (ML axis) |
| `gyro_z` | Superior-inferior angular velocity | $\text{deg/s}$ | Yaw / axial turning rotation (SI axis) |

*Status*: Unresolved pending physical mobile device pairing.

---

## 6. Time Synchronization & Streaming Feasibility

- **Synchronization Boundary**: $\pm 0.1\text{ second}$ nearest timestamp match.
- **Minimum Requirement**: $\ge 10$ fused rows required to proceed with model inference.
- **Current Run Status**: 0 camera frames, 0 IMU samples, 0 fused rows. Temporal synchronization halted at safety boundary.

---

## 7. Model Inference & Pipeline Preservation

In strict compliance with frozen baseline rules:
- **Model File**: `models/fog_model.pkl` (SHA256: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`)
- **Canonical Feature Ordering**: Preserved (`left_ankle_velocity`, `right_ankle_velocity`, `left_knee_angle`, `right_knee_angle`, `stride_width`, `accel_rms`, `gyro_x_var`, `gyro_z_var`).
- **Post-Processing Bands**: Preserved ($p < 0.40$ Normal, $0.40 \le p < 0.60$ Borderline, $p \ge 0.60$ FoG).
- **Synthetic Replay Used**: `False`. No fake data injected.

---

## 8. Independent Verification Execution

### Command:
```bash
.venv/bin/python scripts/independent_gate7b_verification.py outputs/gate7b_hardware_run.json
```

### Raw Output:
```text
=================================================================
NEUROGAIT INDEPENDENT GATE 7B HARDWARE VERIFICATION
=================================================================

[1/8] Verifying Frozen Phase 1 Model Artifact...
      Model SHA256: 02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf [PASS]

[2/8] Verifying Canonical 8-Feature Ordering...
      Canonical Features: ['left_ankle_velocity', 'right_ankle_velocity', 'left_knee_angle', 'right_knee_angle', 'stride_width', 'accel_rms', 'gyro_x_var', 'gyro_z_var'] [PASS]

[3/8] Inspecting Hardware Execution Artifact...
      [BLOCKED] Hardware run did not succeed. Status: BLOCKED, Blocker: CAMERA_ACCESS_BLOCKED

[4/8] Verifying Physical Camera Frame Production...
      Camera Hardware:   MacBook Air Camera (Device Index 0)
      Frames Processed:  0

[5/8] Verifying Physical Phone IMU Production...
      Phone Hardware:    None (No bridge connected)
      IMU Samples:       0

[6/8] Verifying Temporal Synchronization & Fused Rows...
      Fused Rows:        0

[7/8] Verifying Data Mode & Anti-Replay Invariants...
      Data Mode:         none

[8/8] Verifying Canonical Output Schema...
      Episode Count:     0

=================================================================
>>> INDEPENDENT VERIFICATION VERDICT: BLOCKED / FAILED (7 errors) <<<
  • HARDWARE_STATUS_NOT_SUCCESS: Status=BLOCKED, Blocker=CAMERA_ACCESS_BLOCKED
  • CAMERA_ZERO_FRAMES: Received 0 camera frames (CAMERA_ACCESS_BLOCKED).
  • CAMERA_ACCESS_NOT_GRANTED: macOS camera permission denied.
  • PHONE_ZERO_SAMPLES: Received 0 IMU samples (PHONE_IMU_UNAVAILABLE).
  • PHONE_IMU_NOT_CONNECTED: Physical phone IMU was not connected.
  • INSUFFICIENT_FUSED_ROWS: 0 fused rows (< 10 required).
  • INVALID_DATA_MODE: data_mode must be 'real' for Gate 7B, got 'none'.
=================================================================
```

---

## 9. Gate 7A Isolation & Pytest Regression

- Gate 7A replay and parity testing remain 100% operational.
- Existing unit and integration tests remain 100% passing (88/88 passed).
- Zero code modifications were made to core ML, pose, or IMU processing modules.

---

## 10. Remediation Requirements for Physical Unblocking

To achieve a `VERIFIED` Gate 7B result:
1. **Camera Authorization**: The user must grant camera permission to the terminal or parent application hosting Antigravity in macOS:
   - Navigate to `System Settings -> Privacy & Security -> Camera`
   - Enable Camera access for the Terminal / IDE app.
2. **Phone IMU Stream**: The user must launch an IMU streaming client on a physical phone on the same local network:
   - Recommended apps: *Sensor Logger* (iOS/Android) streaming JSON/CSV over HTTP or WebSocket, or *Phyphox* network stream.
   - Configure the stream to emit triaxial acceleration and gyroscope with timestamps.
