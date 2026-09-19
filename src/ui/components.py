"""UI Presentation Components and Visualizations for NeuroGait Streamlit App."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

# Color constants for episode classifications (accessible high-contrast palette)
COLOR_FOG = "#EF4444"         # Red
COLOR_BORDERLINE = "#F59E0B"  # Amber
COLOR_NORMAL = "#10B981"      # Emerald green

TYPE_STYLES = {
    "FoG": {"bg": "#FEE2E2", "text": "#991B1B", "border": "#EF4444", "badge": "🚨 Freezing of Gait"},
    "Borderline": {"bg": "#FEF3C7", "text": "#92400E", "border": "#F59E0B", "badge": "⚠️ Borderline Transition"},
    "Normal": {"bg": "#D1FAE5", "text": "#065F46", "border": "#10B981", "badge": "✅ Normal Gait"},
}

PIPELINE_STEPS = [
    ("CREATED", "Session Initialized"),
    ("UPLOADING", "Uploading to S3"),
    ("UPLOADED", "Upload Confirmed"),
    ("PROCESSING", "ECS Fargate ML Active"),
    ("ML_COMPLETE", "ML Inferences Ready"),
    ("NARRATIVE_GENERATING", "Synthesizing Narrative"),
    ("COMPLETE", "Assessment Ready"),
]

CUE_LABELS = {
    "accel_rms": "Acceleration RMS (accel_rms)",
    "stride_width": "Stride Width (stride_width)",
    "gyro_x_var": "ML Angular Velocity Variance (gyro_x_var)",
    "gyro_z_var": "SI Angular Velocity Variance (gyro_z_var)",
    "left_ankle_velocity": "Left Ankle Velocity (left_ankle_velocity)",
    "right_ankle_velocity": "Right Ankle Velocity (right_ankle_velocity)",
    "left_knee_angle": "Left Knee Flexion Angle (left_knee_angle)",
    "right_knee_angle": "Right Knee Flexion Angle (right_knee_angle)",
}


def inject_custom_styles():
    """Inject polished, accessible CSS styles into the Streamlit app."""
    st.markdown(
        """
        <style>
        /* Modern Clean Typography & Layout */
        .main-header {
            font-size: 2.3rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.2rem;
            color: #0F172A;
        }
        .sub-header {
            font-size: 1.05rem;
            color: #475569;
            margin-bottom: 1.5rem;
        }
        .mode-badge-active {
            background-color: #2563EB;
            color: white;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-block;
        }
        .mode-badge-disabled {
            background-color: #E2E8F0;
            color: #64748B;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 500;
            display: inline-block;
        }
        .metric-card {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }
        .metric-val {
            font-size: 2rem;
            font-weight: 700;
            margin-top: 4px;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        .disclaimer-box {
            background-color: #F8FAFC;
            border-left: 4px solid #3B82F6;
            padding: 14px 18px;
            border-radius: 0 8px 8px 0;
            font-size: 0.84rem;
            color: #334155;
            margin-top: 2rem;
            margin-bottom: 1rem;
            line-height: 1.5;
        }
        .timeline-container {
            width: 100%;
            background: #F1F5F9;
            border-radius: 8px;
            height: 36px;
            position: relative;
            margin: 1rem 0;
            overflow: hidden;
            display: flex;
        }
        .timeline-bar {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.75rem;
            font-weight: 600;
            transition: opacity 0.2s;
        }
        .timeline-bar:hover {
            opacity: 0.85;
            cursor: pointer;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    """Render top application header and description."""
    st.markdown('<div class="main-header">🧠 NeuroGait</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Objective Multimodal Freezing of Gait (FoG) Assessment Platform for Parkinson\'s Disease</div>',
        unsafe_allow_html=True,
    )


def render_mode_selector() -> str:
    """Render mode selection tabs distinguishing Recorded Mode from Live Mode."""
    selected_mode = st.radio(
        "Select Operating Mode",
        options=["recorded", "live_demo"],
        format_func=lambda m: (
            "📁 Recorded Analysis Mode (Primary Demo)"
            if m == "recorded"
            else "🎥 Live Mode — Hardware Validation Pending (Experimental Replay)"
        ),
        horizontal=True,
        label_visibility="collapsed",
    )
    if selected_mode == "live_demo":
        st.info(
            "ℹ️ **Live Mode — Hardware Validation Pending**: "
            "This interface demonstrates the real-time streaming ingestion pipeline using verified replayed trial data "
            "(`PDFE01_1.mp4` + `SUB01_1.txt`). Physical camera and wearable IMU hardware integration is pending physical test bench setup."
        )
    return selected_mode


def render_multimodal_pipeline_flow():
    """Render a visual, concise representation of the 6-stage multimodal pipeline."""
    st.markdown("### 🔄 Multimodal Assessment Pipeline")
    st.caption("How NeuroGait processes synchronized kinematic video and wearable inertial telemetry:")

    st.markdown(
        """
        <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; margin: 1rem 0; padding: 14px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;">
            <div style="flex: 1; min-width: 130px; text-align: center; padding: 10px; background: white; border-radius: 6px; border: 1px solid #CBD5E1;">
                <div style="font-size: 1.3rem;">📹 + 📊</div>
                <div style="font-weight: 700; font-size: 0.8rem; color: #0F172A; margin-top: 4px;">1. Dual Inputs</div>
                <div style="font-size: 0.72rem; color: #64748B;">Monocular Video + 128Hz IMU</div>
            </div>
            <div style="color: #94A3B8; font-weight: bold; font-size: 1.1rem;">→</div>
            <div style="flex: 1; min-width: 130px; text-align: center; padding: 10px; background: white; border-radius: 6px; border: 1px solid #CBD5E1;">
                <div style="font-size: 1.3rem;">⚙️</div>
                <div style="font-weight: 700; font-size: 0.8rem; color: #0F172A; margin-top: 4px;">2. Feature Extract</div>
                <div style="font-size: 0.72rem; color: #64748B;">MediaPipe Pose & IMU Kinetics</div>
            </div>
            <div style="color: #94A3B8; font-weight: bold; font-size: 1.1rem;">→</div>
            <div style="flex: 1; min-width: 130px; text-align: center; padding: 10px; background: white; border-radius: 6px; border: 1px solid #CBD5E1;">
                <div style="font-size: 1.3rem;">⏱️</div>
                <div style="font-weight: 700; font-size: 0.8rem; color: #0F172A; margin-top: 4px;">3. Temporal Sync</div>
                <div style="font-size: 0.72rem; color: #64748B;">±0.1s Dynamic Window Fusion</div>
            </div>
            <div style="color: #94A3B8; font-weight: bold; font-size: 1.1rem;">→</div>
            <div style="flex: 1; min-width: 130px; text-align: center; padding: 10px; background: white; border-radius: 6px; border: 1px solid #CBD5E1;">
                <div style="font-size: 1.3rem;">🧠</div>
                <div style="font-weight: 700; font-size: 0.8rem; color: #0F172A; margin-top: 4px;">4. ML Classifier</div>
                <div style="font-size: 0.72rem; color: #64748B;">Supervised Random Forest</div>
            </div>
            <div style="color: #94A3B8; font-weight: bold; font-size: 1.1rem;">→</div>
            <div style="flex: 1; min-width: 130px; text-align: center; padding: 10px; background: white; border-radius: 6px; border: 1px solid #CBD5E1;">
                <div style="font-size: 1.3rem;">📈</div>
                <div style="font-weight: 700; font-size: 0.8rem; color: #0F172A; margin-top: 4px;">5. Episode Logic</div>
                <div style="font-size: 0.72rem; color: #64748B;">Banding & ≤1.0s Gap Merging</div>
            </div>
            <div style="color: #94A3B8; font-weight: bold; font-size: 1.1rem;">→</div>
            <div style="flex: 1; min-width: 130px; text-align: center; padding: 10px; background: white; border-radius: 6px; border: 1px solid #CBD5E1;">
                <div style="font-size: 1.3rem;">📝</div>
                <div style="font-weight: 700; font-size: 0.8rem; color: #0F172A; margin-top: 4px;">6. Clinical Report</div>
                <div style="font-size: 0.72rem; color: #64748B;">Primary Cues & Narrative</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_session_assessment_banner(summary: Dict[str, Any], episodes: List[Dict[str, Any]], exec_mode: str = "cloud"):
    """Render executive assessment card summarizing trial findings in plain language."""
    fog_eps = [e for e in episodes if e.get("type") == "FoG"]
    fog_count = len(fog_eps)
    total_eps = len(episodes)

    mean_fog_conf = (sum(e.get("confidence", 0.0) for e in fog_eps) / fog_count) if fog_count > 0 else 0.0

    # Dominant primary cue
    cue_counts: Dict[str, int] = {}
    for e in fog_eps:
        c = e.get("primary_cue", "none")
        cue_counts[c] = cue_counts.get(c, 0) + 1
    dominant_cue = max(cue_counts, key=cue_counts.get) if cue_counts else "None"
    dominant_cue_label = CUE_LABELS.get(dominant_cue, dominant_cue)

    # Execution target indicator
    if exec_mode == "cloud":
        mode_badge = "<span style='background: #DBEAFE; color: #1E40AF; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.78rem;'>☁️ AWS CLOUD INFERENCE (ECS Fargate + S3 + DynamoDB)</span>"
    else:
        mode_badge = "<span style='background: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.78rem;'>💻 LOCAL DEMO MODE (Deterministic On-Device Engine / models/fog_model.pkl)</span>"

    if fog_count > 0:
        title = "🚨 Freezing of Gait (FoG) Detected in Patient Trial"
        bg_color = "#FEF2F2"
        border_color = "#EF4444"
        status_desc = f"Identified <strong>{fog_count}</strong> freezing episode(s) across the recorded trial duration."
    else:
        title = "✅ No Overt Freezing of Gait (FoG) Detected"
        bg_color = "#F0FDF4"
        border_color = "#10B981"
        status_desc = "Patient maintained continuous rhythmic gait throughout the evaluated recording."

    st.markdown(
        f"""
        <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-left: 6px solid {border_color}; border-radius: 8px; padding: 18px; margin-bottom: 1.2rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #0F172A;">{title}</div>
                <div>{mode_badge}</div>
            </div>
            <div style="font-size: 0.95rem; color: #334155; margin-bottom: 12px;">{status_desc}</div>
            <div style="display: flex; flex-wrap: wrap; gap: 20px; font-size: 0.88rem; color: #475569; padding-top: 8px; border-top: 1px solid #E2E8F0;">
                <div><strong>Total Episodes:</strong> {fog_count} FoG of {total_eps} total intervals</div>
                <div><strong>Mean Freezing Confidence:</strong> {mean_fog_conf * 100:.1f}%</div>
                <div><strong>Dominant Statistical Cue:</strong> <code>{dominant_cue_label}</code></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_judge_cheat_sheet():
    """Render clean evaluator & judge reference guide answering 5 core architectural questions."""
    with st.expander("💡 Evaluator & Judge Quick Reference Guide (5 Core Architectural Questions)"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 1. WHAT?")
            st.markdown(
                "NeuroGait provides **objective multimodal detection, temporal quantification, and algorithmic explanation** "
                "of Freezing of Gait (FoG) episodes in Parkinson's Disease."
            )
            st.markdown("#### 2. INPUT?")
            st.markdown(
                "Synchronized **monocular patient video** (MediaPipe 2D body pose landmarks) + **128 Hz wearable IMU** (tri-axial accelerometer & gyroscope)."
            )
            st.markdown("#### 3. HOW?")
            st.markdown(
                "Dynamic $\\pm 0.1$s temporal sync $\\rightarrow$ **8 canonical biomechanical features** $\\rightarrow$ **supervised Random Forest** "
                "($p \\ge 0.60$ FoG, $0.40 \\le p < 0.60$ Borderline, $p < 0.40$ Normal) $\\rightarrow$ **episode aggregation** with $\\le 1.0$s gap merging."
            )
        with col_b:
            st.markdown("#### 4. WHERE?")
            st.markdown(
                "Production cloud pipeline on **AWS**: Streamlit UI $\\rightarrow$ **API Gateway** $\\rightarrow$ "
                "**Lambda Control Plane** $\\rightarrow$ **S3** artifact storage $\\rightarrow$ **ECS Fargate** container task $\\rightarrow$ "
                "**DynamoDB** state machine. *(Also includes a 100% deterministic on-device local engine fallback).* "
            )
            st.markdown("#### 5. OUTPUT?")
            st.markdown(
                "Standardized canonical JSON containing timestamped **episodes**, **model confidence ratings**, **primary statistical cue attributions**, "
                "and clinical safety-bounded **explanatory narratives**."
            )


def render_state_tracker(current_state: str, error_info: Optional[Dict[str, Any]] = None):
    """Render visual stepped pipeline state tracker."""
    if current_state in ("UPLOAD_FAILED", "PROCESSING_FAILED", "NARRATIVE_FAILED", "CONNECTION_FAILED"):
        err_msg = error_info.get("message") if error_info else "An error occurred during execution."
        st.error(f"🛑 Pipeline Terminated in Failure State: **{current_state}**\n\n*{err_msg}*")
        return

    # Check index of current state
    curr_idx = -1
    for idx, (code, _) in enumerate(PIPELINE_STEPS):
        if code == current_state:
            curr_idx = idx
            break

    cols = st.columns(len(PIPELINE_STEPS))
    for idx, (code, label) in enumerate(PIPELINE_STEPS):
        with cols[idx]:
            if idx < curr_idx:
                icon = "✅"
                color = "#10B981"
            elif idx == curr_idx:
                icon = "🔄" if code != "COMPLETE" else "🎉"
                color = "#2563EB"
            else:
                icon = "⚪"
                color = "#94A3B8"

            st.markdown(
                f"<div style='text-align: center; font-size: 0.75rem; color: {color}; font-weight: 600;'>"
                f"{icon}<br>{label}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)


def render_summary_metrics(summary: Dict[str, Any], episode_count: int):
    """Render overview summary cards for gait episodes."""
    fog_count = summary.get("fog_episodes", 0)
    borderline_count = summary.get("borderline_episodes", 0)
    normal_count = summary.get("normal_episodes", 0)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">Total Intervals</div>'
            f'<div class="metric-val" style="color: #0F172A;">{episode_count}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">FoG Episodes</div>'
            f'<div class="metric-val" style="color: #DC2626;">{fog_count}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">Borderline Transitions</div>'
            f'<div class="metric-val" style="color: #D97706;">{borderline_count}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">Normal Segments</div>'
            f'<div class="metric-val" style="color: #059669;">{normal_count}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_timeline_visualization(episodes: List[Dict[str, Any]]):
    """Render interactive color-coded visual timeline from canonical episode data."""
    if not episodes:
        return

    st.markdown("### 📊 Episode Sequence Timeline")
    st.caption("Visual distribution of classified intervals across the recorded trial duration:")

    trial_start = min(e["start"] for e in episodes)
    trial_end = max(e["end"] for e in episodes)
    total_dur = max(0.01, trial_end - trial_start)

    # Sort episodes by start timestamp
    sorted_eps = sorted(episodes, key=lambda x: (x["start"], x["end"]))

    # Build multi-bar timeline representation
    bars_html = []
    for ep in sorted_eps:
        ep_type = ep.get("type", "Normal")
        start = ep["start"]
        end = ep["end"]
        conf = ep.get("confidence", 0.0)
        cue = ep.get("primary_cue", "none")
        cue_lbl = CUE_LABELS.get(cue, cue)

        dur = max(0.01, end - start)
        width_pct = max(1.0, (dur / total_dur) * 100.0)

        color = COLOR_FOG if ep_type == "FoG" else (COLOR_BORDERLINE if ep_type == "Borderline" else COLOR_NORMAL)
        title_attr = f"{ep_type}: {start:.2f}s–{end:.2f}s ({dur:.2f}s) | Conf: {conf*100:.1f}% | Cue: {cue_lbl}"

        bars_html.append(
            f'<div class="timeline-bar" style="width: {width_pct:.2f}%; background-color: {color};" title="{title_attr}">'
            f'{ep_type[0]}'
            f'</div>'
        )

    timeline_html = f'<div class="timeline-container">{"".join(bars_html)}</div>'
    st.markdown(timeline_html, unsafe_allow_html=True)

    # Legend
    leg1, leg2, leg3 = st.columns(3)
    with leg1:
        st.markdown(f"<span style='color: {COLOR_FOG}; font-weight: 700;'>■ [F] Freezing of Gait (FoG)</span> (p ≥ 0.60)", unsafe_allow_html=True)
    with leg2:
        st.markdown(f"<span style='color: {COLOR_BORDERLINE}; font-weight: 700;'>■ [B] Borderline Transition</span> (0.40 ≤ p < 0.60)", unsafe_allow_html=True)
    with leg3:
        st.markdown(f"<span style='color: {COLOR_NORMAL}; font-weight: 700;'>■ [N] Normal Gait</span> (p < 0.40)", unsafe_allow_html=True)


def render_episodes_table(episodes: List[Dict[str, Any]]):
    """Render sortable, filterable table of canonical episodes with plain language formatting."""
    st.markdown("### 📋 Detailed Gait Episode Log")

    filter_type = st.selectbox(
        "Filter by Episode Type",
        options=["All Types", "FoG", "Borderline", "Normal"],
        index=0,
    )

    records = []
    for idx, ep in enumerate(episodes, start=1):
        ep_type = ep.get("type", "Normal")
        if filter_type != "All Types" and ep_type != filter_type:
            continue

        start = ep["start"]
        end = ep["end"]
        duration = round(end - start, 3)
        conf = ep.get("confidence", 0.0)
        cue = ep.get("primary_cue", "none")
        cue_formatted = CUE_LABELS.get(cue, cue)
        mode = ep.get("data_mode", "real")

        type_badge = "🚨 FoG" if ep_type == "FoG" else ("⚠️ Borderline" if ep_type == "Borderline" else "✅ Normal")

        records.append({
            "Interval #": idx,
            "Classification": type_badge,
            "Start Time": f"{start:.3f} s",
            "End Time": f"{end:.3f} s",
            "Duration": f"{duration:.3f} s",
            "Confidence": f"{conf * 100:.1f}% ({conf:.4f})",
            "Primary Statistical Cue": cue_formatted,
            "Data Mode": mode,
        })

    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No episodes match the selected filter.")


def render_explanation_section(explanation: Optional[Dict[str, Any]]):
    """Render clinical narrative explanation, provider attribution, and safety disclaimer."""
    st.markdown("### 📝 Clinical Assessment Narrative")

    if not explanation or explanation.get("status") != "SUCCESS":
        status_str = explanation.get("status", "UNAVAILABLE") if explanation else "UNAVAILABLE"
        reason_str = explanation.get("reason", "No narrative returned by backend.") if explanation else "No narrative available."
        st.warning(f"Explanatory narrative is currently **{status_str}** ({reason_str}). Deterministic ML predictions remain fully valid above.")
        return

    provider = explanation.get("provider", "deterministic_rule")
    narrative = explanation.get("narrative", "")
    latency = explanation.get("latency_ms")
    cached = explanation.get("cached", False)
    disclaimer = explanation.get("clinical_disclaimer", "")

    # Provider attribution badge
    if provider == "deterministic_rule":
        prov_desc = "Deterministic Rule Engine (Reproducible, zero hallucination risk)"
    elif provider == "bedrock_claude":
        prov_desc = "AWS Bedrock (Claude 3.5 Sonnet)"
    else:
        prov_desc = provider

    prov_badge = f"**Explanation Provider:** `{provider}` — *{prov_desc}*"
    if cached:
        prov_badge += " • ⚡ *Cached from S3 Storage*"
    if latency is not None:
        prov_badge += f" • ⏱️ *Latency: {latency} ms*"

    st.markdown(prov_badge)
    st.info(narrative)

    # Primary cue attribution notice
    st.markdown(
        """
        > **Primary Statistical Cue Notice**: The *primary cue* indicates the specific kinematic or inertial feature showing the highest standardized deviation relative to baseline. **It represents an objective mathematical deviation, NOT a clinical diagnosis or medical etiology.**
        """
    )

    # Clinical safety disclaimer
    if disclaimer:
        st.markdown(
            f'<div class="disclaimer-box"><strong>CLINICAL SAFETY DISCLOSURE:</strong> {disclaimer}</div>',
            unsafe_allow_html=True,
        )


def render_past_session_lookup(api_client, on_load_session):
    """Render lookup box to retrieve completed assessments by session ID."""
    with st.expander("🔍 Look Up Previous Assessment Result"):
        lookup_id = st.text_input("Enter Session ID (UUIDv4):", placeholder="e.g. f722d81c-c55d-4740-b1f0-934372650b26")
        if st.button("Load Assessment", key="btn_lookup"):
            if not lookup_id.strip():
                st.warning("Please enter a valid session ID.")
            else:
                with st.spinner("Fetching session from backend..."):
                    res = api_client.get_status(lookup_id.strip())
                    if res.get("success"):
                        on_load_session(res)
                    else:
                        st.error(f"Failed to load session: {res.get('message', 'Session not found.')}")
