#!/bin/bash

API_PORT="${API_PORT:-8000}"

# Container entrypoint: starts Xvfb, the Android emulator, waits for boot,
# then launches the FastAPI server.
# set -euo pipefail

# ── 1. Virtual display ────────────────────────────────────────────────────────
# Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
# echo "[entrypoint] Xvfb started."

# ── 2. Launch REST API server (replaces shell as PID 1) ───────────────────────
echo "[entrypoint] Starting REST API on port $API_PORT..."
chmod +x main.py
python3 main.py
