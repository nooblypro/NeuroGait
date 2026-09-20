"""NeuroGait Animated Scroll Hero Experience.

Integrates the 5-beat scroll-driven cinematic interactive intro into Streamlit
using a same-origin component bridge that scrubs background video and drives narrative
beats synchronously with user page scrolling.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def render_animated_hero():
    """Render the 5-beat animated scroll hero experience at top of Streamlit app."""

    # 1. Render outer scroll track in Streamlit layout
    st.markdown(
        """
        <div id="neurogait-scroll-track" style="height: 380vh; width: 100%; pointer-events: none;"></div>
        <div class="scroll-handoff-banner" id="neurogait-handoff">
            <div class="handoff-content">
                <div class="handoff-chip">CINEMATIC INTRO COMPLETE</div>
                <h2 class="handoff-title">NEUROGAIT ASSESSMENT INTERFACE</h2>
                <p class="handoff-sub">Multimodal movement analysis powered by video pose & 6-axis IMU telemetry</p>
                <div class="handoff-indicator">↓ SCROLL TO BEGIN MOVEMENT ASSESSMENT ↓</div>
            </div>
        </div>
        <style>
        .scroll-handoff-banner {
            width: 100%;
            padding: 3rem 2rem;
            margin-bottom: 2rem;
            background: linear-gradient(180deg, rgba(6, 7, 9, 0.95) 0%, rgba(15, 23, 42, 0.8) 100%);
            border: 1px solid rgba(223, 177, 91, 0.3);
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        .handoff-chip {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.22em;
            color: #DFB15B;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        }
        .handoff-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: clamp(1.6rem, 3.2vw, 2.6rem);
            font-weight: 700;
            letter-spacing: 0.12em;
            color: #FFFFFF;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        .handoff-sub {
            font-family: 'Inter', sans-serif;
            font-size: clamp(0.95rem, 1.4vw, 1.15rem);
            color: #CBD5E1;
            margin-bottom: 1.25rem;
        }
        .handoff-indicator {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.18em;
            color: #38BDF8;
            animation: pulse-handoff 2s infinite ease-in-out;
        }
        @keyframes pulse-handoff {
            0%, 100% { opacity: 0.6; transform: translateY(0); }
            50% { opacity: 1; transform: translateY(4px); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 2. Component HTML containing CSS, HTML stage, and JS engine
    component_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />

  <style>
    :root {
      --bg-base: #060709;
      --bg-scrim: radial-gradient(ellipse 75% 75% at 50% 50%, rgba(6, 7, 9, 0.1) 20%, rgba(6, 7, 9, 0.55) 75%, rgba(6, 7, 9, 0.95) 100%);
      --text-primary: #ffffff;
      --text-offwhite: #f8fafc;
      --text-secondary: #cbd5e1;
      --text-muted: #94a3b8;
      --accent-gold: #dfb15b;
      --accent-gold-glow: rgba(223, 177, 91, 0.35);
      --accent-blue: #38bdf8;
      --accent-alert: #f59e0b;
      --line-subtle: rgba(255, 255, 255, 0.12);
      --line-light: rgba(255, 255, 255, 0.22);
      --line-gold: rgba(223, 177, 91, 0.5);
      --font-display: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
      --text-shadow-deep: 0 2px 14px rgba(0, 0, 0, 0.95), 0 4px 30px rgba(0, 0, 0, 0.85);
      --ease-cinematic: cubic-bezier(0.16, 1, 0.3, 1);
    }

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      background: transparent;
      overflow: hidden;
      width: 100%;
      height: 100%;
      font-family: var(--font-body);
      -webkit-font-smoothing: antialiased;
    }

    /* Fixed Viewport Stage filling parent screen */
    #viewport-stage {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      z-index: 9999;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      transition: opacity 0.5s ease;
    }

    .video-container {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      z-index: 0;
      overflow: hidden;
      background-color: var(--bg-base);
    }

    #bg-video {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center 48%;
      display: block;
      opacity: 1;
      filter: contrast(1.16) brightness(1.04) saturate(1.1);
      transform: translateZ(0);
      will-change: transform;
    }

    .vignette-layer {
      position: absolute;
      inset: 0;
      background: var(--bg-scrim);
      pointer-events: none;
      z-index: 1;
    }

    .hud-header {
      position: absolute;
      top: 0; left: 0; right: 0;
      padding: 2.2rem 3rem;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      z-index: 40;
      pointer-events: none;
    }

    .brand-title {
      font-family: var(--font-display);
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: 0.22em;
      color: #ffffff;
      text-transform: uppercase;
      text-shadow: var(--text-shadow-deep);
    }

    .brand-meta {
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 500;
      letter-spacing: 0.18em;
      color: var(--accent-gold);
      margin-top: 0.25rem;
      text-shadow: var(--text-shadow-deep);
    }

    .hud-status {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 500;
      letter-spacing: 0.16em;
      color: var(--text-offwhite);
      text-shadow: var(--text-shadow-deep);
    }

    .pulse-dot {
      width: 7px; height: 7px;
      border-radius: 50%;
      background-color: var(--accent-gold);
      box-shadow: 0 0 12px var(--accent-gold);
      animation: pulse-hud 2s infinite ease-in-out;
    }

    @keyframes pulse-hud {
      0%, 100% { opacity: 0.4; transform: scale(0.9); }
      50% { opacity: 1; transform: scale(1.2); box-shadow: 0 0 16px var(--accent-gold); }
    }

    .hud-separator { color: var(--line-light); }

    .hud-footer {
      position: absolute;
      bottom: 0; left: 0; right: 0;
      padding: 2rem 3rem;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      z-index: 40;
      pointer-events: none;
      font-family: var(--font-mono);
      text-shadow: var(--text-shadow-deep);
    }

    .hud-coord { display: flex; flex-direction: column; gap: 0.25rem; }
    .hud-label { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.22em; color: var(--text-muted); }
    .hud-mono { font-family: var(--font-mono); font-size: 0.78rem; font-weight: 500; letter-spacing: 0.18em; color: #ffffff; }

    .hud-legend { display: flex; gap: 1.8rem; }
    .legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.7rem; font-weight: 500; letter-spacing: 0.16em; color: var(--text-secondary); }
    .legend-box { width: 9px; height: 3px; }
    .video-accent { background-color: var(--accent-gold); box-shadow: 0 0 8px var(--accent-gold-glow); }
    .imu-accent { background-color: var(--accent-blue); box-shadow: 0 0 8px rgba(56, 189, 248, 0.4); }
    .fused-accent { background-color: #ffffff; box-shadow: 0 0 8px rgba(255, 255, 255, 0.6); }

    .narrative-stage {
      position: absolute;
      inset: 0;
      width: 100%; height: 100%;
      z-index: 20;
      pointer-events: none;
    }

    .beat {
      position: absolute;
      inset: 0;
      width: 100%; height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      visibility: hidden;
      transition: opacity 0.4s var(--ease-cinematic), transform 0.4s var(--ease-cinematic);
    }

    .beat-inner {
      width: 100%;
      max-width: 1360px;
      padding: 0 4rem;
      position: relative;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

    .center-content { align-items: center; text-align: center; }
    .hero-right-content {
      align-items: flex-end;
      text-align: right;
      padding-right: clamp(2.5rem, 8vw, 9rem);
      padding-left: 2rem;
    }

    .hero-title {
      font-family: var(--font-display);
      font-size: clamp(3.8rem, 8.5vw, 8.2rem);
      font-weight: 800;
      letter-spacing: 0.16em;
      color: #ffffff;
      line-height: 1.02;
      text-transform: uppercase;
      text-shadow: 0 4px 20px rgba(0, 0, 0, 0.95), 0 8px 45px rgba(0, 0, 0, 0.9), 0 0 45px rgba(223, 177, 91, 0.25);
    }

    .massive-number {
      font-family: var(--font-display);
      font-size: clamp(5.8rem, 13vw, 12rem);
      font-weight: 700;
      line-height: 0.9;
      letter-spacing: -0.04em;
      text-shadow: var(--text-shadow-deep);
    }

    .gold-num { color: var(--accent-gold); text-shadow: 0 0 40px var(--accent-gold-glow), var(--text-shadow-deep); }
    .white-num { color: #ffffff; text-shadow: 0 0 35px rgba(255, 255, 255, 0.4), var(--text-shadow-deep); }

    .beat-heading {
      font-family: var(--font-display);
      font-size: clamp(1.8rem, 3.8vw, 3.4rem);
      font-weight: 700;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: #ffffff;
      text-shadow: var(--text-shadow-deep);
      margin-top: 0.5rem;
    }

    .beat-sub {
      font-family: var(--font-body);
      font-size: clamp(1.05rem, 1.6vw, 1.4rem);
      font-weight: 400;
      color: var(--text-secondary);
      letter-spacing: 0.04em;
      margin-top: 0.75rem;
      max-width: 680px;
      text-shadow: var(--text-shadow-deep);
    }

    .hero-chip {
      font-family: var(--font-mono);
      font-size: clamp(0.78rem, 1.1vw, 1rem);
      font-weight: 600;
      letter-spacing: 0.3em;
      text-transform: uppercase;
      color: var(--accent-gold);
      margin-bottom: 1.4rem;
      text-shadow: var(--text-shadow-deep);
    }

    .hero-statement {
      font-family: var(--font-body);
      font-size: clamp(1.3rem, 2.2vw, 2.2rem);
      font-weight: 500;
      color: #ffffff;
      letter-spacing: 0.06em;
      margin-top: 1.6rem;
      max-width: 560px;
      text-shadow: var(--text-shadow-deep);
    }

    .scroll-hint {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      margin-top: 4.5rem;
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.24em;
      text-shadow: var(--text-shadow-deep);
    }

    .scroll-arrow {
      animation: float-arrow 2s infinite ease-in-out;
      color: var(--accent-gold);
      font-size: 1.2rem;
    }

    @keyframes float-arrow {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(8px); }
    }

    .modalities-phase {
      position: absolute; top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      width: 100%; display: flex; flex-direction: column;
      align-items: center; text-align: center;
      transition: opacity 0.4s var(--ease-cinematic), transform 0.4s var(--ease-cinematic);
    }

    .mod-pill-group { display: flex; align-items: center; gap: 1.5rem; margin-bottom: 1.5rem; }
    .mod-pill {
      font-family: var(--font-display);
      font-size: clamp(1.8rem, 3.8vw, 3.2rem);
      font-weight: 700; letter-spacing: 0.18em;
      padding: 0.6rem 2.2rem; border-radius: 4px;
      background: rgba(8, 10, 16, 0.82);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--line-light);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
    }
    .mod-vid { color: #ffffff; border-color: var(--line-gold); }
    .mod-imu { color: #ffffff; border-color: rgba(56, 189, 248, 0.5); }
    .mod-plus { font-family: var(--font-display); font-size: 2.2rem; font-weight: 600; color: var(--accent-gold); text-shadow: var(--text-shadow-deep); }
    .mod-reveal { display: flex; flex-direction: column; align-items: center; }

    .features-phase {
      position: absolute; inset: 0;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center; text-align: center;
      opacity: 0; transition: opacity 0.4s var(--ease-cinematic);
    }
    .feat-center {
      display: flex; flex-direction: column; align-items: center; z-index: 10;
      background: rgba(6, 8, 12, 0.65);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      padding: 1.5rem 3rem; border-radius: 8px; border: 1px solid var(--line-subtle);
    }

    .anno-tags { position: absolute; inset: 0; pointer-events: none; }
    .anno-tag {
      position: absolute;
      font-family: var(--font-mono);
      font-size: clamp(0.78rem, 1vw, 0.92rem);
      font-weight: 500; letter-spacing: 0.14em; color: #ffffff;
      background: rgba(8, 10, 16, 0.88);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      padding: 0.45rem 1.1rem; border-radius: 4px;
      border: 1px solid var(--line-light);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
      text-shadow: var(--text-shadow-deep); opacity: 0;
      transition: opacity 0.3s ease, transform 0.3s ease;
    }

    .tag-al { top: 22%; left: 16%; border-left: 3px solid var(--accent-gold); }
    .tag-ar { top: 32%; right: 16%; border-right: 3px solid var(--accent-gold); }
    .tag-kl { top: 46%; left: 14%; border-left: 3px solid var(--accent-gold); }
    .tag-kr { top: 56%; right: 14%; border-right: 3px solid var(--accent-gold); }
    .tag-sw { bottom: 24%; left: 22%; border-left: 3px solid #ffffff; }
    .tag-acc { bottom: 18%; right: 22%; border-right: 3px solid var(--accent-blue); }
    .tag-gx { top: 15%; right: 30%; border-top: 3px solid var(--accent-blue); }
    .tag-gz { bottom: 12%; left: 32%; border-bottom: 3px solid var(--accent-blue); }

    .sync-phase {
      position: absolute; top: 50%; left: 50%;
      transform: translate(-50%, -50%); width: 100%; max-width: 900px;
      display: flex; flex-direction: column; align-items: center;
      transition: opacity 0.4s var(--ease-cinematic);
    }
    .sync-track-duo { width: 100%; display: flex; flex-direction: column; gap: 1.2rem; margin-bottom: 2.2rem; }
    .sync-bar-wrap { display: flex; align-items: center; gap: 1.5rem; }
    .sync-label { font-family: var(--font-mono); font-size: 0.82rem; font-weight: 600; letter-spacing: 0.2em; color: var(--text-secondary); width: 80px; text-align: right; }
    .sync-track { flex: 1; height: 12px; background: rgba(255, 255, 255, 0.08); border-radius: 6px; overflow: hidden; position: relative; border: 1px solid var(--line-subtle); }
    .sync-pulse { position: absolute; top: 0; bottom: 0; width: 35%; border-radius: 6px; }
    .vid-pulse { left: 30%; background: linear-gradient(90deg, transparent, var(--accent-gold), transparent); }
    .imu-pulse { left: 30%; background: linear-gradient(90deg, transparent, var(--accent-blue), transparent); transform: translateX(-40px); }

    .sync-badge { display: flex; flex-direction: column; align-items: center; }

    .detect-phase {
      position: absolute; inset: 0;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      opacity: 0; transition: opacity 0.4s var(--ease-cinematic); padding: 0 2rem;
    }

    .timeline-visual-box {
      width: 100%; max-width: 960px;
      background: rgba(8, 10, 16, 0.85); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--line-light); border-radius: 8px; padding: 1.5rem 2rem;
      margin-bottom: 2rem; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
    }

    .tl-title-row { display: flex; justify-content: space-between; font-family: var(--font-mono); font-size: 0.75rem; letter-spacing: 0.18em; color: var(--text-muted); margin-bottom: 1rem; }
    .tl-mode-label { color: var(--accent-gold); font-weight: 600; }
    .single-timeline { width: 100%; height: 28px; background: rgba(255, 255, 255, 0.06); border-radius: 4px; position: relative; overflow: hidden; border: 1px solid var(--line-subtle); }
    .tl-cursor { position: absolute; top: 0; bottom: 0; width: 3px; background: #ffffff; box-shadow: 0 0 12px #ffffff; left: 12%; z-index: 5; }
    .tl-highlight { position: absolute; top: 0; bottom: 0; left: 45%; width: 27%; background: rgba(245, 158, 11, 0.35); border-left: 2px solid var(--accent-alert); border-right: 2px solid var(--accent-alert); opacity: 0; display: flex; justify-content: space-between; align-items: center; padding: 0 0.5rem; }
    .tl-stamp { font-family: var(--font-mono); font-size: 0.65rem; font-weight: 600; color: #ffffff; text-shadow: var(--text-shadow-deep); }

    .detect-bottom-split { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; width: 100%; max-width: 960px; }
    .detect-callout-panel, .confidence-panel {
      background: rgba(8, 10, 16, 0.85); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--line-light); border-radius: 8px; padding: 1.8rem 2.2rem; text-align: left;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
    }
    .detect-callout-panel { border-left: 4px solid var(--accent-alert); }
    .episode-pill { display: inline-block; font-family: var(--font-mono); font-size: 0.68rem; font-weight: 600; letter-spacing: 0.2em; color: var(--accent-alert); background: rgba(245, 158, 11, 0.15); padding: 0.3rem 0.8rem; border-radius: 4px; margin-bottom: 0.8rem; }
    .alert-heading { font-size: 1.5rem; margin-top: 0; color: #ffffff; }
    .episode-interval { font-family: var(--font-mono); font-size: 1.1rem; font-weight: 600; color: var(--accent-gold); margin: 0.6rem 0; }
    .episode-disclaimer { font-size: 0.82rem; color: var(--text-muted); line-height: 1.4; }

    .confidence-panel { text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .conf-heading { font-family: var(--font-display); font-size: 1.2rem; font-weight: 700; letter-spacing: 0.18em; color: #ffffff; margin-top: 0.4rem; }
    .conf-sub { font-size: 0.82rem; color: var(--text-muted); margin-top: 0.4rem; }

    .evidence-bedrock-stage { display: flex; flex-direction: column; align-items: center; gap: 1.5rem; width: 100%; max-width: 840px; }
    .evidence-panel, .bedrock-panel {
      width: 100%; background: rgba(8, 10, 16, 0.88); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--line-light); border-radius: 8px; padding: 1.8rem 2.4rem; text-align: left;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
    }
    .panel-header { display: flex; align-items: center; gap: 0.6rem; font-family: var(--font-mono); font-size: 0.75rem; font-weight: 600; letter-spacing: 0.2em; color: var(--accent-gold); margin-bottom: 1rem; }
    .header-indicator { width: 8px; height: 8px; background: var(--accent-gold); border-radius: 50%; box-shadow: 0 0 10px var(--accent-gold); }
    .console-body { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; font-family: var(--font-mono); font-size: 0.92rem; }
    .con-key { color: var(--text-muted); }
    .con-val { color: #ffffff; font-weight: 600; }
    .synthesis-arrow { font-size: 1.6rem; color: var(--accent-gold); text-shadow: 0 0 12px var(--accent-gold); }

    .bedrock-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid var(--line-subtle); padding-bottom: 0.8rem; }
    .bedrock-title { font-family: var(--font-display); font-size: 1.2rem; font-weight: 700; letter-spacing: 0.18em; color: var(--accent-blue); text-transform: uppercase; }
    .bedrock-mantra { font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); letter-spacing: 0.14em; }
    .bedrock-quote { font-family: var(--font-body); font-size: 1.15rem; font-weight: 400; font-style: italic; color: #ffffff; line-height: 1.6; border-left: 3px solid var(--accent-blue); padding-left: 1.2rem; margin: 1rem 0; }
    .bedrock-note { font-size: 0.8rem; color: var(--text-muted); }

    .kinetic-words-group { display: flex; flex-direction: column; align-items: center; gap: 0.6rem; margin-bottom: 3rem; }
    .k-word { font-family: var(--font-display); font-size: clamp(2.8rem, 6.5vw, 6rem); font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; color: #ffffff; text-shadow: var(--text-shadow-deep); }

    .credits-box { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; background: rgba(8, 10, 16, 0.8); backdrop-filter: blur(12px); padding: 1.5rem 3rem; border-radius: 8px; border: 1px solid var(--line-subtle); }
    .credits-brand { font-family: var(--font-display); font-size: 1.4rem; font-weight: 700; letter-spacing: 0.22em; color: var(--accent-gold); }
    .credits-lead { font-family: var(--font-body); font-size: 0.85rem; color: var(--text-muted); }
    .credits-names { font-family: var(--font-display); font-size: 1.15rem; font-weight: 600; color: #ffffff; letter-spacing: 0.1em; }
    .credits-year { font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); }

    .blackout-curtain { position: absolute; inset: 0; background: #060709; opacity: 0; pointer-events: none; z-index: 100; transition: opacity 0.5s ease; }
  </style>
</head>
<body>
  <div id="viewport-stage">
    <div class="video-container">
      <video id="bg-video" muted playsinline preload="auto" disablepictureinpicture>
        <source src="/app/static/newfinal.mp4" type="video/mp4" />
      </video>
      <div class="vignette-layer"></div>
    </div>

    <header class="hud-header">
      <div class="brand-container">
        <div class="brand-title">NEUROGAIT</div>
        <div class="brand-meta">MULTIMODAL OBSERVER</div>
      </div>
      <div class="hud-status">
        <span class="pulse-dot"></span>
        <span class="hud-mono" id="hud-status-text">VIDEO SCRUB ACTIVE</span>
        <span class="hud-separator">|</span>
        <span class="hud-mono" id="hud-timecode">0.00s</span>
      </div>
    </header>

    <footer class="hud-footer">
      <div class="hud-coord">
        <span class="hud-label">CHAPTER PROGRESS</span>
        <span class="hud-mono" id="hud-progress">1 / 5 // HERO</span>
      </div>
      <div class="hud-legend">
        <span class="legend-item"><span class="legend-box video-accent"></span> VIDEO POSE</span>
        <span class="legend-item"><span class="legend-box imu-accent"></span> IMU 6-AXIS</span>
        <span class="legend-item"><span class="legend-box fused-accent"></span> FUSED VECTOR</span>
      </div>
    </footer>

    <main class="narrative-stage">
      <!-- BEAT 1 -->
      <section class="beat beat-hero" id="beat-1">
        <div class="beat-inner hero-right-content">
          <div class="hero-chip">Multimodal movement assessment</div>
          <h1 class="hero-title">NEUROGAIT</h1>
          <p class="hero-statement">Movement is information.</p>
          <div class="scroll-hint">
            <span class="scroll-arrow">↓</span>
            <span class="scroll-text">SCROLL TO OBSERVE</span>
          </div>
        </div>
      </section>

      <!-- BEAT 2 -->
      <section class="beat" id="beat-2">
        <div class="beat-inner center-content">
          <div class="modalities-phase" id="b2-modalities">
            <div class="mod-pill-group">
              <span class="mod-pill mod-vid">VIDEO</span>
              <span class="mod-plus">+</span>
              <span class="mod-pill mod-imu">IMU</span>
            </div>
            <div class="mod-reveal">
              <div class="massive-number gold-num">02</div>
              <h2 class="beat-heading">MODALITIES</h2>
              <p class="beat-sub">Two synchronized views of the same movement.</p>
            </div>
          </div>

          <div class="features-phase" id="b2-features">
            <div class="feat-center">
              <div class="massive-number white-num">08</div>
              <h2 class="beat-heading">FUSED FEATURES</h2>
              <p class="beat-sub">Synchronized eight-dimensional movement state vector</p>
            </div>
            <div class="anno-tags">
              <div class="anno-tag tag-al" id="tag-1">left_ankle_velocity</div>
              <div class="anno-tag tag-ar" id="tag-2">right_ankle_velocity</div>
              <div class="anno-tag tag-kl" id="tag-3">left_knee_angle</div>
              <div class="anno-tag tag-kr" id="tag-4">right_knee_angle</div>
              <div class="anno-tag tag-sw" id="tag-5">stride_width</div>
              <div class="anno-tag tag-acc" id="tag-6">accel_rms</div>
              <div class="anno-tag tag-gx" id="tag-7">gyro_x_var</div>
              <div class="anno-tag tag-gz" id="tag-8">gyro_z_var</div>
            </div>
          </div>
        </div>
      </section>

      <!-- BEAT 3 -->
      <section class="beat" id="beat-3">
        <div class="beat-inner center-content">
          <div class="sync-phase" id="b3-sync">
            <div class="sync-track-duo">
              <div class="sync-bar-wrap">
                <span class="sync-label">VIDEO</span>
                <div class="sync-track"><div class="sync-pulse vid-pulse"></div></div>
              </div>
              <div class="sync-bar-wrap">
                <span class="sync-label">IMU</span>
                <div class="sync-track"><div class="sync-pulse imu-pulse" id="b3-imu-pulse"></div></div>
              </div>
            </div>
            <div class="sync-badge" id="b3-sync-badge">
              <div class="massive-number gold-num">±0.1s</div>
              <h2 class="beat-heading">TEMPORAL ALIGNMENT</h2>
            </div>
          </div>

          <div class="detect-phase" id="b3-detect">
            <div class="timeline-visual-box">
              <div class="tl-title-row">
                <span class="tl-mode-label">MOVEMENT TIMELINE</span>
                <span class="tl-window-label">EPISODE WINDOW: 05.2s — 06.8s</span>
              </div>
              <div class="single-timeline">
                <div class="tl-cursor" id="b3-cursor"></div>
                <div class="tl-highlight" id="b3-highlight">
                  <span class="tl-stamp">05.2s</span>
                  <span class="tl-stamp">06.8s</span>
                </div>
              </div>
            </div>

            <div class="detect-bottom-split">
              <div class="detect-callout-panel" id="b3-callout-panel">
                <div class="episode-pill">MODEL-DETECTED EPISODE</div>
                <h2 class="beat-heading alert-heading">POSSIBLE FoG EPISODE</h2>
                <div class="episode-interval">05.2s — 06.8s</div>
                <p class="episode-disclaimer">Non-diagnostic assessment derived from continuous gait window classification.</p>
              </div>
              <div class="confidence-panel" id="b3-conf-panel">
                <div class="massive-number gold-num" id="b3-conf-num">92%</div>
                <div class="conf-heading">CONFIDENCE</div>
                <div class="conf-sub">Mean class-1 probability across episode windows</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- BEAT 4 -->
      <section class="beat" id="beat-4">
        <div class="beat-inner center-content">
          <div class="evidence-bedrock-stage">
            <div class="evidence-panel" id="b4-evidence-panel">
              <div class="panel-header">
                <span class="header-indicator"></span>
                <span class="header-text">STRUCTURED EVIDENCE</span>
              </div>
              <div class="console-body">
                <div class="con-line"><span class="con-key">type:</span> <span class="con-val">FoG</span></div>
                <div class="con-line"><span class="con-key">confidence:</span> <span class="con-val">0.92</span></div>
                <div class="con-line"><span class="con-key">interval:</span> <span class="con-val">05.2s — 06.8s</span></div>
                <div class="con-line"><span class="con-key">primary_cue:</span> <span class="con-val">left_ankle_velocity</span></div>
              </div>
            </div>
            <div class="synthesis-arrow" id="b4-arrow">↓</div>
            <div class="bedrock-panel" id="b4-bedrock-panel">
              <div class="bedrock-header">
                <h2 class="bedrock-title">AMAZON BEDROCK</h2>
                <div class="bedrock-mantra">ML detects. AI explains.</div>
              </div>
              <blockquote class="bedrock-quote">
                “A possible freezing episode was detected during this interval (05.2s — 06.8s), primarily associated with altered left ankle movement.”
              </blockquote>
              <div class="bedrock-note">Explaining structured machine evidence. Grounded explanation without diagnostic claims.</div>
            </div>
          </div>
        </div>
      </section>

      <!-- BEAT 5 -->
      <section class="beat" id="beat-5">
        <div class="beat-inner center-content">
          <div class="kinetic-words-group">
            <div class="k-word" id="b5-word-1">Movement.</div>
            <div class="k-word" id="b5-word-2">Measured.</div>
            <div class="k-word" id="b5-word-3">Explained.</div>
          </div>
          <div class="credits-box" id="b5-credits">
            <h2 class="credits-brand">NEUROGAIT</h2>
            <p class="credits-lead">Made with love by</p>
            <div class="credits-names">Devika Anup × Shriram</div>
            <div class="credits-year">2026</div>
          </div>
        </div>
      </section>
    </main>

    <div class="blackout-curtain" id="blackout-curtain"></div>
  </div>

  <script>
    const clamp = (val, min = 0, max = 1) => Math.min(Math.max(val, min), max);
    const lerp = (start, end, amt) => (1 - amt) * start + amt * end;
    const smoothstep = (min, max, value) => {
      const x = Math.max(0, Math.min(1, (value - min) / (max - min)));
      return x * x * (3 - 2 * x);
    };

    const dom = {
      stage: document.getElementById('viewport-stage'),
      video: document.getElementById('bg-video'),
      hudProgress: document.getElementById('hud-progress'),
      hudTimecode: document.getElementById('hud-timecode'),
      blackout: document.getElementById('blackout-curtain'),

      b1: document.getElementById('beat-1'),
      b2: document.getElementById('beat-2'),
      b3: document.getElementById('beat-3'),
      b4: document.getElementById('beat-4'),
      b5: document.getElementById('beat-5'),

      b2Modalities: document.getElementById('b2-modalities'),
      b2Features: document.getElementById('b2-features'),
      b2Tags: [
        document.getElementById('tag-1'), document.getElementById('tag-2'),
        document.getElementById('tag-3'), document.getElementById('tag-4'),
        document.getElementById('tag-5'), document.getElementById('tag-6'),
        document.getElementById('tag-7'), document.getElementById('tag-8'),
      ],

      b3Sync: document.getElementById('b3-sync'),
      b3ImuPulse: document.getElementById('b3-imu-pulse'),
      b3SyncBadge: document.getElementById('b3-sync-badge'),
      b3Detect: document.getElementById('b3-detect'),
      b3Cursor: document.getElementById('b3-cursor'),
      b3Highlight: document.getElementById('b3-highlight'),
      b3CalloutPanel: document.getElementById('b3-callout-panel'),
      b3ConfPanel: document.getElementById('b3-conf-panel'),
      b3ConfNum: document.getElementById('b3-conf-num'),

      b4EvidencePanel: document.getElementById('b4-evidence-panel'),
      b4BedrockPanel: document.getElementById('b4-bedrock-panel'),
      b4Arrow: document.getElementById('b4-arrow'),

      b5Words: [
        document.getElementById('b5-word-1'),
        document.getElementById('b5-word-2'),
        document.getElementById('b5-word-3'),
      ],
      b5Credits: document.getElementById('b5-credits'),
    };

    let targetProgress = 0;
    let currentProgress = 0;

    function updateVideoTime(p) {
      if (!dom.video) return;
      const dur = dom.video.duration;
      if (!dur || isNaN(dur) || dur <= 0) return;
      const maxTime = Math.max(0, dur - 0.04);
      const targetTime = clamp(p * maxTime, 0, maxTime);
      if (dom.hudTimecode) dom.hudTimecode.textContent = targetTime.toFixed(2) + 's';
      if (Math.abs(dom.video.currentTime - targetTime) > 0.02) {
        dom.video.currentTime = targetTime;
      }
    }

    function setBeatVisibility(el, visible, opacity = 1, translateY = 0, scale = 1) {
      if (!el) return;
      if (visible && opacity > 0.005) {
        el.style.visibility = 'visible';
        el.style.opacity = opacity.toFixed(3);
        el.style.transform = `translate3d(0, ${translateY.toFixed(2)}px, 0) scale(${scale.toFixed(3)})`;
      } else {
        el.style.visibility = 'hidden';
        el.style.opacity = '0';
      }
    }

    function updateBeats(p) {
      if (dom.hudProgress) {
        if (p < 0.18) dom.hudProgress.textContent = '1 / 5 // HERO';
        else if (p < 0.42) dom.hudProgress.textContent = '2 / 5 // MODALITIES & FEATURES';
        else if (p < 0.68) dom.hudProgress.textContent = '3 / 5 // SYNC & DETECTION';
        else if (p < 0.88) dom.hudProgress.textContent = '4 / 5 // EVIDENCE & BEDROCK';
        else dom.hudProgress.textContent = '5 / 5 // SYNTHESIS';
      }

      // BEAT 1
      if (p <= 0.190) {
        const fadeOut = 1 - smoothstep(0.110, 0.180, p);
        const shiftY = lerp(0, -30, smoothstep(0.040, 0.180, p));
        setBeatVisibility(dom.b1, true, fadeOut, shiftY);
      } else {
        setBeatVisibility(dom.b1, false);
      }

      // BEAT 2
      if (p >= 0.170 && p <= 0.430) {
        const enter = smoothstep(0.170, 0.200, p);
        const exit = 1 - smoothstep(0.400, 0.430, p);
        setBeatVisibility(dom.b2, true, Math.min(enter, exit));

        const modFadeOut = 1 - smoothstep(0.270, 0.305, p);
        if (dom.b2Modalities) {
          dom.b2Modalities.style.opacity = modFadeOut.toFixed(2);
          dom.b2Modalities.style.transform = `translate(-50%, -50%) scale(${lerp(1, 0.94, 1 - modFadeOut)})`;
        }

        const featFadeIn = smoothstep(0.290, 0.325, p);
        if (dom.b2Features) dom.b2Features.style.opacity = featFadeIn.toFixed(2);

        dom.b2Tags.forEach((tag, idx) => {
          const tagStart = 0.300 + idx * 0.010;
          const tagAlpha = smoothstep(tagStart, tagStart + 0.015, p);
          if (tag) {
            tag.style.opacity = tagAlpha.toFixed(2);
            tag.style.transform = `translateY(${lerp(10, 0, tagAlpha)}px)`;
          }
        });
      } else {
        setBeatVisibility(dom.b2, false);
      }

      // BEAT 3
      if (p >= 0.410 && p <= 0.690) {
        const enter = smoothstep(0.410, 0.440, p);
        const exit = 1 - smoothstep(0.660, 0.690, p);
        setBeatVisibility(dom.b3, true, Math.min(enter, exit));

        const syncFadeOut = 1 - smoothstep(0.510, 0.545, p);
        if (dom.b3Sync) {
          dom.b3Sync.style.opacity = syncFadeOut.toFixed(2);
          const alignP = smoothstep(0.420, 0.485, p);
          if (dom.b3ImuPulse) dom.b3ImuPulse.style.transform = `translateX(${lerp(-40, 0, alignP)}px)`;
          const badgeAlpha = smoothstep(0.465, 0.495, p);
          if (dom.b3SyncBadge) {
            dom.b3SyncBadge.style.opacity = badgeAlpha.toFixed(2);
            dom.b3SyncBadge.style.transform = `translateY(${lerp(14, 0, badgeAlpha)}px)`;
          }
        }

        const detectFadeIn = smoothstep(0.530, 0.565, p);
        if (dom.b3Detect) {
          dom.b3Detect.style.opacity = detectFadeIn.toFixed(2);
          const curP = smoothstep(0.535, 0.640, p);
          const curPos = lerp(12, 84, curP);
          if (dom.b3Cursor) dom.b3Cursor.style.left = curPos + '%';

          const highlightAlpha = smoothstep(0.560, 0.590, p);
          if (dom.b3Highlight) dom.b3Highlight.style.opacity = highlightAlpha.toFixed(2);

          const panelAlpha = smoothstep(0.575, 0.615, p);
          if (dom.b3CalloutPanel) {
            dom.b3CalloutPanel.style.opacity = panelAlpha.toFixed(2);
            dom.b3CalloutPanel.style.transform = `translateY(${lerp(15, 0, panelAlpha)}px)`;
          }
          if (dom.b3ConfPanel) {
            dom.b3ConfPanel.style.opacity = panelAlpha.toFixed(2);
            dom.b3ConfPanel.style.transform = `translateY(${lerp(15, 0, panelAlpha)}px)`;
          }
          if (dom.b3ConfNum) {
            dom.b3ConfNum.textContent = Math.round(92 * smoothstep(0.580, 0.630, p)) + '%';
          }
        }
      } else {
        setBeatVisibility(dom.b3, false);
      }

      // BEAT 4
      if (p >= 0.670 && p <= 0.890) {
        const enter = smoothstep(0.670, 0.700, p);
        const exit = 1 - smoothstep(0.860, 0.890, p);
        setBeatVisibility(dom.b4, true, Math.min(enter, exit));

        const evAlpha = smoothstep(0.685, 0.730, p);
        if (dom.b4EvidencePanel) {
          dom.b4EvidencePanel.style.opacity = evAlpha.toFixed(2);
          dom.b4EvidencePanel.style.transform = `translateY(${lerp(18, 0, evAlpha)}px)`;
        }
        if (dom.b4Arrow) dom.b4Arrow.style.opacity = smoothstep(0.725, 0.760, p).toFixed(2);
        const bedAlpha = smoothstep(0.750, 0.800, p);
        if (dom.b4BedrockPanel) {
          dom.b4BedrockPanel.style.opacity = bedAlpha.toFixed(2);
          dom.b4BedrockPanel.style.transform = `translateY(${lerp(18, 0, bedAlpha)}px)`;
        }
      } else {
        setBeatVisibility(dom.b4, false);
      }

      // BEAT 5 & ENDING
      if (p >= 0.870) {
        setBeatVisibility(dom.b5, true, 1);
        const w1P = smoothstep(0.885, 0.915, p);
        const w2P = smoothstep(0.910, 0.940, p);
        const w3P = smoothstep(0.935, 0.965, p);

        if (dom.b5Words[0]) { dom.b5Words[0].style.opacity = w1P.toFixed(2); dom.b5Words[0].style.transform = `translateY(${lerp(20, 0, w1P)}px)`; }
        if (dom.b5Words[1]) { dom.b5Words[1].style.opacity = w2P.toFixed(2); dom.b5Words[1].style.transform = `translateY(${lerp(20, 0, w2P)}px)`; }
        if (dom.b5Words[2]) { dom.b5Words[2].style.opacity = w3P.toFixed(2); dom.b5Words[2].style.transform = `translateY(${lerp(20, 0, w3P)}px)`; }

        const credP = smoothstep(0.960, 0.988, p);
        if (dom.b5Credits) {
          dom.b5Credits.style.opacity = credP.toFixed(2);
          dom.b5Credits.style.transform = `translateY(${lerp(18, 0, credP)}px)`;
        }
        if (dom.blackout) {
          dom.blackout.style.opacity = smoothstep(0.988, 1.000, p).toFixed(2);
        }
      } else {
        setBeatVisibility(dom.b5, false);
        if (dom.blackout) dom.blackout.style.opacity = '0';
      }
    }

    function onFrame() {
      currentProgress = lerp(currentProgress, targetProgress, 0.095);
      if (Math.abs(targetProgress - currentProgress) < 0.0001) {
        currentProgress = targetProgress;
      }
      updateVideoTime(currentProgress);
      updateBeats(currentProgress);

      requestAnimationFrame(onFrame);
    }

    window.onScroll = function() {
      try {
        const parentWin = window.parent || window;
        const parentDoc = parentWin.document || document;
        const track = parentDoc.getElementById('neurogait-scroll-track');
        if (!track) return;

        const mainEl = parentDoc.querySelector('.stMain');
        let scrolled = 0;
        let trackHeight = track.offsetHeight - parentWin.innerHeight;

        if (mainEl && mainEl.scrollTop > 0) {
          scrolled = mainEl.scrollTop;
        } else {
          const rect = track.getBoundingClientRect();
          scrolled = -rect.top;
        }

        if (trackHeight > 0) {
          targetProgress = clamp(scrolled / trackHeight);

          if (scrolled >= trackHeight + 50) {
            dom.stage.style.opacity = '0';
            dom.stage.style.pointerEvents = 'none';
          } else {
            dom.stage.style.opacity = '1';
            dom.stage.style.pointerEvents = 'none';
          }
        }
      } catch (err) {
        console.error("Scroll sync error:", err);
      }
    };

    function init() {
      if (dom.video) {
        dom.video.pause();
        dom.video.currentTime = 0;
      }

      const parentWin = window.parent || window;
      const parentDoc = parentWin.document || document;
      const mainEl = parentDoc.querySelector('.stMain');

      parentWin.addEventListener('scroll', window.onScroll, { passive: true });
      parentWin.addEventListener('resize', window.onScroll);
      if (mainEl) {
        mainEl.addEventListener('scroll', window.onScroll, { passive: true });
      }

      window.onScroll();
      currentProgress = targetProgress;

      requestAnimationFrame(onFrame);
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  </script>
</body>
</html>
    """

    components.html(component_html, height=0, scrolling=False)
