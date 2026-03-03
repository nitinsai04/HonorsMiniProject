import streamlit as st
import os
import shutil
import fitz  # PyMuPDF
import subprocess
import sys
import time

# Configurations
st.set_page_config(page_title="Gesture Presentation Hub", layout="wide", page_icon="👋")

RESOURCES_DIR = "Resources"
GESTURE_APP_SCRIPT = "gesture_app.py"

# Custom CSS for modern UI
st.markdown("""
<style>
    .reportview-container {
        background: #0f172a;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 900px;
    }
    h1 {
        font-family: 'Inter', sans-serif;
        color: #f8fafc;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5rem;
        font-weight: 600;
        font-size: 16px;
        background-color: #3b82f6;
        color: white;
        transition: all 0.3s ease;
        border: none;
    }
    .stButton>button:hover {
        background-color: #2563eb;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    .card {
        padding: 2rem;
        border-radius: 12px;
        background: #1e293b;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        margin-bottom: 2rem;
        border: 1px solid #334155;
    }
    .stFileUploader>div>div {
        background: #0f172a;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

def init_resources():
    if os.path.exists(RESOURCES_DIR):
        shutil.rmtree(RESOURCES_DIR)
    os.makedirs(RESOURCES_DIR)

def process_pdf(file_path):
    doc = fitz.open(file_path)
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=150)
        pix.save(os.path.join(RESOURCES_DIR, f"slide{i+1}.png"))
    doc.close()

st.markdown("<h1>👋 Gesture Presentation Hub</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; font-size: 1.1rem; margin-bottom: 2rem;'>Upload a PDF or an Image to start a gesture-controlled presentation with functional spotlight and drawing capabilities.</p>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📄 1. Upload Content")
    uploaded_file = st.file_uploader("Upload Presentation (PDF) or Image (PNG/JPG)", type=["pdf", "png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.subheader("⚙️ 2. Prepare Presentation")
        
        if st.button("Process & Load Slides"):
            with st.spinner("Processing file..."):
                init_resources()
                temp_path = os.path.join(RESOURCES_DIR, "temp" + os.path.splitext(uploaded_file.name)[1])
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    
                if uploaded_file.name.lower().endswith('.pdf'):
                    process_pdf(temp_path)
                    os.remove(temp_path)
                else:
                    os.rename(temp_path, os.path.join(RESOURCES_DIR, "slide1.png"))
                
                st.success("Slides successfully prepared!")
                st.session_state['slides_ready'] = True
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get('slides_ready', False):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🚀 3. Launch Application")
    st.markdown("<p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem;'>The gesture interface will launch in a new local window.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟢 Start Presentation"):
            proc = st.session_state.get('proc')
            if proc is not None and proc.poll() is None:
                st.warning("Presentation is already running.")
            else:
                st.session_state['proc'] = subprocess.Popen([sys.executable, GESTURE_APP_SCRIPT])
                st.success("Presentation started! Check the newly opened window.")
    with col2:
        if st.button("🔴 Stop Presentation"):
            proc = st.session_state.get('proc')
            if proc is not None and proc.poll() is None:
                proc.terminate()
                st.session_state['proc'] = None
                st.info("Presentation stopped successfully.")
            else:
                st.error("Presentation is not currently running.")
    st.markdown("</div>", unsafe_allow_html=True)
