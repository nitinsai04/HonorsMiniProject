#!/bin/bash
# One-command setup and launch for the Gesture Presentation Web App.
# Usage: bash start_webapp.sh

set -e

echo "Installing dependencies..."
pip install -r WebApp/requirements_webapp.txt

echo ""
echo "Starting Gesture Presentation Hub..."
echo "Open http://localhost:8501 in your browser."
echo ""
python -m streamlit run WebApp/app2.py
