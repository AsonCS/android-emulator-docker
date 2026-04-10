"""
Logcat and telemetry routes.

GET /logs/logcat         – fetch the logcat buffer
GET /logs/logcat/search  – fetch logcat filtered by grep string and/or log level
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict

import adb_runner.runner as adb

router = APIRouter()

# Maps human-readable level names to Android logcat priority letters.
_LEVEL_MAP: dict[str, str] = {
    "verbose": "V",
    "debug": "D",
    "info": "I",
    "warning": "W",
    "warn": "W",
    "error": "E",
    "fatal": "F",
    "silent": "S",
}

_LOG_EXAMPLE = (
    "04-09 12:00:01.123  1234  1234 I ActivityManager: Start proc com.example.app\n"
    "04-09 12:00:01.456  1234  1234 D InputReader: Received event\n"
    "04-09 12:00:02.000  1234  1234 E AndroidRuntime: FATAL EXCEPTION: main\n"
)


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "ADB binary not found at 'adb'"}}
    )


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get(
    "/logcat",
    response_class=PlainTextResponse,
    summary="Retrieve logcat buffer",
    responses={
        200: {
            "description": "Logcat lines from the emulator as plain text",
            "content": {
                "text/plain": {
                    "examples": {
                        "default": {
                            "summary": "Recent log lines",
                            "value": _LOG_EXAMPLE,
                        },
                        "empty": {
                            "summary": "Buffer cleared / empty",
                            "value": "",
                        },
                    }
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def logcat(
    lines: Optional[int] = Query(
        None, ge=1, description="Return only the last **N** lines of the buffer"
    ),
    clear: bool = Query(
        False, description="Clear the logcat buffer on the device after fetching"
    ),
):
    """
    Fetch the current logcat buffer from the emulator.

    - Use `lines` to tail the buffer (e.g. `?lines=100`).
    - Use `clear=true` to wipe the buffer after reading (useful for test isolation).
    """
    args = ["logcat", "-d"]
    if lines is not None:
        args += ["-t", str(lines)]

    try:
        stdout, _ = adb.run(args, timeout=30)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if clear:
        try:
            adb.run(["logcat", "-c"], timeout=10)
        except adb.ADBError:
            pass

    return stdout


@router.get(
    "/logcat/search",
    response_class=PlainTextResponse,
    summary="Search logcat output",
    responses={
        200: {
            "description": "Filtered logcat lines as plain text",
            "content": {
                "text/plain": {
                    "examples": {
                        "grep_only": {
                            "summary": "Filtered by keyword",
                            "value": "04-09 12:00:01.123  1234 I ActivityManager: Start proc com.example.app\n",
                        },
                        "level_only": {
                            "summary": "Errors only",
                            "value": "04-09 12:00:02.000  1234 E AndroidRuntime: FATAL EXCEPTION: main\n",
                        },
                        "no_results": {
                            "summary": "No matching lines",
                            "value": "",
                        },
                    }
                }
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid log level supplied",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid level 'trace'. Valid values: ['verbose', 'debug', 'info', 'warning', 'warn', 'error', 'fatal', 'silent']"
                    }
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def logcat_search(
    grep: Optional[str] = Query(
        None, description="Case-insensitive substring to filter log lines"
    ),
    level: Optional[str] = Query(
        None,
        description=(
            "Minimum log level to include. "
            "One of: `verbose`, `debug`, `info`, `warning`, `error`, `fatal`"
        ),
    ),
):
    """
    Retrieve logcat output filtered by a keyword and/or minimum log level.

    Both filters are applied server-side:
    - `grep` performs a case-insensitive substring match on each line.
    - `level` maps to Android logcat priority (`*:E`, `*:W`, etc.).
    """
    args = ["logcat", "-d"]

    if level is not None:
        priority = _LEVEL_MAP.get(level.lower())
        if priority is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid level '{level}'. "
                    f"Valid values: {list(_LEVEL_MAP.keys())}"
                ),
            )
        args.append(f"*:{priority}")

    try:
        stdout, _ = adb.run(args, timeout=30)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    log_lines = stdout.splitlines()
    if grep:
        needle = grep.lower()
        log_lines = [line for line in log_lines if needle in line.lower()]

    return "\n".join(log_lines)
