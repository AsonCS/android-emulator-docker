"""
Diagnostics routes backed by ADB.

GET /diagnostics/dumpsys    - run dumpsys (all or a specific service)
GET /diagnostics/dumpstate  - run dumpstate
GET /diagnostics/bugreport  - run bugreport
"""
import os
import re
import shutil
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict

import adb_runner.runner as adb
import config

router = APIRouter()

_DUMPSYS_EXAMPLE = (
    "Current Battery Service state:\n"
    "  AC powered: false\n"
    "  USB powered: true\n"
    "  level: 100\n"
)


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "ADB command timed out after 120s: ['shell', 'dumpstate']"}}
    )


def _plain_output(stdout: str, stderr: str) -> str:
    if stdout:
        return stdout
    return stderr


@router.get(
    "/dumpsys",
    response_class=PlainTextResponse,
    summary="Run dumpsys",
    responses={
        200: {
            "description": "dumpsys output as plain text",
            "content": {
                "text/plain": {
                    "examples": {
                        "battery": {
                            "summary": "Battery service",
                            "value": _DUMPSYS_EXAMPLE,
                        },
                        "empty": {
                            "summary": "No output",
                            "value": "",
                        },
                    }
                }
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid dumpsys parameters",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_pkg": {
                            "summary": "Missing package name",
                            "value": {
                                "detail": "pkg_name is required when section='package'"
                            },
                        },
                    }
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def dumpsys(
    section: str = Query(
        "all",
        description=(
            "dumpsys section/service name. Common values: "
            "`all`, `netstats`, `bluetooth_manager`, `alarm`, `window`, "
            "`location`, `package`, `procstats`, `activity`, `battery`."
        ),
    ),
    pkg_name: Optional[str] = Query(
        None,
        description="Package name used when `section=package` (e.g. `com.example.app`).",
    ),
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used. "
            "If provided but not connected, the API attempts `adb connect <device_id>`."
        ),
    ),
):
    """
    Run `adb shell dumpsys` and return plain text output.

    - `section=all` executes `adb shell dumpsys`.
    - `section=<service>` executes `adb shell dumpsys <service>`.
    - `section=package` requires `pkg_name` and executes
      `adb shell dumpsys package <pkg_name>`.
    """
    normalized = section.strip()
    if not normalized:
        normalized = "all"

    args = ["shell", "dumpsys"]

    if normalized.lower() == "all":
        pass
    elif normalized.lower() == "package":
        if not pkg_name or not pkg_name.strip():
            raise HTTPException(
                status_code=400,
                detail="pkg_name is required when section='package'",
            )
        args.extend(["package", pkg_name.strip()])
    else:
        # Preserve support for custom Android service names while still documenting common options.
        args.append(normalized)

    try:
        stdout, stderr = adb.run(args, timeout=120, device_id=device_id)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return _plain_output(stdout, stderr)


@router.get(
    "/dumpstate",
    response_class=PlainTextResponse,
    summary="Run dumpstate",
    responses={
        200: {
            "description": "dumpstate output as plain text",
            "content": {
                "text/plain": {
                    "examples": {
                        "default": {
                            "summary": "Representative dumpstate output",
                            "value": "== dumpstate: 2026-04-17 12:00:00 ==\n...\n",
                        }
                    }
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def dumpstate(
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used. "
            "If provided but not connected, the API attempts `adb connect <device_id>`."
        ),
    ),
):
    """Run `adb shell dumpstate` and return plain text output."""
    try:
        stdout, stderr = adb.run(["shell", "dumpstate"], timeout=180, device_id=device_id)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return _plain_output(stdout, stderr)


class BugreportResponse(BaseModel):
    path: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "path": "/tmp/emulator_api/bugreports/bugreport-sdk_phone64_x86_64-2026-04-17-20-38-11.zip"
            }
        }
    )


@router.get(
    "/bugreport",
    response_model=BugreportResponse,
    summary="Run bugreport",
    responses={
        200: {
            "description": "Path to the pulled bugreport zip file",
            "content": {
                "application/json": {
                    "example": {
                        "path": "/tmp/emulator_api/bugreports/bugreport-sdk_phone64_x86_64-2026-04-17-20-38-11.zip"
                    }
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable or zip not found"},
    },
)
def bugreport(
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used. "
            "If provided but not connected, the API attempts `adb connect <device_id>`."
        ),
    ),
):
    """
    Run `adb bugreport`, move the resulting zip to `/tmp/emulator_api/bugreports`,
    and return its path.
    """
    try:
        stdout, stderr = adb.run(["bugreport"], timeout=300, device_id=device_id)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    combined = stdout + stderr
    match = re.search(r"Bug report copied to (\S+\.zip)", combined)
    if not match:
        raise HTTPException(
            status_code=503,
            detail=f"bugreport zip path not found in output: {combined.strip()}",
        )

    source_path = match.group(1)
    dest_dir = os.path.join(config.TEMP_DIR, "bugreports")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, os.path.basename(source_path))

    try:
        shutil.move(source_path, dest_path)
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to move bugreport to {dest_dir}: {exc}",
        )

    return {"path": dest_path}
