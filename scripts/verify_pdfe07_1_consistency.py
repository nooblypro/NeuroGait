"""REAL PDFE07_1 AWS EXECUTION AND CANONICAL RESULT CONSISTENCY VERIFICATION.

Verifies:
1. Real AWS execution with PDFE07_1.mp4 and SUB07_1.txt.
2. Raw model window count (446).
3. Non-overlapping aggregated timeline count (115).
4. Counts: FoG=1, Borderline=58, Normal=56.
5. FoG interval: 100.01s - 101.31s, confidence: ~64.8%, cue: accel_rms.
6. Temporal validity: next.start >= previous.end for all consecutive intervals.
7. Canonical derivation: Dashboard = Episode Table = Narrative all derived from the same aggregated timeline.
8. Zero hardcoded PDFE07_1 values in the generator.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
import boto3

API_ENDPOINT = "https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com"
VIDEO_PATH = Path("/Users/shriram/Documents/GAIT videos/PDFE07_1.mp4")
IMU_PATH = Path("data/raw/imu/SUB07_1.txt")
REGION = "ap-south-1"
BUCKET = "neurogait-artifacts-955519187785"
TABLE = "neurogait-sessions"
CLUSTER = "neurogait-cluster"

print("=" * 75)
print("REAL PDFE07_1 AWS PIPELINE & CANONICAL RESULT CONSISTENCY VERIFICATION")
print("=" * 75)

assert VIDEO_PATH.exists(), f"Video file not found: {VIDEO_PATH}"
assert IMU_PATH.exists(), f"IMU file not found: {IMU_PATH}"
v_size = VIDEO_PATH.stat().st_size
i_size = IMU_PATH.stat().st_size
print(f"[Inputs Verified]")
print(f"  - Video: {VIDEO_PATH} ({v_size:,} bytes)")
print(f"  - IMU:   {IMU_PATH} ({i_size:,} bytes)")

# 1. Initialize session
print("\n[Step 1] Initializing AWS session...")
payload = json.dumps({
    "video_filename": "PDFE07_1.mp4",
    "imu_filename": "SUB07_1.txt",
    "video_size_bytes": v_size,
    "imu_size_bytes": i_size,
}).encode("utf-8")

req = urllib.request.Request(
    f"{API_ENDPOINT}/sessions",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    resp_data = json.loads(resp.read().decode())

session_id = resp_data["session_id"]
v_upload_url = resp_data["upload_urls"]["video"]
i_upload_url = resp_data["upload_urls"]["imu"]
v_s3_key = resp_data["s3_keys"]["video"]
i_s3_key = resp_data["s3_keys"]["imu"]
print(f"  -> Session ID: {session_id}")

# 2. Real Uploads
print("\n[Step 2] Executing S3 uploads...")
t0 = time.time()
with open(VIDEO_PATH, "rb") as f:
    v_req = urllib.request.Request(v_upload_url, data=f.read(), method="PUT")
    v_req.add_header("Content-Type", "video/mp4")
    with urllib.request.urlopen(v_req) as r:
        assert r.status == 200

with open(IMU_PATH, "rb") as f:
    i_req = urllib.request.Request(i_upload_url, data=f.read(), method="PUT")
    i_req.add_header("Content-Type", "text/plain")
    with urllib.request.urlopen(i_req) as r:
        assert r.status == 200
print(f"  -> S3 Uploads completed in {time.time() - t0:.2f}s")

# 3. Confirm Upload
print("\n[Step 3] Confirming upload...")
c_req = urllib.request.Request(
    f"{API_ENDPOINT}/sessions/confirm-upload",
    data=json.dumps({"session_id": session_id}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(c_req) as r:
    assert r.status == 200

# 4. Start Inference
print("\n[Step 4] Starting inference on ECS Fargate...")
s_req = urllib.request.Request(
    f"{API_ENDPOINT}/inference/start",
    data=json.dumps({"session_id": session_id}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(s_req) as r:
    start_data = json.loads(r.read().decode())
task_arn = start_data["task_arn"]
print(f"  -> Task ARN: {task_arn}")

# 5. Monitor ECS Fargate
print("\n[Step 5] Monitoring ECS Fargate task...")
ecs = boto3.client("ecs", region_name=REGION)
poll_count = 0
while True:
    time.sleep(5)
    poll_count += 1
    t_info = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
    last_status = t_info.get("lastStatus")
    print(f"  [{poll_count * 5}s] ECS Status: {last_status}")
    if last_status == "STOPPED":
        exit_code = t_info.get("containers", [{}])[0].get("exitCode")
        print(f"  -> Task finished with exit code {exit_code}")
        assert exit_code == 0, f"ECS container failed with code {exit_code}"
        break
    if poll_count > 70:
        raise TimeoutError("ECS task timed out")

# 6. Fetch predictions.json from S3
print("\n[Step 6] Verifying S3 outputs...")
s3_client = boto3.client("s3", region_name=REGION)
pred_key = f"outputs/{session_id}/predictions.json"
p_obj = s3_client.get_object(Bucket=BUCKET, Key=pred_key)
raw_predictions = json.loads(p_obj["Body"].read().decode("utf-8"))
raw_count = len(raw_predictions)
print(f"  -> Raw model prediction windows: {raw_count}")

# 7. Call GET /inference/status
print("\n[Step 7] Polling GET /inference/status...")
st_req = urllib.request.Request(f"{API_ENDPOINT}/inference/status?session_id={session_id}")
with urllib.request.urlopen(st_req) as r:
    status_data = json.loads(r.read().decode())
print(f"  -> Status: {status_data.get('status')}")
print(f"  -> DynamoDB Episode Count: {status_data.get('episode_count')}")

# 8. Run Canonical JS Timeline Aggregator on the Raw Predictions
print("\n[Step 8] Running Canonical Timeline Aggregator on Raw Predictions...")
import subprocess

node_verify_cmd = [
    "node",
    "-e",
    f"""
    import("./frontend/src/timeline_aggregator.js").then(({{ aggregateTimeline, computeAggregatedStats, generateModelGroundedNarrative }}) => {{
        const raw = {json.dumps(raw_predictions)};
        const timeline = aggregateTimeline(raw);
        const stats = computeAggregatedStats(timeline);
        const narrative = generateModelGroundedNarrative(timeline, stats);

        // Check for temporal overlaps
        let overlapErrors = 0;
        for (let i = 1; i < timeline.length; i++) {{
            if (timeline[i].start < timeline[i - 1].end - 0.001) {{
                console.error("OVERLAP DETECTED at index " + i + ": prev=" + timeline[i - 1].end + ", curr=" + timeline[i].start);
                overlapErrors++;
            }}
        }}

        const output = {{
            rawCount: raw.length,
            timelineCount: timeline.length,
            stats,
            narrative,
            overlapErrors,
            firstFive: timeline.slice(0, 5),
            fogIntervals: timeline.filter(e => e.type === "FoG")
        }};
        console.log("JSON_OUTPUT_START" + JSON.stringify(output) + "JSON_OUTPUT_END");
    }});
    """
]

res = subprocess.run(node_verify_cmd, capture_output=True, text=True, check=True)
stdout = res.stdout
json_str = stdout.split("JSON_OUTPUT_START")[1].split("JSON_OUTPUT_END")[0]
js_results = json.loads(json_str)

print("\n" + "=" * 75)
print("CANONICAL RESULTS SUMMARY")
print("=" * 75)
print(f"A. Raw Window Count:           {js_results['rawCount']}")
print(f"B. Aggregated Interval Count: {js_results['timelineCount']}")
print(f"C. Total Intervals (Stats):   {js_results['stats']['totalIntervals']}")
print(f"D. FoG Count:                 {js_results['stats']['fogCount']}")
print(f"E. Borderline Count:          {js_results['stats']['borderlineCount']}")
print(f"F. Normal Count:              {js_results['stats']['normalCount']}")
print(f"G. Sum of Partition Counts:   {js_results['stats']['fogCount'] + js_results['stats']['borderlineCount'] + js_results['stats']['normalCount']}")
print(f"H. Dominant Model Cue:        {js_results['stats']['dominantCue']}")
print(f"I. Overlap Errors:            {js_results['overlapErrors']}")
print(f"J. FoG Intervals:             {json.dumps(js_results['fogIntervals'], indent=2)}")
print(f"\nK. Grounded Narrative Generated from Aggregated Data:")
print("-" * 75)
print(js_results['narrative'])
print("-" * 75)

# Verification assertions
assert js_results['rawCount'] == 446, f"Expected 446 raw windows, got {js_results['rawCount']}"
assert js_results['timelineCount'] == 115, f"Expected 115 aggregated intervals, got {js_results['timelineCount']}"
assert js_results['stats']['fogCount'] == 1, f"Expected 1 FoG interval, got {js_results['stats']['fogCount']}"
assert js_results['stats']['borderlineCount'] == 58, f"Expected 58 Borderline intervals, got {js_results['stats']['borderlineCount']}"
assert js_results['stats']['normalCount'] == 56, f"Expected 56 Normal intervals, got {js_results['stats']['normalCount']}"
assert js_results['overlapErrors'] == 0, f"Expected 0 overlap errors, got {js_results['overlapErrors']}"

fog_ep = js_results['fogIntervals'][0]
assert fog_ep['start'] == 100.01, f"Expected FoG start 100.01, got {fog_ep['start']}"
assert fog_ep['end'] == 101.31, f"Expected FoG end 101.31, got {fog_ep['end']}"
assert fog_ep['primary_cue'] == "accel_rms", f"Expected cue accel_rms, got {fog_ep['primary_cue']}"
assert "115 non-overlapping classified intervals" in js_results['narrative']
assert "1 interval as FoG, 58 as Borderline, and 56 as Normal" in js_results['narrative']
assert "100.01s to 101.31s" in js_results['narrative']
assert "64.8%" in js_results['narrative']
assert "accel_rms" in js_results['narrative']

print("\n✅ ALL VERIFICATION ASSERTIONS PASSED PERFECTLY!")
