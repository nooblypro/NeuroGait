"""NeuroGait Cinematic Landing Page Renderer.

Serves the built `frontend/dist/index.html` cinematic landing webpage as the main
landing page of NeuroGait on `http://localhost:8501/`.
"""

from __future__ import annotations

import glob
import os
import re
import streamlit as st
import streamlit.components.v1 as components


def get_cinematic_landing_html() -> str:
    """Read and inline frontend/dist/index.html with its CSS and JS assets."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dist_dir = os.path.join(project_root, "frontend", "dist")
    html_path = os.path.join(dist_dir, "index.html")

    if not os.path.exists(html_path):
        # Fallback if build is not present
        return "<h1>Cinematic Landing Page Build Pending</h1>"

    css_files = glob.glob(os.path.join(dist_dir, "assets", "*.css"))
    js_files = glob.glob(os.path.join(dist_dir, "assets", "*.js"))

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    css_content = ""
    for css_file in css_files:
        with open(css_file, "r", encoding="utf-8") as f:
            css_content += f.read() + "\n"

    js_content = ""
    for js_file in js_files:
        with open(js_file, "r", encoding="utf-8") as f:
            js_content += f.read() + "\n"

    # Replace relative video asset path with Streamlit static serving path
    html_content = html_content.replace('/newfinal.mp4', '/app/static/newfinal.mp4')

    # Inject inline styles and scripts
    if css_content:
        html_content = re.sub(r'<link[^>]*rel="stylesheet"[^>]*>', f'<style>{css_content}</style>', html_content)

    if js_content:
        html_content = re.sub(r'<script[^>]*src="/assets/[^"]*"[^>]*></script>', f'<script>{js_content}</script>', html_content)

    return html_content


def render_cinematic_landing_page():
    """Render the full cinematic landing webpage as the main page of NeuroGait."""
    html = get_cinematic_landing_html()
    components.html(html, height=1200, scrolling=True)
