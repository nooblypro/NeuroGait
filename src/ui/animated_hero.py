"""NeuroGait Hero Experience & Multimodal Observer Showcase.

Renders an interactive 5-beat scrollytelling hero banner at the top of Streamlit,
featuring background video scrubbing, HUD telemetry, feature tags, and seamless
transition into the assessment interface.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def render_animated_hero():
    """Render the 5-beat animated hero experience at the top of the app."""
    hero_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
    *, *::before, *::after {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    body {
        background: #060709;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #FFFFFF;
        overflow: hidden;
    }

    #neurogait-hero-stage {
        position: relative;
        width: 100%;
        height: 540px;
        background: #060709;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(223, 177, 91, 0.4);
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.8), 0 0 35px rgba(223, 177, 91, 0.15);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .hero-video-wrap {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        z-index: 0;
    }

    #hero-bg-video {
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center 48%;
        opacity: 0.75;
        filter: contrast(1.15) brightness(0.95);
    }

    .hero-scrim {
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 80% 80% at 50% 50%, rgba(6, 7, 9, 0.3) 0%, rgba(6, 7, 9, 0.85) 75%, rgba(6, 7, 9, 0.98) 100%);
    }

    .hero-hud-header {
        position: relative;
        z-index: 10;
        padding: 1.2rem 1.8rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(6, 7, 9, 0.65);
        backdrop-filter: blur(12px);
    }

    .hud-title {
        font-family: monospace;
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: 0.22em;
        color: #FFFFFF;
    }

    .hud-subtitle {
        font-family: monospace;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.18em;
        color: #DFB15B;
        margin-top: 0.2rem;
    }

    .hud-badge {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-family: monospace;
        font-size: 0.72rem;
        color: #F8FAFC;
        letter-spacing: 0.14em;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #DFB15B;
        box-shadow: 0 0 12px #DFB15B;
        animation: pulse-dot-anim 2s infinite ease-in-out;
    }

    @keyframes pulse-dot-anim {
        0%, 100% { opacity: 0.4; transform: scale(0.9); }
        50% { opacity: 1; transform: scale(1.3); box-shadow: 0 0 16px #DFB15B; }
    }

    .hero-chapters-nav {
        position: relative;
        z-index: 10;
        display: flex;
        gap: 0.5rem;
        padding: 0.6rem 1.5rem;
        background: rgba(8, 10, 16, 0.85);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        overflow-x: auto;
    }

    .chap-btn {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.18);
        color: #CBD5E1;
        font-family: monospace;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        padding: 0.4rem 0.85rem;
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.2s ease;
        white-space: nowrap;
    }

    .chap-btn:hover {
        background: rgba(223, 177, 91, 0.25);
        border-color: #DFB15B;
        color: #FFFFFF;
    }

    .chap-btn.active {
        background: #DFB15B;
        border-color: #DFB15B;
        color: #060709;
        font-weight: 700;
        box-shadow: 0 0 12px rgba(223, 177, 91, 0.5);
    }

    .hero-narrative-content {
        position: relative;
        z-index: 10;
        padding: 1.5rem 2rem;
        flex: 1;
        display: flex;
        align-items: center;
    }

    .beat-card {
        display: none;
        width: 100%;
        animation: fadeInBeat 0.3s ease forwards;
    }

    .beat-card.beat-active {
        display: block;
    }

    @keyframes fadeInBeat {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .beat-chip {
        font-family: monospace;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.25em;
        color: #DFB15B;
        margin-bottom: 0.4rem;
    }

    .hero-main-title {
        font-size: 3.2rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        color: #FFFFFF;
        line-height: 1;
        margin: 0;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.9), 0 0 30px rgba(223, 177, 91, 0.3);
    }

    .hero-statement {
        font-size: 1.4rem;
        font-weight: 500;
        color: #F8FAFC;
        margin-top: 0.5rem;
    }

    .hero-highlights {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-top: 1.2rem;
        flex-wrap: wrap;
    }

    .hl-pill {
        font-family: monospace;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 0.35rem 0.85rem;
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        color: #FFFFFF;
    }

    .gold-pill {
        background: rgba(223, 177, 91, 0.25);
        border-color: #DFB15B;
        color: #DFB15B;
    }

    .hl-plus, .hl-arrow {
        color: #DFB15B;
        font-weight: 700;
    }

    .beat-split {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
        align-items: center;
    }

    .big-num {
        font-size: 3.2rem;
        font-weight: 800;
        line-height: 1;
    }

    .gold-text { color: #DFB15B; text-shadow: 0 0 20px rgba(223, 177, 91, 0.4); }
    .white-text { color: #FFFFFF; }

    .beat-title {
        font-size: 1.2rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        color: #FFFFFF;
        margin-top: 0.2rem;
    }

    .beat-desc {
        font-size: 0.88rem;
        color: #CBD5E1;
        margin-top: 0.4rem;
        line-height: 1.4;
    }

    .tag-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.4rem;
        margin-top: 0.6rem;
    }

    .tag-item {
        font-family: monospace;
        font-size: 0.7rem;
        padding: 0.3rem 0.5rem;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(56, 189, 248, 0.4);
        border-radius: 4px;
        color: #38BDF8;
    }

    .callout-box {
        background: rgba(15, 23, 42, 0.92);
        border-left: 4px solid #F59E0B;
        border-radius: 6px;
        padding: 1rem 1.2rem;
    }

    .callout-badge {
        font-family: monospace;
        font-size: 0.65rem;
        font-weight: 700;
        color: #F59E0B;
        letter-spacing: 0.18em;
    }

    .callout-heading {
        font-size: 1.1rem;
        color: #FFFFFF;
        margin: 0.3rem 0 0.1rem 0;
    }

    .callout-interval {
        font-family: monospace;
        font-size: 0.85rem;
        color: #DFB15B;
    }

    .callout-conf {
        font-size: 0.82rem;
        color: #CBD5E1;
        margin-top: 0.3rem;
    }

    .bedrock-showcase {
        display: flex;
        align-items: center;
        gap: 1.2rem;
        width: 100%;
    }

    .ev-console {
        flex: 1;
        background: rgba(8, 10, 16, 0.92);
        border: 1px solid rgba(223, 177, 91, 0.35);
        border-radius: 6px;
        padding: 0.9rem 1.1rem;
        font-family: monospace;
        font-size: 0.78rem;
    }

    .console-title {
        color: #DFB15B;
        font-weight: 700;
        letter-spacing: 0.14em;
        margin-bottom: 0.5rem;
    }

    .console-row {
        margin-bottom: 0.2rem;
        color: #CBD5E1;
    }

    .console-row strong { color: #FFFFFF; }

    .arrow-divider {
        font-size: 1.5rem;
        color: #DFB15B;
    }

    .bedrock-card {
        flex: 1.4;
        background: rgba(15, 23, 42, 0.92);
        border: 1px solid rgba(56, 189, 248, 0.4);
        border-radius: 6px;
        padding: 0.9rem 1.1rem;
    }

    .bedrock-tag {
        font-family: monospace;
        font-size: 0.65rem;
        font-weight: 700;
        color: #38BDF8;
        letter-spacing: 0.14em;
    }

    .bedrock-text {
        font-style: italic;
        color: #FFFFFF;
        font-size: 0.9rem;
        margin: 0.4rem 0;
        line-height: 1.35;
    }

    .bedrock-sub {
        font-size: 0.72rem;
        color: #94A3B8;
    }

    .synthesis-box {
        text-align: center;
        width: 100%;
    }

    .synth-words {
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        color: #FFFFFF;
        text-shadow: 0 0 25px rgba(223, 177, 91, 0.35);
    }

    .synth-credits {
        margin-top: 1rem;
    }

    .credits-name {
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 0.2em;
        color: #DFB15B;
    }

    .credits-meta {
        font-size: 0.8rem;
        color: #CBD5E1;
        margin-top: 0.2rem;
    }

    .hero-handoff-bar {
        position: relative;
        z-index: 10;
        padding: 0.65rem 1.5rem;
        background: rgba(15, 23, 42, 0.95);
        border-top: 1px solid rgba(223, 177, 91, 0.3);
        text-align: center;
    }

    .handoff-label {
        font-family: monospace;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.2em;
        color: #38BDF8;
    }
    </style>
    </head>
    <body>
    <div id="neurogait-hero-stage">
        <!-- 0. Background Video -->
        <div class="hero-video-wrap">
            <video id="hero-bg-video" autoplay muted loop playsinline disablepictureinpicture>
                <source src="/app/static/newfinal.mp4" type="video/mp4" />
            </video>
            <div class="hero-scrim"></div>
        </div>

        <!-- 1. Ambient HUD Overlay Header -->
        <div class="hero-hud-header">
            <div class="hud-brand">
                <div class="hud-title">NEUROGAIT</div>
                <div class="hud-subtitle">MULTIMODAL OBSERVER // MOVEMENT ANALYSIS</div>
            </div>
            <div class="hud-badge">
                <span class="pulse-dot"></span>
                <span class="hud-status">MULTIMODAL PIPELINE ONLINE</span>
            </div>
        </div>

        <!-- 2. Interactive Chapter Tabs (5 Narrative Beats) -->
        <div class="hero-chapters-nav">
            <button class="chap-btn active" onclick="switchBeat(1)">1. HERO</button>
            <button class="chap-btn" onclick="switchBeat(2)">2. MODALITIES & FEATURES</button>
            <button class="chap-btn" onclick="switchBeat(3)">3. SYNC & DETECT</button>
            <button class="chap-btn" onclick="switchBeat(4)">4. EVIDENCE & BEDROCK</button>
            <button class="chap-btn" onclick="switchBeat(5)">5. SYNTHESIS</button>
        </div>

        <!-- 3. Narrative Stage (5 Beats) -->
        <div class="hero-narrative-content">
            <!-- BEAT 1: HERO -->
            <div class="beat-card beat-active" id="bcard-1">
                <div class="beat-chip">MULTIMODAL MOVEMENT ASSESSMENT</div>
                <h1 class="hero-main-title">NEUROGAIT</h1>
                <p class="hero-statement">Movement is information.</p>
                <div class="hero-highlights">
                    <span class="hl-pill">Video Pose Kinematics</span>
                    <span class="hl-plus">+</span>
                    <span class="hl-pill">6-Axis Wearable IMU</span>
                    <span class="hl-arrow">➔</span>
                    <span class="hl-pill gold-pill">8 Fused Features</span>
                </div>
            </div>

            <!-- BEAT 2: MODALITIES & FEATURES -->
            <div class="beat-card" id="bcard-2">
                <div class="beat-split">
                    <div class="split-side">
                        <div class="big-num gold-text">02</div>
                        <div class="beat-title">MODALITIES</div>
                        <p class="beat-desc">Two synchronized streams: 2D Video Pose Kinematics + 128Hz Wearable IMU Inertial Sensors.</p>
                    </div>
                    <div class="split-side">
                        <div class="big-num white-text">08</div>
                        <div class="beat-title">FUSED FEATURES</div>
                        <div class="tag-grid">
                            <span class="tag-item">left_ankle_velocity</span>
                            <span class="tag-item">right_ankle_velocity</span>
                            <span class="tag-item">left_knee_angle</span>
                            <span class="tag-item">right_knee_angle</span>
                            <span class="tag-item">stride_width</span>
                            <span class="tag-item">accel_rms</span>
                            <span class="tag-item">gyro_x_var</span>
                            <span class="tag-item">gyro_z_var</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- BEAT 3: SYNC & DETECT -->
            <div class="beat-card" id="bcard-3">
                <div class="beat-split">
                    <div class="split-side">
                        <div class="big-num gold-text">±0.1s</div>
                        <div class="beat-title">TEMPORAL ALIGNMENT</div>
                        <p class="beat-desc">High-precision cross-modal timestamp synchronization across walking trials.</p>
                    </div>
                    <div class="split-side">
                        <div class="callout-box">
                            <div class="callout-badge">MODEL DETECTED EPISODE</div>
                            <div class="callout-heading">POSSIBLE FoG EPISODE</div>
                            <div class="callout-interval">Interval: 05.2s — 06.8s</div>
                            <div class="callout-conf">Model Confidence: <strong>92%</strong> (Mean Class-1 Probability)</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- BEAT 4: EVIDENCE & BEDROCK -->
            <div class="beat-card" id="bcard-4">
                <div class="bedrock-showcase">
                    <div class="ev-console">
                        <div class="console-title">STRUCTURED ML EVIDENCE</div>
                        <div class="console-row"><span>type:</span> <strong>FoG</strong></div>
                        <div class="console-row"><span>confidence:</span> <strong>0.92</strong></div>
                        <div class="console-row"><span>interval:</span> <strong>05.2s — 06.8s</strong></div>
                        <div class="console-row"><span>primary_cue:</span> <strong>left_ankle_velocity</strong></div>
                    </div>
                    <div class="arrow-divider">➔</div>
                    <div class="bedrock-card">
                        <div class="bedrock-tag">AMAZON BEDROCK // CLAUDE 3.5 SONNET</div>
                        <div class="bedrock-text">
                            “A possible freezing episode was detected during this interval (05.2s — 06.8s), primarily associated with altered left ankle movement.”
                        </div>
                        <div class="bedrock-sub">Structured ML evidence synthesized into grounded clinical narrative without diagnostic claims.</div>
                    </div>
                </div>
            </div>

            <!-- BEAT 5: SYNTHESIS -->
            <div class="beat-card" id="bcard-5">
                <div class="synthesis-box">
                    <div class="synth-words">Movement. Measured. Explained.</div>
                    <div class="synth-credits">
                        <div class="credits-name">NEUROGAIT</div>
                        <div class="credits-meta">Made with love by Devika Anup × Shriram • 2026</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 4. Handoff Banner to Assessment Interface -->
        <div class="hero-handoff-bar">
            <span class="handoff-label">↓ BEGIN MOVEMENT ASSESSMENT BELOW ↓</span>
        </div>
    </div>

    <script>
    function switchBeat(beatNum) {
        const btns = document.querySelectorAll('.chap-btn');
        btns.forEach((btn, idx) => {
            if (idx + 1 === beatNum) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        const cards = document.querySelectorAll('.beat-card');
        cards.forEach((card, idx) => {
            if (idx + 1 === beatNum) {
                card.classList.add('beat-active');
            } else {
                card.classList.remove('beat-active');
            }
        });
    }
    </script>
    </body>
    </html>
    """

    components.html(hero_html, height=560, scrolling=False)
