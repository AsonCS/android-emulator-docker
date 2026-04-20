"""
Screen capture and video recording routes.

GET  /screen/image         - real-time PNG screenshot
POST /screen/record/start  - begin rotating screen recording chunks
POST /screen/record/stop   - stop recording and return all pulled chunk paths
"""
import logging
import os
import signal
import subprocess
import threading
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

import adb_runner.runner as adb
import config

router = APIRouter()
logger = logging.getLogger(__name__)

_recording_proc: Optional[subprocess.Popen] = None
_recording_local_dir: Optional[str] = None
_recording_device_id: Optional[str] = None
_recording_device_files: list[str] = []
_recording_thread: Optional[threading.Thread] = None
_recording_stop_event: Optional[threading.Event] = None
_recording_active_session = False
_recording_lock = threading.Lock()

_DEVICE_RECORDING_DIR = "/sdcard/emulator_api_recordings"
_SEGMENT_SECONDS = 120
_DEFAULT_MAX_DURATION_SECONDS = 60000


# -- Response models -----------------------------------------------------------


class RecordStartResponse(BaseModel):
    message: str
    device_dir: str
    segment_seconds: int
    max_duration_seconds: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Recording started",
                "device_dir": "/sdcard/emulator_api_recordings",
                "segment_seconds": 120,
                "max_duration_seconds": 60000,
            }
        }
    )


class RecordStopResponse(BaseModel):
    message: str
    device_id: Optional[str]
    files: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Recording stopped and files pulled",
                "device_id": "emulator-5554",
                "files": [
                    "/tmp/emulator_api/recordings/emulator-5554/chunk_00001.mp4",
                    "/tmp/emulator_api/recordings/emulator-5554/chunk_00002.mp4",
                ],
            }
        }
    )


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "A recording is already in progress"}}
    )


# -- Screenshot ---------------------------------------------------------------


@router.get(
    "/image",
    response_class=Response,
    summary="Capture screenshot",
    responses={
        200: {
            "description": "PNG screenshot of the emulator screen",
            "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}},
        },
        503: {
            "model": ErrorResponse,
            "description": "Emulator unreachable or screenshot failed",
            "content": {
                "application/json": {
                    "example": {"detail": "Screenshot returned empty data"}
                }
            },
        },
    },
)
def screenshot(
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
):
    """
    Capture and return a real-time screenshot of the emulator screen as a PNG image.

    Uses `adb exec-out screencap -p` which returns raw PNG bytes without a shell wrapper.
    """
    try:
        png_bytes = adb.run_binary(
            ["exec-out", "screencap", "-p"],
            timeout=15,
            device_id=device_id,
        )
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if not png_bytes:
        raise HTTPException(status_code=503, detail="Screenshot returned empty data")

    return Response(content=png_bytes, media_type="image/png")


# -- Screen recording ---------------------------------------------------------


def _sanitize_for_path(value: str) -> str:
    sanitized = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
    return sanitized or "unknown_device"


def _extract_selected_device(proc: subprocess.Popen, fallback: Optional[str]) -> Optional[str]:
    args = proc.args
    if isinstance(args, list):
        for index, token in enumerate(args):
            if token == "-s" and index + 1 < len(args):
                return str(args[index + 1])
    return fallback


def _device_chunk_path(index: int) -> str:
    return f"{_DEVICE_RECORDING_DIR}/chunk_{index:05d}.mp4"


def _stop_recording_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return

    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=15)
    except Exception as exc:
        logger.warning("Error stopping recording process: %s", exc)
        proc.kill()
        proc.wait()


def _rotation_worker(target_device: str, max_duration_seconds: int, next_chunk_index: int) -> None:
    global _recording_proc, _recording_device_files

    start_ts = time.monotonic()

    while True:
        with _recording_lock:
            stop_event = _recording_stop_event
        if stop_event is None:
            break

        elapsed = time.monotonic() - start_ts
        remaining = max_duration_seconds - elapsed
        if remaining <= 0:
            break

        wait_time = min(_SEGMENT_SECONDS, remaining)
        if stop_event.wait(wait_time):
            break

        with _recording_lock:
            proc = _recording_proc
        if proc is not None:
            _stop_recording_process(proc)

        if stop_event.is_set():
            break

        device_path = _device_chunk_path(next_chunk_index)
        try:
            proc = adb.start_process(
                ["shell", "screenrecord", device_path],
                device_id=target_device,
            )
        except adb.ADBError as exc:
            logger.error("Failed to start rotated recording chunk %s: %s", next_chunk_index, exc)
            break

        with _recording_lock:
            _recording_proc = proc
            _recording_device_files.append(device_path)
        next_chunk_index += 1

    with _recording_lock:
        proc = _recording_proc
    if proc is not None:
        _stop_recording_process(proc)
    with _recording_lock:
        _recording_proc = None


@router.post(
    "/record/start",
    response_model=RecordStartResponse,
    summary="Start screen recording",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Recording started",
                        "device_dir": "/sdcard/emulator_api_recordings",
                        "segment_seconds": 120,
                        "max_duration_seconds": 60000,
                    }
                }
            }
        },
        409: {
            "model": ErrorResponse,
            "description": "A recording is already in progress",
            "content": {
                "application/json": {
                    "example": {"detail": "A recording is already in progress"}
                }
            },
        },
    },
)
def record_start(
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
    max_duration_seconds: int = Query(
        _DEFAULT_MAX_DURATION_SECONDS,
        ge=1,
        description=(
            "Maximum total recording duration in seconds. "
            "Recording rotates every 120 seconds until this duration or stop."
        ),
    ),
):
    """
    Start an on-device screen recording via `adb shell screenrecord`.

    The recording is saved as rotating 120-second chunks under `/sdcard/emulator_api_recordings`.
    Call `POST /screen/record/stop` to stop and retrieve all chunks.
    Only one recording session can be active at a time.
    """
    global _recording_proc, _recording_local_dir, _recording_device_id
    global _recording_device_files, _recording_thread, _recording_stop_event
    global _recording_active_session

    with _recording_lock:
        if _recording_active_session:
            raise HTTPException(
                status_code=409, detail="A recording is already in progress"
            )

    try:
        adb.run(["shell", "mkdir", "-p", _DEVICE_RECORDING_DIR], device_id=device_id)
        adb.run(
            ["shell", "rm", "-f", f"{_DEVICE_RECORDING_DIR}/*.mp4"],
            device_id=device_id,
        )
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    first_device_path = _device_chunk_path(1)
    try:
        first_proc = adb.start_process(
            ["shell", "screenrecord", first_device_path],
            device_id=device_id,
        )
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    selected_device = _extract_selected_device(first_proc, device_id)
    if not selected_device:
        _stop_recording_process(first_proc)
        raise HTTPException(status_code=503, detail="Unable to resolve selected device")

    local_dir = os.path.join(
        config.TEMP_DIR,
        "recordings",
        _sanitize_for_path(selected_device),
    )
    os.makedirs(local_dir, exist_ok=True)

    with _recording_lock:
        _recording_proc = first_proc
        _recording_local_dir = local_dir
        _recording_device_id = selected_device
        _recording_device_files = [first_device_path]
        _recording_stop_event = threading.Event()
        _recording_active_session = True
        _recording_thread = threading.Thread(
            target=_rotation_worker,
            args=(selected_device, max_duration_seconds, 2),
            daemon=True,
        )
        _recording_thread.start()

    return {
        "message": "Recording started",
        "device_dir": _DEVICE_RECORDING_DIR,
        "segment_seconds": _SEGMENT_SECONDS,
        "max_duration_seconds": max_duration_seconds,
    }


@router.post(
    "/record/stop",
    response_model=RecordStopResponse,
    summary="Stop screen recording and collect chunk paths",
    responses={
        200: {
            "description": "All pulled recording chunk paths",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Recording stopped and files pulled",
                        "device_id": "emulator-5554",
                        "files": [
                            "/tmp/emulator_api/recordings/emulator-5554/chunk_00001.mp4",
                            "/tmp/emulator_api/recordings/emulator-5554/chunk_00002.mp4",
                        ],
                    }
                }
            },
        },
        409: {
            "model": ErrorResponse,
            "description": "No recording is in progress",
            "content": {
                "application/json": {
                    "example": {"detail": "No recording is in progress"}
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "Failed to pull recording chunks from device",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to pull recording: adb: error: ..."
                    }
                }
            },
        },
    },
)
def record_stop(
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, uses the same target from record start when available."
        ),
    ),
):
    """
    Stop the active screen recording, pull all chunk MP4 files, and return local paths.

    Sends `SIGINT` to stop the active `screenrecord` process, then pulls each recorded chunk
    into a local device-specific folder. After pulling, chunk files are deleted from the device.
    """
    global _recording_proc, _recording_local_dir, _recording_device_id
    global _recording_device_files, _recording_thread, _recording_stop_event
    global _recording_active_session

    with _recording_lock:
        if not _recording_active_session:
            raise HTTPException(status_code=409, detail="No recording is in progress")

        stop_event = _recording_stop_event
        proc = _recording_proc
        thread = _recording_thread
        target_device = _recording_device_id or device_id
        local_dir = _recording_local_dir

    if stop_event is not None:
        stop_event.set()

    if proc is not None:
        _stop_recording_process(proc)

    if thread is not None and thread.is_alive():
        thread.join(timeout=20)

    with _recording_lock:
        device_files = list(_recording_device_files)
        target_device = _recording_device_id or target_device or device_id
        local_dir = local_dir or _recording_local_dir

        _recording_proc = None
        _recording_local_dir = None
        _recording_device_id = None
        _recording_device_files = []
        _recording_thread = None
        _recording_stop_event = None
        _recording_active_session = False

    if not target_device:
        raise HTTPException(status_code=503, detail="Unable to resolve recording device")

    local_dir = local_dir or os.path.join(
        config.TEMP_DIR,
        "recordings",
        _sanitize_for_path(target_device),
    )
    os.makedirs(local_dir, exist_ok=True)

    pulled_paths: list[str] = []
    pull_errors: list[str] = []

    for index, device_path in enumerate(device_files, start=1):
        local_path = os.path.join(local_dir, f"chunk_{index:05d}.mp4")
        try:
            adb.run(
                ["pull", device_path, local_path],
                timeout=60,
                device_id=target_device,
            )
            if os.path.exists(local_path):
                pulled_paths.append(local_path)
            else:
                pull_errors.append(f"Failed to pull recording: {device_path}")
        except adb.ADBError as exc:
            pull_errors.append(str(exc))

        try:
            adb.run(["shell", "rm", "-f", device_path], device_id=target_device)
        except adb.ADBError as exc:
            logger.warning("Failed to delete device recording file '%s': %s", device_path, exc)

    if pull_errors and not pulled_paths:
        raise HTTPException(status_code=503, detail="; ".join(pull_errors))

    return {
        "message": "Recording stopped and files pulled",
        "device_id": target_device,
        "files": pulled_paths,
    }
