# NeuroGait Pre-Manual QA Deployment & Verification Report

**Execution Date**: 2026-09-20  
**Deployment Target**: AWS Production Infrastructure (ECS Fargate + S3 Website Hosting)  
**Investigator**: Antigravity Deployment & Verification Agent  

---

## Final Status Verdict

```
READY FOR MANUAL QA
```

---

## A. Current Git Commit

- **Commit SHA**: `7a0d8c21e471b4f6c2a0ee3bc239523c3092d900`
- **Short SHA**: `7a0d8c2`
- **Commit Message**: `fix(parity): canonicalize production Linux runtime, update tests and reference fixture`
- **Branch**: `main`
- **Remote**: `origin https://github.com/nooblypro/NeuroGait.git`
- **Verification**: Verified that this commit contains the canonicalized timeline presentation, pinned production runtime requirements, updated reference fixtures, and regression tests.

---

## B. Frontend Build & Deployment Result

- **Build Tool**: Vite v5.4.21
- **Build Command**: `npm --prefix frontend run build`
- **Exit Code**: 0 (Clean build in 254ms)
- **Generated Bundle Artifacts**:
  - `dist/index.html` (21.41 kB, gzip: 5.76 kB)
  - `dist/assets/index-CVyoCgtG.js` (22.08 kB, gzip: 7.13 kB)
  - `dist/assets/index-DmUSwqk2.css` (25.44 kB, gzip: 5.30 kB)
- **Deployment Command**: `aws s3 sync frontend/dist/ s3://neurogait-frontend-955519187785/ --delete`
- **S3 Sync Status**: Completed successfully. All modified and new bundle assets synced to S3 bucket `neurogait-frontend-955519187785`.

---

## C. Live Frontend URL

- **URL**: [http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com/](http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com/)
- **Hosting Type**: Amazon S3 Static Website Hosting (Region: `ap-south-1`)

---

## D. Backend Task Definition

- **Family**: `neurogait-task`
- **Revision**: `2`
- **Full ARN**: `arn:aws:ecs:ap-south-1:955519187785:task-definition/neurogait-task:2`
- **Status**: `ACTIVE`
- **Compute Architecture**: AWS Fargate (ARM64 / Linux, 1024 CPU, 2048 Memory)
- **Control Plane Lambda Binding**: `neurogait-control-plane` environment variable `ECS_TASK_DEFINITION=neurogait-task:2`

---

## E. ECR Image Tag

- **Repository**: `955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml`
- **Tag**: `parity-v1`

---

## F. ECR Image Digest

- **Image Digest**: `sha256:9ef0154fbd342c85d29a9e09f9ca7b6375dd6eeeb0046d2409c9ee1e768993f9`
- **Push Timestamp**: `2026-09-20T21:35:43.705000+05:30`

---

## G. Production Model Hash Verification

- **Model Path**: `models/fog_model.pkl`
- **Expected SHA-256**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **Local SHA-256**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **In-Container SHA-256**: `02a87b0a226fb51aa4a9b8363cf6126451bab1e597810dc5c1d08bfdee8b3ecf`
- **Pose Model SHA-256**: `4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad`
- **Integrity Status**: **100% UNMODIFIED & FROZEN**

---

## H. Frontend → Backend Connectivity

- **API Gateway Base URL**: `https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com`
- **Health Check (`GET /health`)**:
  - **Status Code**: `HTTP/2 200`
  - **CORS Headers**: `access-control-allow-origin: *`
  - **Response Payload**:
    ```json
    {
      "status": "HEALTHY",
      "service": "neurogait-control-plane",
      "region": "ap-south-1",
      "ecs_cluster": "neurogait-cluster",
      "s3_bucket": "neurogait-artifacts-955519187785",
      "dynamodb_table": "neurogait-sessions",
      "task_definition": "neurogait-task:2"
    }
    ```
- **Live JS Bundle Verification**: The deployed JavaScript bundle (`/assets/index-CVyoCgtG.js`) embeds `https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com` as its backend target.

---

## I. Browser Smoke-Test Result

Directly inspected via browser automation subagent on the live production URL:
- **Title**: `NeuroGait — Multimodal Movement Assessment`
- **Background Video**: `#bg-video` loaded and ready (`readyState = 4`).
- **Assets Loaded**:
  - Script: `/assets/index-CVyoCgtG.js` (Verified active)
  - CSS: `/assets/index-DmUSwqk2.css` (Verified active)
- **Beat 6 Assessment UI**:
  - Mode selectors, preset buttons (`⭐ Run Verified Demo Sample`, `📤 Upload Custom Patient Video & IMU Files`) active and interactive.
  - Radio options for AWS Cloud Pipeline vs Local Offline Engine present.
  - Action button: `🚀 RUN MULTIMODAL ASSESSMENT` enabled and clickable.
  - Stepper: All 7 pipeline progression steps verified.
- **Console Errors**: **0 console errors / uncaught exceptions**.

---

## J. Cache Verification

- **CloudFront CDN**: None configured (`aws cloudfront list-distributions` returned `null`).
- **S3 Origin**: Direct S3 website endpoint serves the uploaded `index.html` immediately.
- **HTTP Verification**: `curl -s http://neurogait-frontend-955519187785.s3-website.ap-south-1.amazonaws.com/` confirms the latest asset hashes (`index-CVyoCgtG.js` and `index-DmUSwqk2.css`) are served directly.
- **Stale Cache Issue**: **NONE**. Stale bundle risk is zero.

---

## K. Exact Files & Commits Deployed

- **Commit Deployed**: `7a0d8c2`
- **Frontend Files Compiled & Deployed**:
  - `frontend/src/main.js`
  - `frontend/src/timeline_aggregator.js`
  - `frontend/src/style.css`
  - `frontend/index.html`
- **Backend Image & Task Deployed**:
  - Image: `955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:parity-v1`
  - Digest: `sha256:9ef0154fbd342c85d29a9e09f9ca7b6375dd6eeeb0046d2409c9ee1e768993f9`
  - Task Definition: `neurogait-task:2`

---

## Summary Verdict

The live website, backend API, and ECS task are verified to be running the latest repository state. The system is:

```
READY FOR MANUAL QA
```
