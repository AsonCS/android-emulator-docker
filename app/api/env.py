"""
Environment simulation routes.

POST /env/location – set GPS coordinates
POST /env/network  – toggle airplane mode, Wi-Fi, or mobile data
"""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

import adb_runner.runner as adb

router = APIRouter()


# ── Request models ─────────────────────────────────────────────────────────────


class LocationRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS longitude (-180 to 180)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"latitude": 37.7749, "longitude": -122.4194}
        }
    )


class NetworkRequest(BaseModel):
    type: Literal["airplane", "wifi", "data"] = Field(
        ...,
        description=(
            "Network feature to toggle:\n"
            "- `airplane` – airplane mode\n"
            "- `wifi` – Wi-Fi adapter\n"
            "- `data` – mobile data"
        ),
    )
    enabled: bool = Field(..., description="`true` to enable, `false` to disable")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"type": "airplane", "enabled": True}
        }
    )


# ── Response model ─────────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    message: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"message": "Operation completed"}}
    )


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "ADB command timed out after 15s"}}
    )


# ── Location ──────────────────────────────────────────────────────────────────


@router.post(
    "/location",
    response_model=MessageResponse,
    summary="Set GPS location",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "sf": {
                            "summary": "San Francisco",
                            "value": {"message": "Location set to (37.7749, -122.4194)"},
                        },
                        "london": {
                            "summary": "London",
                            "value": {"message": "Location set to (51.5074, -0.1278)"},
                        },
                    }
                }
            }
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def set_location(req: LocationRequest):
    """
    Set the GPS coordinates of the emulator using `adb emu geo fix`.

    Note: longitude is provided before latitude per the NMEA convention used by
    the Android Emulator console interface.
    """
    try:
        adb.run(
            ["emu", "geo", "fix", str(req.longitude), str(req.latitude)],
            timeout=15,
        )
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"message": f"Location set to ({req.latitude}, {req.longitude})"}


# ── Network ───────────────────────────────────────────────────────────────────


@router.post(
    "/network",
    response_model=MessageResponse,
    summary="Toggle network state",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "airplane_on": {
                            "summary": "Airplane mode enabled",
                            "value": {"message": "airplane enabled"},
                        },
                        "wifi_off": {
                            "summary": "Wi-Fi disabled",
                            "value": {"message": "wifi disabled"},
                        },
                        "data_on": {
                            "summary": "Mobile data enabled",
                            "value": {"message": "data enabled"},
                        },
                    }
                }
            }
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def set_network(req: NetworkRequest):
    """
    Toggle airplane mode, Wi-Fi, or mobile data on the emulator.

    - **airplane** – changes the global `airplane_mode_on` setting and broadcasts
      `android.intent.action.AIRPLANE_MODE` to apply the change immediately.
    - **wifi** – calls `adb shell svc wifi enable/disable`.
    - **data** – calls `adb shell svc data enable/disable`.
    """
    try:
        if req.type == "airplane":
            value = "1" if req.enabled else "0"
            adb.run(
                ["shell", "settings", "put", "global", "airplane_mode_on", value],
                timeout=10,
            )
            adb.run(
                [
                    "shell", "am", "broadcast",
                    "-a", "android.intent.action.AIRPLANE_MODE",
                    "--ez", "state", str(req.enabled).lower(),
                ],
                timeout=10,
            )

        elif req.type == "wifi":
            state = "enable" if req.enabled else "disable"
            adb.run(["shell", "svc", "wifi", state], timeout=10)

        elif req.type == "data":
            state = "enable" if req.enabled else "disable"
            adb.run(["shell", "svc", "data", state], timeout=10)

    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    state_label = "enabled" if req.enabled else "disabled"
    return {"message": f"{req.type} {state_label}"}
