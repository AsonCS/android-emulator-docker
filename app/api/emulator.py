"""
Emulator state management routes.

GET  /emulator/status  – current emulator state
POST /emulator/reboot  – restart Android OS
POST /emulator/wipe    – wipe data and restart emulator
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

import emulator_manager.manager as manager
from emulator_manager.manager import EmulatorStatus

router = APIRouter()


# ── Response models ────────────────────────────────────────────────────────────


class StatusResponse(BaseModel):
    status: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "Ready"}}
    )


class MessageResponse(BaseModel):
    message: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"message": "Operation completed successfully"}}
    )


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Emulator is offline"}}
    )


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Get emulator status",
    responses={
        200: {
            "description": "Current emulator state",
            "content": {
                "application/json": {
                    "examples": {
                        "ready": {"summary": "Emulator ready", "value": {"status": "Ready"}},
                        "booting": {"summary": "Emulator booting", "value": {"status": "Booting"}},
                        "offline": {"summary": "Emulator offline", "value": {"status": "Offline"}},
                        "online": {"summary": "Emulator online", "value": {"status": "Online"}},
                    }
                }
            },
        }
    },
)
def get_status(
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
):
    """
    Retrieve the current state of the Android emulator.

    Possible values:
    - **Offline** – emulator process is not running or ADB cannot reach it
    - **Booting** – ADB sees the device but `sys.boot_completed` is not `1` yet
    - **Online** – device is visible to ADB (alias kept for backwards compatibility)
    - **Ready** – emulator is fully booted and responsive
    """
    status = manager.get_status(device_id=device_id)
    return {"status": status.value}


@router.post(
    "/reboot",
    response_model=MessageResponse,
    summary="Reboot emulator",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"message": "Emulator reboot initiated"}
                }
            }
        },
        503: {
            "model": ErrorResponse,
            "description": "Emulator is offline",
            "content": {
                "application/json": {
                    "example": {"detail": "Emulator is offline"}
                }
            },
        },
    },
)
def reboot(
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
):
    """
    Perform a soft reboot of the Android OS inside the running emulator.

    The emulator process itself is not restarted; only the Android OS reboots.
    The device will transition through **Booting** before returning to **Ready**.
    """
    if manager.get_status(device_id=device_id) == EmulatorStatus.OFFLINE:
        raise HTTPException(status_code=503, detail="Emulator is offline")
    manager.reboot(device_id=device_id)
    return {"message": "Emulator reboot initiated"}


@router.post(
    "/wipe",
    response_model=MessageResponse,
    summary="Wipe emulator data",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Emulator wipe initiated. The emulator is restarting with clean data."
                    }
                }
            }
        }
    },
)
def wipe(
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
):
    """
    Wipe the emulator's data partition and restart it with a clean state.

    This is equivalent to launching the emulator with `-wipe-data`.
    The operation is **asynchronous** — the endpoint returns immediately while
    the emulator restarts in the background. Poll `/emulator/status` to wait for
    the **Ready** state.
    """
    manager.wipe(device_id=device_id)
    return {"message": "Emulator wipe initiated. The emulator is restarting with clean data."}
