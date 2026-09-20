"""FINAL REAL EXECUTION VERIFICATION OF NEUROGAIT AWS PIPELINE.

Executes a real end-to-end pipeline run with real inputs:
- /Users/shriram/Documents/GAIT videos/PDFE14_1.mp4
- data/raw/imu/SUB14_1.txt
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
import boto3

API_ENDPOINT = "https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com"
VIDEO_PATH = Path("/Users/shriram/Documents/GAIT videos/PDFE14_1.mp4")
IMU_PATH = Path("data/raw/imu/SUB14_1.txt")
REGION = "ap-south-1"
BUCKET = "neurogait-artifacts-955519187785"
TABLE = "neurogait-sessions"
CLUSTER = "neurogait-cluster"

print("=" * 70)
print("FINAL REAL EXECUTION VERIFICATION: NEUROGAIT AWS PIPELINE")
print("=" * 70)

# Check files
assert VIDEO_PATH.exists(), f"Video file not found: {VIDEO_PATH}"
assert IMU_PATH.exists(), f"IMU file not found: {IMU_PATH}"
v_size = VIDEO_PATH.stat().st_size
i_size = IMU_PATH.stat().st_size
print(f"Inputs verified:")
print(f"  - Video: {VIDEO_PATH} ({v_size:,} bytes)")
print(f"  - IMU:   {IMU_PATH} ({i_size:,} bytes)")

# -------------------------------------------------------------
# 1. POST /sessions
# -------------------------------------------------------------
print("\n[Step 1] Initializing session via POST /sessions...")
payload = json.dumps({
    "video_filename": "PDFE14_1.mp4",
    "imu_filename": "SUB14_1.txt",
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
    status_code = resp.status
    resp_data = json.loads(resp.read().decode())

session_id = resp_data["session_id"]
v_upload_url = resp_data["upload_urls"]["video"]
i_upload_url = resp_data["upload_urls"]["imu"]
v_s3_key = resp_data["s3_keys"]["video"]
i_s3_key = resp_data["s3_keys"]["imu"]
print(f"  -> HTTP Status: {status_code}")
print(f"  -> Session ID:  {session_id}")
print(f"  -> Video Key:   {v_s3_key}")
print(f"  -> IMU Key:     {i_s3_key}")

# -------------------------------------------------------------
# 2. Perform Real S3 PUT Uploads
# -------------------------------------------------------------
print("\n[Step 2] Executing real presigned S3 PUT uploads...")
# Upload Video
print(f"  -> Uploading video ({v_size:,} bytes) to S3...")
t_v0 = time.time()
with open(VIDEO_PATH, "rb") as f:
    video_bytes = f.read()

v_req = urllib.request.Request(v_upload_url, data=video_bytes, method="PUT")
v_req.add_header("Content-Type", "video/mp4")
with urllib.request.urlopen(v_req) as v_resp:
    v_put_status = v_resp.status
print(f"  -> Video upload completed in {time.time() - t_v0:.2f}s with HTTP {v_put_status}")

# Upload IMU
print(f"  -> Uploading IMU ({i_size:,} bytes) to S3...")
t_i0 = time.time()
with open(IMU_PATH, "rb") as f:
    imu_bytes = f.read()

i_req = urllib.request.Request(i_upload_url, data=imu_bytes, method="PUT")
i_req.add_header("Content-Type", "text/plain")
with urllib.request.urlopen(i_req) as i_resp:
    i_put_status = i_resp.status
print(f"  -> IMU upload completed in {time.time() - t_i0:.2f}s with HTTP {i_put_status}")

# Verify with S3 head_object
s3_client = boto3.client("s3", region_name=REGION)
v_head = s3_client.head_object(Bucket=BUCKET, Key=v_s3_key)
i_head = s3_client.head_object(Bucket=BUCKET, Key=i_s3_key)
print(f"  -> S3 Object Verified: s3://{BUCKET}/{v_s3_key} (Size: {v_head['ContentLength']:,} bytes, ETag: {v_head['ETag']})")
print(f"  -> S3 Object Verified: s3://{BUCKET}/{i_s3_key} (Size: {i_head['ContentLength']:,} bytes, ETag: {i_head['ETag']})")

# -------------------------------------------------------------
# 3. POST /sessions/confirm-upload
# -------------------------------------------------------------
print("\n[Step 3] Calling POST /sessions/confirm-upload...")
confirm_payload = json.dumps({"session_id": session_id}).encode("utf-8")
c_req = urllib.request.Request(
    f"{API_ENDPOINT}/sessions/confirm-upload",
    data=confirm_payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(c_req) as c_resp:
    confirm_status = c_resp.status
    confirm_data = json.loads(c_resp.read().decode())

print(f"  -> Confirm HTTP Status: {confirm_status}")
print(f"  -> Confirm Response:    {confirm_data}")

# Verify DynamoDB State
dynamo = boto3.client("dynamodb", region_name=REGION)
dyn_res = dynamo.get_item(TableName=TABLE, Key={"session_id": {"S": session_id}})
state_after_confirm = dyn_res.get("Item", {}).get("state", {}).get("S")
print(f"  -> DynamoDB State after confirmation: {state_after_confirm}")
assert state_after_confirm == "UPLOADED", f"Expected UPLOADED, got {state_after_confirm}"

# -------------------------------------------------------------
# 4. POST /inference/start
# -------------------------------------------------------------
print("\n[Step 4] Calling POST /inference/start...")
start_payload = json.dumps({"session_id": session_id}).encode("utf-8")
s_req = urllib.request.Request(
    f"{API_ENDPOINT}/inference/start",
    data=start_payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(s_req) as s_resp:
        start_status = s_resp.status
        start_data = json.loads(s_resp.read().decode())
    print(f"  -> Start HTTP Status: {start_status}")
    print(f"  -> Start Response:    {start_data}")
    task_arn = start_data.get("task_arn")
except urllib.error.HTTPError as e:
    err_body = e.read().decode()
    print(f"  -> Start HTTPError {e.code}: {err_body}")
    sys.exit(1)

# -------------------------------------------------------------
# 5. Verify ECS Execution Directly via AWS Boto3
# -------------------------------------------------------------
print("\n[Step 5] Verifying ECS Fargate Task Execution...")
ecs = boto3.client("ecs", region_name=REGION)
task_desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])
tasks = task_desc.get("tasks", [])
assert len(tasks) > 0, "No task found in ECS"
task = tasks[0]
print(f"  -> ECS Task ARN:        {task_arn}")
print(f"  -> Task Definition:     {task.get('taskDefinitionArn')}")
print(f"  -> Initial LastStatus:  {task.get('lastStatus')}")
print(f"  -> Initial Desired:     {task.get('desiredStatus')}")
print(f"  -> Created At:          {task.get('createdAt')}")

# Poll task until completion
print("\n[Step 6] Monitoring ECS Fargate task lifecycle...")
poll_count = 0
while True:
    time.sleep(5)
    poll_count += 1
    t_info = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
    last_status = t_info.get("lastStatus")
    print(f"  [{poll_count * 5}s] ECS Task Status: {last_status}")
    if last_status == "STOPPED":
        stop_code = t_info.get("stopCode")
        stopped_reason = t_info.get("stoppedReason")
        containers = t_info.get("containers", [])
        exit_code = containers[0].get("exitCode") if containers else None
        print(f"  -> Task STOPPED!")
        print(f"  -> Stop Code:       {stop_code}")
        print(f"  -> Stopped Reason:  {stopped_reason}")
        print(f"  -> Container Exit:  {exit_code}")
        break
    if poll_count > 60:
        print("  -> Timeout waiting for ECS task")
        break

# -------------------------------------------------------------
# 6. Check S3 predictions.json
# -------------------------------------------------------------
print("\n[Step 7] Checking S3 predictions output...")
pred_key = f"outputs/{session_id}/predictions.json"
try:
    p_head = s3_client.head_object(Bucket=BUCKET, Key=pred_key)
    print(f"  -> S3 predictions.json FOUND!")
    print(f"  -> Path:   s3://{BUCKET}/{pred_key}")
    print(f"  -> Size:   {p_head['ContentLength']:,} bytes")
    print(f"  -> ETag:   {p_head['ETag']}")
    p_obj = s3_client.get_object(Bucket=BUCKET, Key=pred_key)
    p_content = json.loads(p_obj["Body"].read().decode("utf-8"))
    print(f"  -> Episodes Count in predictions.json: {len(p_content)}")
    print(f"  -> First Episode: {p_content[0] if p_content else None}")
except Exception as e:
    print(f"  -> S3 predictions.json error: {e}")

# -------------------------------------------------------------
# 7. Poll GET /inference/status to trigger Bedrock & complete state
# -------------------------------------------------------------
print("\n[Step 8] Calling GET /inference/status to check DynamoDB and Bedrock...")
st_req = urllib.request.Request(f"{API_ENDPOINT}/inference/status?session_id={session_id}")
with urllib.request.urlopen(st_req) as st_resp:
    st_data = json.loads(st_resp.read().decode())

print(f"  -> Final Status Response: {json.dumps(st_data, indent=2)}")

# Check ECS Logs from CloudWatch
print("\n[Step 9] Fetching ECS CloudWatch Logs...")
logs_client = boto3.client("logs", region_name=REGION)
task_id = task_arn.split("/")[-1]
stream_name = f"ecs/neurogait-container/{task_id}"
try:
    log_events = logs_client.get_log_events(
        logGroupName="/ecs/neurogait-ml",
        logStreamName=stream_name,
        limit=50,
    )
    print(f"  -> CloudWatch Log Stream: {stream_name}")
    for event in log_events.get("events", []):
        print(f"     {event['message'].strip()}")
except Exception as e:
    print(f"  -> Log fetch warning: {e}")
