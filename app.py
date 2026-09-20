"""NeuroGait Streamlit Application Entrypoint.

Public Recorded Mode user interface for multimodal Freezing of Gait (FoG)
assessment in Parkinson's Disease.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
import streamlit as st

from src.ui.api_client import NeuroGaitAPIClient
from src.ui.animated_hero import render_animated_hero
from src.ui.components import (
    inject_custom_styles,
    render_borderline_section,
    render_explanation_section,
    render_fog_episodes_section,
    render_header,
    render_judge_cheat_sheet,
    render_mode_selector,
    render_multimodal_pipeline_flow,
    render_past_session_lookup,
    render_results_dashboard,
    render_session_assessment_banner,
    render_state_tracker,
    render_summary_metrics,
    render_technical_details_section,
    render_timeline_visualization,
)

# Page configuration
st.set_page_config(
    page_title="NeuroGait — Multimodal FoG Assessment",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize styles
inject_custom_styles()


def init_session_state():
    """Initialize persistent Streamlit session state."""
    if "api_client" not in st.session_state:
        st.session_state.api_client = NeuroGaitAPIClient()
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "backend_state" not in st.session_state:
        st.session_state.backend_state = None
    if "results" not in st.session_state:
        st.session_state.results = None
    if "error_info" not in st.session_state:
        st.session_state.error_info = None
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    # Browser refresh preservation: restore session if present in URL query params
    try:
        url_sid = st.query_params.get("session_id")
        if url_sid and st.session_state.session_id is None and not st.session_state.is_processing:
            status_res = st.session_state.api_client.get_status(url_sid)
            if status_res.get("success"):
                st.session_state.session_id = url_sid
                st.session_state.backend_state = status_res.get("status")
                st.session_state.results = status_res
    except Exception:
        pass


def reset_assessment():
    """Reset assessment state for a fresh analysis."""
    st.session_state.session_id = None
    st.session_state.backend_state = None
    st.session_state.results = None
    st.session_state.error_info = None
    st.session_state.is_processing = False
    try:
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
    except Exception:
        pass


def main():
    init_session_state()
    client: NeuroGaitAPIClient = st.session_state.api_client

    # Render Animated 5-Beat Scroll Intro Experience
    render_animated_hero()

    # Render Header & Mode Selector
    render_header()
    selected_mode = render_mode_selector()

    # Sidebar: Service connectivity & settings
    with st.sidebar:
        st.markdown("### ⚙️ System Status")
        health = client.check_health()
        if health.get("success"):
            st.success("🟢 Cloud Control Plane: **Connected**")
            data = health.get("data", {})
            st.caption(f"**Region:** `{data.get('region', 'ap-south-1')}`")
            st.caption(f"**Service:** `{data.get('service', 'neurogait-control-plane')}`")
        else:
            st.error("🔴 Cloud Control Plane: **Offline**")
            st.caption(health.get("message", "Check network connection or use Local Demo Mode."))

        st.markdown("---")
        st.markdown("### ℹ️ About NeuroGait")
        st.caption(
            "NeuroGait integrates synchronized MediaPipe 2D pose kinematics and 128Hz wearable IMU sensor streams "
            "to detect Freezing of Gait episodes and identify statistical feature deviations relative to baseline."
        )

        st.markdown("---")
        if st.button("🔄 Reset Assessment", use_container_width=True):
            reset_assessment()
            st.rerun()

    # Mode 2: Live Streaming Prototype (Pending hardware validation)
    if selected_mode == "live_demo":
        st.markdown("### 🎥 Live Mode — Hardware Validation Pending")
        st.caption(
            "Experimental real-time streaming pipeline demonstration replaying verified patient trial data (`PDFE01_1.mp4` + `SUB01_1.txt`). "
            "Physical camera and wearable IMU hardware integration is pending physical test bench setup."
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Camera Input", "REPLAY STREAM", delta="29.98 FPS (Observed)")
        with col2:
            st.metric("IMU Input", "REPLAY STREAM", delta="128.0 Hz (Observed)")
        with col3:
            st.metric("Hardware Status", "VALIDATION PENDING")
        with col4:
            st.metric("Sync Tolerance", "±0.1 sec")

        st.markdown("---")

        if "live_worker" not in st.session_state:
            st.session_state.live_worker = None

        worker = st.session_state.live_worker
        is_live_running = worker is not None and worker.is_running()

        c_start, c_stop = st.columns(2)
        with c_start:
            start_live = st.button("▶️ START STREAMING REPLAY", type="primary", use_container_width=True, disabled=is_live_running)
        with c_stop:
            stop_live = st.button("⏹️ STOP STREAMING", use_container_width=True, disabled=not is_live_running)

        if start_live and not is_live_running:
            reset_assessment()
            from src.live_pipeline import LiveReplayWorker
            new_worker = LiveReplayWorker()
            new_worker.start()
            st.session_state.live_worker = new_worker
            st.session_state.backend_state = "MONITORING"
            st.rerun()

        if is_live_running:
            st.info(f"⏳ Live Demo Stream actively replaying in background thread... (Frames processed: {worker.session.frames_processed}, IMU: {worker.session.imu_samples_received})")
            time.sleep(1)
            if worker.is_completed and worker.result:
                st.session_state.results = worker.result
                st.session_state.backend_state = "COMPLETE"
                st.session_state.live_worker = None
                st.rerun()
            elif worker.error:
                st.session_state.error_info = {"error": str(worker.error)}
                st.session_state.backend_state = "PROCESSING_FAILED"
                st.session_state.live_worker = None
                st.rerun()
            else:
                st.rerun()

        if stop_live and is_live_running:
            with st.spinner("Finalizing live demo episodes..."):
                res = worker.stop()
                st.session_state.results = res
                st.session_state.backend_state = "COMPLETE" if res else "PROCESSING_FAILED"
                st.session_state.live_worker = None
                st.rerun()

        # Render Results Dashboard if COMPLETE
        if st.session_state.results and st.session_state.backend_state == "COMPLETE":
            st.markdown("---")
            render_results_dashboard(st.session_state.results)

        return

    # Mode 1: Primary Recorded Analysis Mode
    # Evaluator Architecture Guide
    render_judge_cheat_sheet()

    # Look up past session expander
    def on_load_past_session(data: Dict[str, Any]):
        sid = data.get("session_id")
        st.session_state.session_id = sid
        st.session_state.backend_state = data.get("status")
        st.session_state.results = data
        st.session_state.error_info = None
        st.session_state.is_processing = False
        try:
            if sid:
                st.query_params["session_id"] = sid
        except Exception:
            pass
        st.success(f"Loaded completed session `{sid}`.")
        st.rerun()

    render_past_session_lookup(client, on_load_past_session)

    # Main Patient Trial Selection
    st.markdown("### 📁 Select Patient Gait Trial")
    st.caption("Evaluate the verified repository clinical sample trial, or upload custom synchronized video and IMU sensor files.")

    trial_source = st.radio(
        "Trial Data Source",
        options=["sample", "upload"],
        format_func=lambda x: (
            "⭐ Run Verified Demo Sample (PDFE01_1 Patient Trial)"
            if x == "sample"
            else "📤 Upload Custom Patient Video & IMU Files"
        ),
        horizontal=True,
        disabled=st.session_state.is_processing,
    )

    use_sample = trial_source == "sample"
    video_file = None
    imu_file = None

    if use_sample:
        st.success(
            "✅ **Verified Recorded Sample Selected**: Figshare Parkinson's disease turning-task trial "
            "(`PDFE01_1.mp4` — 120s video @ 29.98 FPS + `SUB01_1.txt` — 128 Hz tri-axial accelerometer & gyroscope).\n\n"
            "*(Notice: This is a verified recorded clinical dataset sample, not live patient monitoring.)*"
        )
        can_submit = not st.session_state.is_processing
    else:
        col1, col2 = st.columns(2)
        with col1:
            video_file = st.file_uploader(
                "1. Kinematic Video (.mp4)",
                type=["mp4"],
                help="High-frame-rate patient turning-task video (MP4 format, max 500 MB).",
                disabled=st.session_state.is_processing,
            )
            if video_file:
                v_size_mb = video_file.size / (1024 * 1024)
                st.success(f"📹 **{video_file.name}** ({v_size_mb:.2f} MB)")

        with col2:
            imu_file = st.file_uploader(
                "2. Inertial IMU Sensor (.txt, .csv)",
                type=["txt", "csv"],
                help="128 Hz accelerometer & gyroscope sensor stream (max 50 MB).",
                disabled=st.session_state.is_processing,
            )
            if imu_file:
                i_size_mb = imu_file.size / (1024 * 1024)
                st.success(f"📊 **{imu_file.name}** ({i_size_mb:.2f} MB)")

        can_submit = bool(video_file and imu_file and not st.session_state.is_processing)

    # Execution Environment Selection
    exec_target = st.radio(
        "Execution Environment",
        options=["cloud", "local_engine"],
        format_func=lambda t: (
            "☁️ AWS Cloud Pipeline (Production: API Gateway + Lambda + S3 + ECS Fargate + DynamoDB)"
            if t == "cloud"
            else "💻 Local Deterministic Engine (Offline Demo Mode / models/fog_model.pkl)"
        ),
        horizontal=True,
        disabled=st.session_state.is_processing,
    )
    if exec_target == "local_engine":
        st.info("💻 **LOCAL DEMO MODE (OFFLINE FALLBACK)**: Direct deterministic local inference using frozen model `models/fog_model.pkl`. Produces identical canonical JSON contract on-device without cloud connectivity.")
    else:
        st.info("☁️ **AWS CLOUD INFERENCE**: Production serverless pipeline uploading artifacts to S3, dispatching an ECS Fargate container task, and tracking execution state in DynamoDB.")

    submit_label = "🚀 Run Verified Demo Analysis" if use_sample else "🚀 Run Multimodal Assessment"
    submit_btn = st.button(
        submit_label,
        type="primary",
        disabled=not can_submit,
        use_container_width=True,
    )

    # Workflow Execution on Submit
    if submit_btn and (use_sample or (video_file and imu_file)):
        reset_assessment()
        st.session_state.is_processing = True

        progress_placeholder = st.empty()

        # Resolve input files & bytes
        if use_sample:
            real_v_path = "data/raw/videos/PDFE01_1.mp4"
            real_i_path = "data/raw/imu/SUB01_1.txt"
            v_name = "PDFE01_1.mp4"
            i_name = "SUB01_1.txt"
            with open(real_v_path, "rb") as f:
                v_bytes = f.read()
            with open(real_i_path, "rb") as f:
                i_bytes = f.read()
            v_size = len(v_bytes)
            i_size = len(i_bytes)
            local_v_file = real_v_path
            local_i_file = real_i_path
            temp_files_to_clean = []
        else:
            v_name = video_file.name
            i_name = imu_file.name
            v_bytes = video_file.getvalue()
            i_bytes = imu_file.getvalue()
            v_size = video_file.size
            i_size = imu_file.size
            import tempfile
            tf_v = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tf_v.write(v_bytes)
            tf_v.close()
            tf_i = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
            tf_i.write(i_bytes)
            tf_i.close()
            local_v_file = tf_v.name
            local_i_file = tf_i.name
            temp_files_to_clean = [tf_v.name, tf_i.name]

        # Branch A: Local Deterministic Engine (Offline / Demo Fallback)
        if exec_target == "local_engine":
            try:
                with progress_placeholder.container():
                    st.info("💻 Executing on-device deterministic pipeline using `models/fog_model.pkl`...")
                from src.pipeline import predict_fog
                from src.explanation.orchestrator import generate_explanation
                import uuid
                import numpy as np

                episodes_json = predict_fog(
                    video_path=local_v_file,
                    csv_path=local_i_file,
                    model_path="models/fog_model.pkl",
                    data_mode="real",
                )
                explanation_res = generate_explanation(episodes_json, preferred_provider="auto")
                local_sid = f"local-{uuid.uuid4().hex[:8]}"

                local_results = {
                    "success": True,
                    "status": "COMPLETE",
                    "session_id": local_sid,
                    "episode_count": len(episodes_json),
                    "summary": {
                        "total_duration": float(np.max([ep["end"] for ep in episodes_json])) if episodes_json else 0.0,
                        "fog_episodes": sum(1 for ep in episodes_json if ep["type"] == "FoG"),
                        "borderline_episodes": sum(1 for ep in episodes_json if ep["type"] == "Borderline"),
                        "normal_episodes": sum(1 for ep in episodes_json if ep["type"] == "Normal"),
                    },
                    "episodes": episodes_json,
                    "explanation": explanation_res.to_dict(),
                    "execution_target": "LOCAL_DETERMINISTIC_ENGINE",
                }

                st.session_state.session_id = local_sid
                try:
                    st.query_params["session_id"] = local_sid
                except Exception:
                    pass
                st.session_state.backend_state = "COMPLETE"
                st.session_state.results = local_results
                st.session_state.is_processing = False
                st.success("✅ Local Deterministic Gait Assessment Complete!")
                st.rerun()
            except Exception as e:
                st.session_state.is_processing = False
                st.session_state.backend_state = "PROCESSING_FAILED"
                st.session_state.error_info = {"error": str(e)}
                st.error(f"❌ Local inference failed: {e}")
                return
            finally:
                for tf in temp_files_to_clean:
                    try:
                        os.unlink(tf)
                    except OSError:
                        pass

        # Branch B: AWS Cloud Control Plane Pipeline
        # Step 1: Client validation & Session Creation
        with progress_placeholder.container():
            st.info("Initializing session on cloud control plane...")
            session_res = client.create_session(
                video_filename=v_name,
                imu_filename=i_name,
                video_size_bytes=v_size,
                imu_size_bytes=i_size,
            )

        if not session_res.get("success"):
            st.session_state.is_processing = False
            st.session_state.error_info = session_res
            st.error(f"❌ Session creation failed: {session_res.get('message')}")
            return

        session_id = session_res["session_id"]
        upload_urls = session_res["upload_urls"]
        st.session_state.session_id = session_id
        try:
            st.query_params["session_id"] = session_id
        except Exception:
            pass
        st.session_state.backend_state = "CREATED"

        # Step 2: Upload Artifacts to S3 via Presigned URLs
        with progress_placeholder.container():
            st.info("Uploading video and sensor artifacts securely to S3...")
            st.session_state.backend_state = "UPLOADING"

            v_upload = client.upload_artifact(upload_urls["video"], v_bytes, "video/mp4")
            if not v_upload.get("success"):
                st.session_state.is_processing = False
                st.session_state.backend_state = "UPLOAD_FAILED"
                st.session_state.error_info = v_upload
                st.error(f"❌ Video upload failed: {v_upload.get('message')}")
                return

            i_upload = client.upload_artifact(upload_urls["imu"], i_bytes, "text/plain")
            if not i_upload.get("success"):
                st.session_state.is_processing = False
                st.session_state.backend_state = "UPLOAD_FAILED"
                st.session_state.error_info = i_upload
                st.error(f"❌ IMU upload failed: {i_upload.get('message')}")
                return

        # Step 3: Confirm Upload
        with progress_placeholder.container():
            st.info("Verifying uploaded artifacts in S3...")
            confirm_res = client.confirm_upload(session_id)
            if not confirm_res.get("success"):
                st.session_state.is_processing = False
                st.session_state.error_info = confirm_res
                st.error(f"❌ Upload confirmation failed: {confirm_res.get('message')}")
                return
            st.session_state.backend_state = "UPLOADED"

        # Step 4: Start Inference on ECS Fargate
        with progress_placeholder.container():
            st.info("Dispatching machine learning inference on ECS Fargate...")
            start_res = client.start_inference(session_id)
            if not start_res.get("success"):
                st.session_state.is_processing = False
                st.session_state.error_info = start_res
                st.error(f"❌ Failed to dispatch inference: {start_res.get('message')}")
                return
            st.session_state.backend_state = "PROCESSING"

        # Step 5: Poll Status until COMPLETE
        poll_count = 0
        max_polls = 120  # 10 minutes timeout (5s intervals)
        while poll_count < max_polls:
            with progress_placeholder.container():
                st.info(f"⏳ Executing multimodal inference on AWS Fargate... (Elapsed: {poll_count * 5}s)")
            time.sleep(5)
            poll_count += 1

            status_res = client.get_status(session_id)
            if not status_res.get("success"):
                st.session_state.is_processing = False
                st.session_state.error_info = status_res
                st.error(f"❌ Error during status check: {status_res.get('message')}")
                return

            current_st = status_res.get("status")
            st.session_state.backend_state = current_st

            if current_st == "COMPLETE":
                progress_placeholder.empty()
                st.session_state.results = status_res
                st.session_state.is_processing = False
                st.success("✅ Multimodal Gait Assessment Complete!")
                st.rerun()

            elif current_st in ("UPLOAD_FAILED", "PROCESSING_FAILED", "NARRATIVE_FAILED", "CONNECTION_FAILED"):
                progress_placeholder.empty()
                st.session_state.is_processing = False
                st.session_state.error_info = status_res.get("error", {})
                st.error(f"🛑 Pipeline stopped in state: {current_st}")
                st.rerun()

        # Polling timeout
        progress_placeholder.empty()
        st.session_state.is_processing = False
        st.warning("⚠️ Processing is taking longer than expected. You can check results later using your Session ID.")

    # Render Current State Tracker
    if st.session_state.backend_state:
        st.markdown("---")
        st.markdown(f"**Current Session:** `{st.session_state.session_id}`")
        render_state_tracker(st.session_state.backend_state, st.session_state.error_info)

    # Render Results Dashboard (when results are available)
    if st.session_state.results and st.session_state.backend_state == "COMPLETE":
        st.markdown("---")
        render_results_dashboard(st.session_state.results)


if __name__ == "__main__":
    main()
