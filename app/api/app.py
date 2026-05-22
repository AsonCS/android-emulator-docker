"""
Android application management routes.

POST /app/install    – upload and install an APK
POST /app/uninstall  – uninstall by package name
POST /app/clear      – wipe user data/cache for a package
"""
import os
import tempfile
import logging

from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field

import adb_runner.runner as adb
import config

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Request / Response models ─────────────────────────────────────────────────


class UninstallRequest(BaseModel):
    package: str = Field(..., description="Package name, e.g. com.example.app")

    model_config = ConfigDict(
        json_schema_extra={"example": {"package": "com.example.myapp"}}
    )


class ClearDataRequest(BaseModel):
    package: str = Field(..., description="Package name, e.g. com.example.app")

    model_config = ConfigDict(
        json_schema_extra={"example": {"package": "com.example.myapp"}}
    )


class InstallResponse(BaseModel):
    message: str
    output: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"message": "APK installed successfully", "output": "Success"}
        }
    )


class UninstallResponse(BaseModel):
    message: str
    output: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Package 'com.example.myapp' uninstalled",
                "output": "Success",
            }
        }
    )


class ClearDataResponse(BaseModel):
    message: str
    output: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "App data cleared for 'com.example.myapp'",
                "output": "Success",
            }
        }
    )


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Package not found: com.example.missing"}}
    )


# ── APK install ───────────────────────────────────────────────────────────────


@router.post(
    "/install",
    response_model=InstallResponse,
    summary="Install an APK",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "APK installed successfully",
                        "output": "Success",
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Not an APK, or installation rejected by device",
            "content": {
                "application/json": {
                    "examples": {
                        "not_apk": {
                            "summary": "Wrong file type",
                            "value": {"detail": "Uploaded file must be an APK (.apk)"},
                        },
                        "install_failed": {
                            "summary": "Device rejected install",
                            "value": {
                                "detail": "Install failed: Failure [INSTALL_FAILED_ALREADY_EXISTS]"
                            },
                        },
                    }
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "ADB unreachable",
            "content": {
                "application/json": {
                    "example": {"detail": "ADB command timed out after 120s"}
                }
            },
        },
    },
)
async def install_apk(
    file: UploadFile = File(..., description="APK file to install on the emulator"),
    reinstall: bool = Query(
        False, description="Reinstall the app keeping its data (`-r` flag)"
    ),
    grant_permissions: bool = Query(
        False, description="Automatically grant all runtime permissions (`-g` flag)"
    ),
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
):
    """
    Upload an APK and install it on the emulator via `adb install`.

    - `reinstall=true` → passes `-r` (keeps app data on reinstall)
    - `grant_permissions=true` → passes `-g` (grants all runtime permissions)
    """
    if not (file.filename or "").lower().endswith(".apk"):
        raise HTTPException(
            status_code=400, detail="Uploaded file must be an APK (.apk)"
        )

    fd, tmp_path = tempfile.mkstemp(suffix=".apk", dir=config.TEMP_DIR)
    try:
        os.write(fd, await file.read())
    finally:
        os.close(fd)

    install_args = ["install"]
    if reinstall:
        install_args.append("-r")
    if grant_permissions:
        install_args.append("-g")
    install_args.append(tmp_path)

    try:
        stdout, stderr = adb.run(install_args, timeout=120, device_id=device_id)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        os.unlink(tmp_path)

    if "Failure" in stdout or "error" in stderr.lower():
        raise HTTPException(
            status_code=400, detail=f"Install failed: {stdout.strip()} {stderr.strip()}"
        )

    return {"message": "APK installed successfully", "output": stdout.strip()}


# ── Uninstall ─────────────────────────────────────────────────────────────────


@router.post(
    "/uninstall",
    response_model=UninstallResponse,
    summary="Uninstall an application",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Package 'com.example.myapp' uninstalled",
                        "output": "Success",
                    }
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Package not found on device",
            "content": {
                "application/json": {
                    "example": {"detail": "Package not found: com.example.missing"}
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def uninstall_apk(
    req: UninstallRequest,
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
):
    """
    Uninstall an application from the emulator by its package name.

    Equivalent to `adb uninstall <package>`.
    """
    try:
        stdout, stderr = adb.run(["uninstall", req.package], timeout=60, device_id=device_id)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if "Failure" in stdout or "Unknown package" in stdout:
        raise HTTPException(
            status_code=404, detail=f"Package not found: {req.package}"
        )

    return {"message": f"Package '{req.package}' uninstalled", "output": stdout.strip()}


# ── Clear data ────────────────────────────────────────────────────────────────


@router.post(
    "/clear",
    response_model=ClearDataResponse,
    summary="Clear application data",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "App data cleared for 'com.example.myapp'",
                        "output": "Success",
                    }
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Package not found on device",
            "content": {
                "application/json": {
                    "example": {"detail": "Package not found or clear failed: com.example.missing"}
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def clear_app_data(
    req: ClearDataRequest,
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
):
    """
    Wipe the user data and cache for a specific package via `adb shell pm clear <package>`.

    This is equivalent to going to **Settings → Apps → [App] → Clear Data** on the device.
    """
    try:
        stdout, stderr = adb.run(
            ["shell", "pm", "clear", req.package],
            timeout=30,
            device_id=device_id,
        )
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if "Failed" in stdout or "Unknown package" in stdout:
        raise HTTPException(
            status_code=404,
            detail=f"Package not found or clear failed: {req.package}",
        )

    return {
        "message": f"App data cleared for '{req.package}'",
        "output": stdout.strip(),
    }
