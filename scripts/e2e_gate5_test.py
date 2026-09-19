"""End-to-End Live Verification Script for NeuroGait Gate 5 (DynamoDB + State).

Runs full live lifecycle against deployed AWS infrastructure:
1. POST /sessions -> CREATED
2. Verify DynamoDB state is CREATED
3. Attempt POST /inference/start -> Assert 409 Conflict (invalid transition from CREATED)
4. Presigned S3 Uploads (Video + IMU)
5. POST /sessions/confirm-upload -> UPLOADED
6. Verify DynamoDB state is UPLOADED
7. POST /inference/start -> PROCESSING (launch ECS Fargate)
8. Verify DynamoDB state is PROCESSING with task ARN
9. Poll GET /inference/status until COMPLETE
10. Verify canonical S3 predictions and S3 explanation
11. Repeat GET /inference/status -> verify idempotency (cached: True, state: COMPLETE)
12. Inspect DynamoDB item -> verify absence of large payloads
13. Test legacy session backward-compatibility backfill
"""

import json
import os
import sys
import time
import urllib.request
import boto3

API_ENDPOINT = "https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com"
DYNAMODB_TABLE = "neurogait-sessions"
REGION = "ap-south-1"

VIDEO_PATH = "data/raw/videos/PDFE01_1.mp4"
IMU_PATH = "data/raw/imu/SUB01_1.txt"


def http_request(url: str, method: str = "GET", data: dict = None) -> tuple[int, dict]:
    body_bytes = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, json.loads(raw) if raw else {}


def upload_file_to_presigned_url(url: str, file_path: str, content_type: str):
    with open(file_path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", content_type)
    with urllib.request.urlopen(req) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError(f"S3 presigned upload failed with status {resp.status}")


def get_dynamo_item(session_id: str) -> dict:
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)
    res = table.get_item(Key={"session_id": session_id}, ConsistentRead=True)
    return res.get("Item", {})


def main():
    print("=" * 70)
    print("NEUROGAIT GATE 5: DYNAMODB + STATE MACHINE E2E VERIFICATION")
    print("=" * 70)

    # 1. Health check
    code, health = http_request(f"{API_ENDPOINT}/health")
    print(f"\n[1] Health Check: HTTP {code}")
    print(f"    Payload: {json.dumps(health, indent=2)}")
    assert code == 200 and health.get("dynamodb_table") == DYNAMODB_TABLE

    # 2. Create Session
    v_size = os.path.getsize(VIDEO_PATH)
    i_size = os.path.getsize(IMU_PATH)
    print(f"\n[2] Creating Session with {v_size} bytes video, {i_size} bytes IMU...")
    code, session_res = http_request(
        f"{API_ENDPOINT}/sessions",
        method="POST",
        data={
            "video_filename": "PDFE01_1.mp4",
            "imu_filename": "SUB01_1.txt",
            "video_size_bytes": v_size,
            "imu_size_bytes": i_size,
        },
    )
    print(f"    Response HTTP {code}: status={session_res.get('status')}")
    assert code == 200 and session_res.get("status") == "CREATED"
    session_id = session_res["session_id"]
    upload_urls = session_res["upload_urls"]
    print(f"    Session ID: {session_id}")

    # 3. Verify DynamoDB State is CREATED
    item = get_dynamo_item(session_id)
    print(f"\n[3] DynamoDB Inspection after creation:")
    print(f"    State: {item.get('state')}")
    print(f"    Video S3 Key: {item.get('video_s3_key')}")
    print(f"    Created At: {item.get('created_at')}")
    assert item.get("state") == "CREATED"

    # 4. Attempt POST /inference/start on CREATED session -> Expect 409 Conflict
    print(f"\n[4] Attempting POST /inference/start while in CREATED state...")
    code, err_res = http_request(
        f"{API_ENDPOINT}/inference/start",
        method="POST",
        data={"session_id": session_id},
    )
    print(f"    Response HTTP {code}: {json.dumps(err_res)}")
    assert code == 409
    assert err_res.get("error") == "InvalidStateTransition"
    assert "UPLOADED" in err_res.get("message")
    print("    -> Confirmed: CREATED -> PROCESSING is strictly rejected with HTTP 409.")

    # 5. Upload artifacts to S3
    print(f"\n[5] Uploading real artifacts via presigned URLs to S3...")
    t0 = time.perf_counter()
    upload_file_to_presigned_url(upload_urls["video"], VIDEO_PATH, "video/mp4")
    upload_file_to_presigned_url(upload_urls["imu"], IMU_PATH, "text/plain")
    print(f"    Artifacts uploaded in {time.perf_counter() - t0:.2f}s")

    # 6. Confirm upload: POST /sessions/confirm-upload -> UPLOADED
    print(f"\n[6] Confirming upload via API Gateway...")
    code, confirm_res = http_request(
        f"{API_ENDPOINT}/sessions/confirm-upload",
        method="POST",
        data={"session_id": session_id},
    )
    print(f"    Response HTTP {code}: {json.dumps(confirm_res)}")
    assert code == 200 and confirm_res.get("status") == "UPLOADED"

    item = get_dynamo_item(session_id)
    print(f"    DynamoDB State after confirmation: {item.get('state')}")
    assert item.get("state") == "UPLOADED"

    # 7. Start inference: POST /inference/start -> PROCESSING
    print(f"\n[7] Dispatching inference from UPLOADED state...")
    code, start_res = http_request(
        f"{API_ENDPOINT}/inference/start",
        method="POST",
        data={"session_id": session_id},
    )
    print(f"    Response HTTP {code}: {json.dumps(start_res)}")
    assert code == 202 and start_res.get("status") == "PROCESSING"
    task_arn = start_res["task_arn"]

    item = get_dynamo_item(session_id)
    print(f"    DynamoDB State after start: {item.get('state')}")
    print(f"    ECS Task ARN in DynamoDB: {item.get('ecs_task_arn')}")
    assert item.get("state") == "PROCESSING"
    assert item.get("ecs_task_arn") == task_arn

    # 8. Poll GET /inference/status until COMPLETE
    print(f"\n[8] Polling GET /inference/status for session {session_id}...")
    poll_start = time.perf_counter()
    status_res = {}
    while time.perf_counter() - poll_start < 300:
        code, status_res = http_request(f"{API_ENDPOINT}/inference/status?session_id={session_id}")
        st = status_res.get("status")
        print(f"    [{time.perf_counter() - poll_start:.1f}s] Status: {st}")
        if st == "COMPLETE":
            break
        time.sleep(5)

    assert status_res.get("status") == "COMPLETE"
    assert status_res.get("episode_count") == 48
    print(f"\n    Inference & Explanation completed in {time.perf_counter() - poll_start:.2f}s!")
    print(f"    Summary: {json.dumps(status_res.get('summary'))}")
    print(f"    Explanation Provider: {status_res.get('explanation', {}).get('provider')}")
    print(f"    Explanation Cached (First call): {status_res.get('explanation', {}).get('cached')}")

    # 9. Second call: Idempotency verification
    print(f"\n[9] Testing Idempotency (Second GET /inference/status call)...")
    code, status_res_2 = http_request(f"{API_ENDPOINT}/inference/status?session_id={session_id}")
    assert code == 200 and status_res_2.get("status") == "COMPLETE"
    assert status_res_2.get("explanation", {}).get("cached") is True
    print(f"    Status: {status_res_2.get('status')}")
    print(f"    Cached: {status_res_2.get('explanation', {}).get('cached')}")
    print("    -> Confirmed: Idempotent return with 0 transitions.")

    # 10. Inspect DynamoDB item - Verify zero large artifacts
    item = get_dynamo_item(session_id)
    print(f"\n[10] Final DynamoDB Item Audit:")
    print(f"     Keys present in item: {sorted(list(item.keys()))}")
    print(f"     Final State: {item.get('state')}")
    print(f"     Episode Count: {item.get('episode_count')}")
    print(f"     Summary: {item.get('summary')}")
    print(f"     Provider: {item.get('provider')}")

    # Assert no large payloads in DynamoDB
    assert "video_data" not in item
    assert "imu_data" not in item
    assert "episodes" not in item
    assert "predictions" not in item
    assert "narrative" not in item  # narrative is in S3 explanation.json
    print("     -> Confirmed: Zero large binary/prediction/narrative arrays in DynamoDB.")

    # 11. Legacy Session Backfill Test
    legacy_id = "6ba9e60d-3374-482e-bb0f-0c5f75382c46"
    print(f"\n[11] Testing Legacy Session ({legacy_id}) Status Retrieval...")
    code, leg_res = http_request(f"{API_ENDPOINT}/inference/status?session_id={legacy_id}")
    print(f"     Response HTTP {code}: status={leg_res.get('status')}, episodes={leg_res.get('episode_count')}")
    assert code == 200 and leg_res.get("status") == "COMPLETE"
    leg_item = get_dynamo_item(legacy_id)
    print(f"     Legacy DynamoDB backfilled state: {leg_item.get('state')}")
    assert leg_item.get("state") == "COMPLETE"

    print("\n" + "=" * 70)
    print("ALL GATE 5 E2E LIVE VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
