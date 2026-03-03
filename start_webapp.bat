@echo off
echo Installing dependencies...
pip install -r WebApp\requirements_webapp.txt

echo.
echo Starting Gesture Presentation Hub...
echo Open http://localhost:8501 in your browser.
echo.
python -m streamlit run WebApp\app2.py
