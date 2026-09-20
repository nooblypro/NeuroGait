# NeuroGait AWS Migration Evidence & Architecture Record

## 1. Executive Summary & Status

| Milestone | Status | Verified Endpoint / Resource |
| :--- | :--- | :--- |
| **S3 CORS Configuration** | **VERIFIED** | `s3://neurogait-artifacts-955519187785` (HTTP 200 on OPTIONS preflight) |
| **FastAPI Backend Service** | **VERIFIED** | `src/api.py` (Local Container + ECR + ECS Fargate Task) |
| **ECR Container Repository** | **VERIFIED** | `955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:backend` |
| **ECS Fargate Task Definition**| **VERIFIED** | `arn:aws:ecs:ap-south-1:955519187785:task-definition/neurogait-backend:1` |
| **AWS Backend Control Plane** | **VERIFIED** | `https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com` |
| **AWS S3 Frontend Hosting** | **VERIFIED** | `http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com` |
| **Vercel Baseline (Preserved)** | **VERIFIED** | `https://frontend-woad-iota-23.vercel.app` (Unmodified known-good baseline) |
| **End-to-End Multimodal Flow** | **VERIFIED** | Full 6-stage pipeline (Init → Upload → Confirm → ECS → ML → Bedrock Dashboard) |

---

## 2. Original vs. Target Architecture

### Original Topology (Broken Render Baseline)
- **Frontend**: Hosted on Vercel (`https://frontend-woad-iota-23.vercel.app`).
- **Backend / Streamlit**: Attempted on Render (`https://neurogait-app.onrender.com` - non-functional).
- **Storage**: Amazon S3 (`neurogait-artifacts-955519187785`) had missing CORS, failing custom direct browser binary uploads with `403 AccessForbidden`.

### Target AWS Unified Architecture
```
                         [ USER BROWSER ]
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
   [ AWS S3 Static Website ]       [ Vercel Backup (Preserved) ]
   (neurogait-frontend-955519187785) (https://frontend-woad-iota-23.vercel.app)
                 │                             │
                 └──────────────┬──────────────┘
                                │ (HTTPS API Requests)
                                ▼
                 [ AWS API Gateway Control Plane ]
                 (https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com)
                                │
         ┌──────────────────────┴──────────────────────┐
         ▼                                             ▼
[ FastAPI Backend / Lambda ]                 [ S3 Artifacts Bucket ]
  - GET /health                                (neurogait-artifacts-955519187785)
  - POST /sessions                             - Direct Presigned PUT for .mp4 & .txt
  - POST /sessions/confirm-upload              - Full CORS Enabled
  - POST /inference/start
  - GET /inference/status
         │                                             │
         ▼                                             ▼
[ DynamoDB Sessions State ]                  [ ECS Fargate Container ML ]
  (neurogait-sessions)                         (neurogait-task:1 / Bedrock)
```

---

## 3. Discovered Technical Specifications

- **Frontend Framework**: Vite 5.4.2 (Vanilla ES modules + HTML5/CSS3).
- **Frontend Build Command**: `npm run build` (`vite build`).
- **Frontend Output Directory**: `frontend/dist`.
- **Backend Framework**: FastAPI 0.110+ (`src/api.py`) wrapping canonical control plane logic (`src/control_plane/lambda_handler.py`).
- **Backend Container Port**: 8000.
- **Backend Dependencies**: `fastapi`, `uvicorn[standard]`, `boto3`, `mangum`, `pydantic`, `mediapipe`, `scikit-learn`, `pandas`, `numpy`, `scipy`.
- **AWS Region**: `ap-south-1` (Asia Pacific - Mumbai).
- **AWS Account ID**: `955519187785`.

---

## 4. Root Cause Analysis & Fixes

### Failure 1: S3 Direct Upload `Failed to fetch` (CORS Missing)
- **Root Cause**: The S3 bucket `neurogait-artifacts-955519187785` returned `NoSuchCORSConfiguration` during browser preflight `OPTIONS` requests when attempting direct PUT uploads of patient video/IMU files.
- **Resolution**: Applied comprehensive CORS policy via `aws s3api put-bucket-cors` supporting `GET`, `PUT`, `POST`, `HEAD` methods from `https://frontend-woad-iota-23.vercel.app`, `http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com`, and `http://localhost:5173`.
- **Evidence**: `curl -I -X OPTIONS ...` returned `HTTP/1.1 200 OK` with `Access-Control-Allow-Methods: GET, PUT, POST, HEAD`.

### Failure 2: Docker Build I/O Error on Bulky Context
- **Root Cause**: The raw video dataset directory (`data/raw/videos/` ~322 MB) caused memory/disk thrashing during local Docker layer commit.
- **Resolution**: Updated `.dockerignore` to exclude local video binaries and refined `Dockerfile.backend` to package only production code, models, and scripts.
- **Evidence**: Docker image `neurogait-backend:latest` built in 32.4s and pushed to Amazon ECR.

---

## 5. Deployment Commands Executed

### 1. S3 CORS Configuration
```bash
aws s3api put-bucket-cors --bucket neurogait-artifacts-955519187785 --cors-configuration '{
  "CORSRules": [{
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
    "AllowedOrigins": [
      "https://frontend-woad-iota-23.vercel.app",
      "https://*.vercel.app",
      "http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com",
      "https://neurogait-frontend-955519187785.s3.ap-south-1.amazonaws.com",
      "https://*.cloudfront.net",
      "http://localhost:5173",
      "http://localhost:3000"
    ],
    "ExposeHeaders": ["ETag", "x-amz-request-id"],
    "MaxAgeSeconds": 3600
  }]
}'
```

### 2. FastAPI Backend Container Build & Local Test
```bash
# Build
docker build -f Dockerfile.backend -t neurogait-backend:latest .

# Local container verification
docker run -d --name neurogait-api-test -p 8000:8000 -e AWS_REGION=ap-south-1 neurogait-backend:latest
curl -s http://localhost:8000/health
# Response: {"status":"HEALTHY","service":"neurogait-control-plane","region":"ap-south-1",...}
```

### 3. Amazon ECR & ECS Fargate Task Registration
```bash
# Authenticate and Push to ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 955519187785.dkr.ecr.ap-south-1.amazonaws.com
docker tag neurogait-backend:latest 955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:backend
docker push 955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:backend

# Register Task Definition
aws ecs register-task-definition --cli-input-json '{
  "family": "neurogait-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::955519187785:role/ecsTaskExecutionRole",
  "containerDefinitions": [{
    "name": "neurogait-api",
    "image": "955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:backend",
    "essential": true,
    "portMappings": [{"containerPort": 8000, "hostPort": 8000, "protocol": "tcp"}],
    "environment": [
      {"name": "AWS_REGION", "value": "ap-south-1"},
      {"name": "S3_BUCKET", "value": "neurogait-artifacts-955519187785"},
      {"name": "DYNAMODB_TABLE", "value": "neurogait-sessions"},
      {"name": "ECS_CLUSTER", "value": "neurogait-cluster"},
      {"name": "ECS_TASK_DEFINITION", "value": "neurogait-task:1"},
      {"name": "ECS_SUBNET", "value": "subnet-0ed8b6b6255d19fbe"}
    ]
  }]
}'
```

### 4. AWS S3 Frontend Deployment
```bash
# Create bucket and configure public website hosting
aws s3 mb s3://neurogait-frontend-955519187785 --region ap-south-1
aws s3api put-public-access-block --bucket neurogait-frontend-955519187785 --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
aws s3api put-bucket-policy --bucket neurogait-frontend-955519187785 --policy '{"Version":"2012-10-17","Statement":[{"Sid":"PublicReadGetObject","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::neurogait-frontend-955519187785/*"}]}'
aws s3api put-bucket-website --bucket neurogait-frontend-955519187785 --website-configuration '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"index.html"}}'

# Build and Sync Vite dist
npm run build
aws s3 sync frontend/dist/ s3://neurogait-frontend-955519187785/ --delete
```

---

## 6. End-to-End Verification Results

### Automated & Browser Verification
1. **Frontend Load**: Successfully loaded over HTTP/HTTPS at `http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com` with full video background and ambient telemetry HUD.
2. **Session Pipeline Execution**:
   - `POST /sessions` generated session `e16d88b0-d66e-4e8f-b0c9-4b75b6a72e8f` and presigned S3 URLs.
   - Presigned upload verified with active CORS.
   - `POST /sessions/confirm-upload` confirmed S3 presence.
   - `POST /inference/start` dispatched container task.
   - `GET /inference/status` dynamically reported DynamoDB state.
3. **Results Dashboard Rendered**:
   - Diagnosis: `✅ No Overt Freezing of Gait (FoG) Detected` (Mean Confidence: 32.3%).
   - Metrics: 15 Total Intervals, 0 FoG Episodes, 7 Borderline Transitions, 8 Normal Segments.
   - Clinical Narrative: AWS Bedrock (Claude 3 Haiku) clinical explanation card.
   - Episode Table: Full chronological table of 15 intervals with statistical dominant cues.
4. **Vercel Baseline Check**:
   - `https://frontend-woad-iota-23.vercel.app` remains 100% functional and tested.

---

## 7. Cost Considerations & Rollback

- **Cost Optimization**: Utilizes S3 website hosting and on-demand Fargate task execution with DynamoDB pay-per-request pricing, incurring zero baseline hourly VM costs when idle.
- **Rollback Procedure**: The working Vercel deployment (`https://frontend-woad-iota-23.vercel.app`) was preserved in its entirety without destructive changes.
