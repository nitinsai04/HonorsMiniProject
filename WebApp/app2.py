"""
Gesture Presentation Hub — v2
Streamlit web app: upload PDFs → convert to slides → launch gesture presentation.

Run from project root:
    streamlit run WebApp/app2.py
"""

import os
import sys
import json
import shutil
import subprocess

import streamlit as st
try:
    import pymupdf as fitz
except ImportError:
    import fitz

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gesture Presentation Hub",
    page_icon="👋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE        = os.path.dirname(os.path.abspath(__file__))
SLIDES_DIR  = os.path.join(HERE, "temp_slides")
CONFIG_PATH = os.path.join(SLIDES_DIR, "config.json")
ENGINE_SCRIPT = os.path.join(HERE, "run_engine.py")

# ── CSS (consistent with existing app.py dark theme) ─────────────────────────
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 860px;
    }
    h1 { color: #f8fafc; font-weight: 800; margin-bottom: 0.3rem; }
    h3 { color: #e2e8f0; }
    .card {
        padding: 1.6rem 2rem;
        border-radius: 12px;
        background: #1e293b;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.4);
        margin-bottom: 1.6rem;
        border: 1px solid #334155;
    }
    .stButton > button {
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
        font-size: 15px;
        background-color: #3b82f6;
        color: white;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #2563eb;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59,130,246,0.4);
    }
    .status-pill {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .running  { background: #14532d; color: #86efac; }
    .stopped  { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }
    .ready    { background: #1e3a5f; color: #93c5fd; }
    .sidebar-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prep_slides_dir():
    if os.path.exists(SLIDES_DIR):
        shutil.rmtree(SLIDES_DIR)
    os.makedirs(SLIDES_DIR)


def _convert_pdfs(uploaded_files) -> list[str]:
    """Convert all uploaded PDFs to numbered PNGs; return sorted path list."""
    _prep_slides_dir()
    paths = []
    slide_num = 1

    for uf in uploaded_files:
        # Save upload to disk temporarily
        tmp = os.path.join(SLIDES_DIR, f"_tmp_{uf.name}")
        with open(tmp, "wb") as f:
            f.write(uf.getbuffer())

        doc = fitz.open(tmp)
        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            pix  = page.get_pixmap(dpi=150)
            out  = os.path.join(SLIDES_DIR, f"slide_{slide_num:04d}.png")
            pix.save(out)
            paths.append(out)
            slide_num += 1
        doc.close()
        os.remove(tmp)

    return sorted(paths)


def _write_config(paths: list[str], settings: dict) -> str:
    os.makedirs(SLIDES_DIR, exist_ok=True)
    config = {"paths": paths, "settings": settings}
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)
    return CONFIG_PATH


def _proc_running() -> bool:
    proc = st.session_state.get("proc")
    return proc is not None and proc.poll() is None


# ── Sidebar: settings + gesture map ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")

    spotlight_radius   = st.slider("Spotlight Radius",   50,  400, 150)
    dim_opacity_pct    = st.slider("Dim Opacity (%)",    30,   95,  70)
    gesture_threshold  = st.slider("Gesture Threshold", 100,  500, 300)
    dimmed_bright_pct  = st.slider("Dimmed Brightness (%)", 10, 90,  30)
    hardware_dim       = st.checkbox("Hardware Brightness (macOS)", value=True)

    settings = {
        "spotlight_radius":  spotlight_radius,
        "dim_opacity":       dim_opacity_pct  / 100,
        "gesture_threshold": gesture_threshold,
        "dimmed_brightness": dimmed_bright_pct / 100,
        "hardware_dim":      hardware_dim,
    }

    st.markdown("---")
    st.markdown("## 🤌 Gesture Map")

    gestures = [
        ("Thumb + Index",   "Previous slide"),
        ("Thumb + Middle",  "Next slide"),
        ("Thumb + Ring",    "Spotlight on/off"),
        ("Index + Middle",  "Pointer"),
        ("Index only",      "Draw / annotate"),
        ("I + M + R up",    "Erase last stroke"),
    ]
    for g, a in gestures:
        st.markdown(f"**`{g}`** → {a}")

    st.markdown("---")
    st.markdown("## ⌨️ Keyboard")
    st.markdown(
        "`s` spotlight &nbsp;·&nbsp; `h` hw-brightness  \n"
        "`+`/`-` radius &nbsp;·&nbsp; `[`/`]` dim  \n"
        "`q` quit",
        unsafe_allow_html=True,
    )


# ── Main: header ──────────────────────────────────────────────────────────────
st.markdown("<h1>👋 Gesture Presentation Hub</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#94a3b8;font-size:1.05rem;margin-bottom:1.8rem;'>"
    "Upload PDFs, prepare slides, then launch the gesture-controlled presentation "
    "with spotlight and drawing support.</p>",
    unsafe_allow_html=True,
)

# ── Step 1: Upload ────────────────────────────────────────────────────────────
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("### 📄 Step 1 — Upload PDFs")
uploaded = st.file_uploader(
    "Select one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True,
    help="Each PDF's pages become individual slides in order.",
)

if uploaded:
    total_hint = ", ".join(f"**{u.name}**" for u in uploaded)
    st.markdown(
        f"<p style='color:#94a3b8;font-size:0.9rem;margin-top:0.5rem;'>"
        f"{len(uploaded)} file{'s' if len(uploaded)>1 else ''} selected: {total_hint}</p>",
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

# ── Step 2: Process ───────────────────────────────────────────────────────────
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("### ⚙️ Step 2 — Prepare Slides")

if not uploaded:
    st.markdown(
        "<p style='color:#64748b;'>Upload PDFs above to enable slide preparation.</p>",
        unsafe_allow_html=True,
    )
else:
    if st.button("Process & Load Slides", use_container_width=True):
        with st.spinner("Converting PDF pages to slides…"):
            paths = _convert_pdfs(uploaded)
        if paths:
            st.session_state["slide_paths"] = paths
            st.session_state["slides_ready"] = True
            st.success(f"{len(paths)} slide{'s' if len(paths)>1 else ''} ready.")
        else:
            st.session_state["slides_ready"] = False

    if st.session_state.get("slides_ready"):
        n = len(st.session_state.get("slide_paths", []))
        st.markdown(
            f"<span class='status-pill ready'>✓ {n} slides loaded</span>",
            unsafe_allow_html=True,
        )

st.markdown("</div>", unsafe_allow_html=True)

# ── Step 3: Launch ────────────────────────────────────────────────────────────
if st.session_state.get("slides_ready"):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 🚀 Step 3 — Launch Presentation")
    st.markdown(
        "<p style='color:#94a3b8;font-size:0.9rem;margin-bottom:1.2rem;'>"
        "The gesture window opens on your desktop. Use hand gestures or keyboard shortcuts.</p>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🟢 Start Presentation", use_container_width=True):
            if _proc_running():
                st.warning("Presentation is already running.")
            else:
                cfg = _write_config(
                    st.session_state["slide_paths"], settings
                )
                proc = subprocess.Popen(
                    [sys.executable, ENGINE_SCRIPT, cfg],
                    cwd=os.path.dirname(HERE),   # project root as cwd
                )
                st.session_state["proc"] = proc
                st.success("Presentation started! Check the desktop window.")

    with col2:
        if st.button("🔴 Stop Presentation", use_container_width=True):
            if _proc_running():
                st.session_state["proc"].terminate()
                st.session_state["proc"] = None
                st.info("Presentation stopped.")
            else:
                st.error("No presentation is currently running.")

    # Status badge
    status_html = (
        "<span class='status-pill running'>● Running</span>"
        if _proc_running()
        else "<span class='status-pill stopped'>○ Stopped</span>"
    )
    st.markdown(
        f"<p style='margin-top:1rem;'>Status: {status_html}</p>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
