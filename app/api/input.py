"""
Input event simulation routes.

POST /input/tap   – tap at (x, y)
POST /input/swipe – swipe between two points
POST /input/text  – type text into the focused field
POST /input/key   – send a hardware key event
"""
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

import adb_runner.runner as adb

router = APIRouter()

_KEYCODE_RE = re.compile(r"^(\d+|[A-Z][A-Z0-9_]*)$")


# ── Request models ─────────────────────────────────────────────────────────────


class TapRequest(BaseModel):
    x: int = Field(..., description="X coordinate in pixels")
    y: int = Field(..., description="Y coordinate in pixels")

    model_config = ConfigDict(
        json_schema_extra={"example": {"x": 540, "y": 960}}
    )


class SwipeRequest(BaseModel):
    x1: int = Field(..., description="Start X coordinate")
    y1: int = Field(..., description="Start Y coordinate")
    x2: int = Field(..., description="End X coordinate")
    y2: int = Field(..., description="End Y coordinate")
    duration_ms: int = Field(300, ge=1, description="Swipe duration in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={"example": {"x1": 100, "y1": 800, "x2": 100, "y2": 200, "duration_ms": 500}}
    )


class TextRequest(BaseModel):
    text: str = Field(..., description="Text to enter into the focused field")

    model_config = ConfigDict(
        json_schema_extra={"example": {"text": "Hello world"}}
    )


class KeyRequest(BaseModel):
    keycode: str = Field(
        ..., description="Android keycode name (e.g. KEYCODE_POWER, KEYCODE_HOME) or integer"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"keycode": "KEYCODE_HOME"}
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
        json_schema_extra={"example": {"detail": "Invalid keycode 'INVALID KEY'"}}
    )


# ── Tap ───────────────────────────────────────────────────────────────────────


@router.post(
    "/tap",
    response_model=MessageResponse,
    summary="Simulate a tap",
    responses={
        200: {
            "content": {
                "application/json": {"example": {"message": "Tapped at (540, 960)"}}
            }
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def tap(req: TapRequest):
    """
    Simulate a single touch tap at `(x, y)` on the emulator screen.

    Equivalent to `adb shell input tap <x> <y>`.
    Coordinates are in device pixels; the resolution depends on the AVD screen size.
    """
    try:
        adb.run(["shell", "input", "tap", str(req.x), str(req.y)])
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"message": f"Tapped at ({req.x}, {req.y})"}


# ── Swipe ─────────────────────────────────────────────────────────────────────


@router.post(
    "/swipe",
    response_model=MessageResponse,
    summary="Simulate a swipe",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Swiped from (100, 800) to (100, 200) over 500 ms"
                    }
                }
            }
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def swipe(req: SwipeRequest):
    """
    Simulate a swipe gesture from `(x1, y1)` to `(x2, y2)` over `duration_ms` milliseconds.

    Useful for scroll gestures, dismiss actions, and drag transitions.
    Equivalent to `adb shell input swipe <x1> <y1> <x2> <y2> <duration_ms>`.
    """
    try:
        adb.run(
            [
                "shell", "input", "swipe",
                str(req.x1), str(req.y1),
                str(req.x2), str(req.y2),
                str(req.duration_ms),
            ]
        )
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {
        "message": (
            f"Swiped from ({req.x1}, {req.y1}) to ({req.x2}, {req.y2}) "
            f"over {req.duration_ms} ms"
        )
    }


# ── Text input ────────────────────────────────────────────────────────────────


@router.post(
    "/text",
    response_model=MessageResponse,
    summary="Type text",
    responses={
        200: {
            "content": {
                "application/json": {"example": {"message": "Text entered"}}
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Empty text supplied",
            "content": {
                "application/json": {"example": {"detail": "Text must not be empty"}}
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def text_input(req: TextRequest):
    """
    Type a string into the currently focused text field on the emulator.

    Spaces are URL-encoded as `%s` because `adb shell input text` treats spaces as
    argument separators. The command is never passed through a shell interpreter.
    """
    if not req.text:
        raise HTTPException(status_code=400, detail="Text must not be empty")
    encoded = req.text.replace(" ", "%s")
    try:
        adb.run(["shell", "input", "text", encoded])
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"message": "Text entered"}


# ── Key event ─────────────────────────────────────────────────────────────────


@router.post(
    "/key",
    response_model=MessageResponse,
    summary="Send a hardware key event",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "power": {
                            "summary": "Power key",
                            "value": {"message": "Key event sent: KEYCODE_POWER"},
                        },
                        "home": {
                            "summary": "Home key",
                            "value": {"message": "Key event sent: KEYCODE_HOME"},
                        },
                        "back": {
                            "summary": "Back key",
                            "value": {"message": "Key event sent: KEYCODE_BACK"},
                        },
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid keycode format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid keycode 'INVALID KEY'. Must be a KEYCODE_* name or a non-negative integer."
                    }
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def key_event(req: KeyRequest):
    """
    Simulate a hardware key press on the emulator.

    Accepts either a named keycode (e.g. `KEYCODE_POWER`, `KEYCODE_HOME`, `KEYCODE_BACK`, `KEYCODE_POWER`)
    or a raw integer keycode. The full list of Android keycodes is available at
    [https://developer.android.com/reference/android/view/KeyEvent](https://developer.android.com/reference/android/view/KeyEvent).
    """
    keycode = req.keycode.strip().upper()
    if not _KEYCODE_RE.match(keycode):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid keycode '{req.keycode}'. "
                "Must be a KEYCODE_* name or a non-negative integer."
            ),
        )
    try:
        adb.run(["shell", "input", "keyevent", keycode])
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"message": f"Key event sent: {keycode}"}
