"""
Screen capture and video recording routes.

GET  /screen/image         – real-time PNG screenshot
POST /screen/record/start  – begin screen recording
POST /screen/record/stop   – stop recording and download the MP4
"""
import logging
import os
import signal
import subprocess
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict

import adb_runner.runner as adb
import config

router = APIRouter()
logger = logging.getLogger(__name__)

_DEVICE_RECORDING_PATH = "/sdcard/recording.mp4"
_recording_proc: Optional[subprocess.Popen] = None
_recording_local_path: Optional[str] = None
_recording_device_id: Optional[str] = None


# ── Response models ────────────────────────────────────────────────────────────


class RecordStartResponse(BaseModel):
    message: str
    device_path: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Recording started",
                "device_path": "/sdcard/recording.mp4",
            }
        }
    )


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "A recording is already in progress"}}
    )


# ── Screenshot ────────────────────────────────────────────────────────────────


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


# ── Screen recording ──────────────────────────────────────────────────────────


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
                        "device_path": "/sdcard/recording.mp4",
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
):
    """
    Start an on-device screen recording via `adb shell screenrecord`.

    The recording is saved to `/sdcard/recording.mp4` on the emulator.
    Call `POST /screen/record/stop` to stop and retrieve the file.
    Only one recording session can be active at a time.
    """
    global _recording_proc, _recording_local_path, _recording_device_id

    if _recording_proc is not None and _recording_proc.poll() is None:
        raise HTTPException(
            status_code=409, detail="A recording is already in progress"
        )

    try:
        adb.run(["shell", "rm", "-f", _DEVICE_RECORDING_PATH], device_id=device_id)
    except adb.ADBError:
        pass

    _recording_local_path = os.path.join(
        config.TEMP_DIR, "recordings", "screen_recording.mp4"
    )
    _recording_device_id = device_id
    _recording_proc = adb.start_process(
        ["shell", "screenrecord", _DEVICE_RECORDING_PATH],
        device_id=device_id,
    )
    return {"message": "Recording started", "device_path": _DEVICE_RECORDING_PATH}


@router.post(
    "/record/stop",
    summary="Stop screen recording and download",
    responses={
        200: {
            "description": "The recorded MP4 file",
            "content": {"video/mp4": {"schema": {"type": "string", "format": "binary"}}},
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
            "description": "Failed to pull recording from device",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to pull recording: adb: error: ..."}
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
    Stop the active screen recording, pull the MP4 from the emulator, and stream it to the client.

    Sends `SIGINT` to the `screenrecord` process so it can finalise and write the MP4 header
    before exiting. The file is then pulled via `adb pull` and returned as `video/mp4`.
    """
    global _recording_proc, _recording_local_path, _recording_device_id

    if _recording_proc is None or _recording_proc.poll() is not None:
        raise HTTPException(status_code=409, detail="No recording is in progress")

    try:
        _recording_proc.send_signal(signal.SIGINT)
        _recording_proc.wait(timeout=15)
    except Exception as exc:
        logger.warning("Error stopping recording process: %s", exc)
        _recording_proc.kill()
        _recording_proc.wait()
    finally:
        _recording_proc = None

    target_device = _recording_device_id or device_id
    _recording_device_id = None

    local_path = _recording_local_path or os.path.join(
        config.TEMP_DIR, "recordings", "screen_recording.mp4"
    )

    try:
        _, stderr = adb.run(
            ["pull", _DEVICE_RECORDING_PATH, local_path],
            timeout=60,
            device_id=target_device,
        )
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if not os.path.exists(local_path):
        raise HTTPException(
            status_code=503, detail=f"Failed to pull recording: {stderr}"
        )

    return FileResponse(
        path=local_path,
        media_type="video/mp4",
        filename="screen_recording.mp4",
    )
