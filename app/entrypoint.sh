#!/bin/bash

# Container entrypoint: starts Xvfb, the Android emulator, waits for boot,
# then launches the FastAPI server.
set -euo pipefail

# ── 1. Virtual display ────────────────────────────────────────────────────────
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
echo "[entrypoint] Xvfb started."

# ── 2. Android Emulator ───────────────────────────────────────────────────────
emulator -list-avds
emulator \
    -avd "$EMULATOR_NAME" \
    -port $EMULATOR_PORT \
    -no-audio \
    -no-window \
    -no-boot-anim \
    -writable-system \
    -gpu swiftshader_indirect \
    -no-snapshot \
    & EMULATOR_PID=$!
echo "[entrypoint] Emulator started (PID=$EMULATOR_PID)."

# ── 3. Wait for ADB device ────────────────────────────────────────────────────
echo "[entrypoint] Waiting for ADB device..."
adb wait-for-device

# ── 4. Wait for full boot ─────────────────────────────────────────────────────
echo "[entrypoint] Waiting for boot to complete..."
until [ "$(adb -s "$EMULATOR_SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
    sleep 5
done
echo "[entrypoint] Emulator is ready."

# ── 5. Launch REST API server (replaces shell as PID 1) ───────────────────────
echo "[entrypoint] Starting REST API on port $API_PORT..."
exec uvicorn main:application \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --workers 1
