"""
Subprocess wrapper — called by app2.py to launch the presentation engine.
Usage: python WebApp/run_engine.py <path_to_config.json>
"""

import sys
import json
import os

# Resolve project root so presentation_app.engine can be imported
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from presentation_app.engine import run_presentation

if len(sys.argv) < 2:
    print("Usage: run_engine.py <config.json>", file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1]) as f:
    config = json.load(f)

run_presentation(config["paths"], config["settings"])
