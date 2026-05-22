#!/usr/bin/env bash
# Container entrypoint: starts Xvfb, the Android emulator, waits for boot,
# then launches the FastAPI server.
set -euo pipefail

ADB_BIN="${ADB_PATH:-adb}"
SERIAL="${EMULATOR_SERIAL:-emulator-5554}"
AVD="${EMULATOR_NAME:-test_avd}"
PORT="${API_PORT:-8000}"

# ── 1. Virtual display ────────────────────────────────────────────────────────
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
export DISPLAY=:99
echo "[entrypoint] Xvfb started."

# ── 2. Android Emulator ───────────────────────────────────────────────────────
emulator \
    -avd "${AVD}" \
    -no-audio \
    -no-window \
    -gpu swiftshader_indirect \
    -no-snapshot \
    ${EMULATOR_EXTRA_ARGS:-} &
EMULATOR_PID=$!
echo "[entrypoint] Emulator started (PID=${EMULATOR_PID})."

# ── 3. Wait for ADB device ────────────────────────────────────────────────────
echo "[entrypoint] Waiting for ADB device..."
"${ADB_BIN}" wait-for-device

# ── 4. Wait for full boot ─────────────────────────────────────────────────────
echo "[entrypoint] Waiting for boot to complete..."
until [ "$("${ADB_BIN}" -s "${SERIAL}" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
    sleep 2
done
echo "[entrypoint] Emulator is ready."

# ── 5. Launch REST API server (replaces shell as PID 1) ───────────────────────
echo "[entrypoint] Starting REST API on port ${PORT}..."
exec uvicorn main:application \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers 1
