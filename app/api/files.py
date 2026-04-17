"""
File system management routes.

POST /files/emulator/push   - upload a file from client -> container -> emulator
GET  /files/emulator/pull   - pull a file from emulator -> container -> client
GET  /files/container       - list container files, or download one
POST /files/container       - upload a file into the container storage
POST /files/tmp/clean       - remove all files and folders inside /tmp/emulator_api
"""
import os
import tempfile
import logging
import shutil
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict

import config
import file_system.manager as fs

router = APIRouter()
logger = logging.getLogger(__name__)

_ALLOWED_DEST_PREFIXES = ("/sdcard/", "/data/local/tmp/")
_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TMP_CLEAN_ROOT = "/tmp/emulator_api"


# ── Response models ────────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    message: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"message": "File pushed to '/sdcard/test.txt'"}}
    )


class ContainerSaveResponse(BaseModel):
    message: str
    path: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"message": "File saved", "path": "uploads/config.json"}}
    )


class ContainerListResponse(BaseModel):
    files: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "files": [
                    "app-debug.apk",
                    "captures/screenshot.png",
                    "uploads/config.json",
                ]
            }
        }
    )


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "ADB push failed: remote couldn't create file"}}
    )


class TmpCleanResponse(BaseModel):
    message: str
    cleaned_root: str
    deleted: list[str]
    failed: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Tmp directory cleanup complete",
                "cleaned_root": "/tmp/emulator_api",
                "deleted": ["/tmp/emulator_api/bugreports", "/tmp/emulator_api/tmpfyd0b1ze"],
                "failed": [],
            }
        }
    )


# ── Path validation ─────────────────────────────────────────────────────────────


def _validate_emulator_dest(dest: str) -> None:
    if not any(dest.startswith(p) for p in _ALLOWED_DEST_PREFIXES):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Destination path must start with one of: "
                f"{list(_ALLOWED_DEST_PREFIXES)}"
            ),
        )


def _resolve_relative_to_app(path: str) -> str:
    """
    Resolve a relative path against the app root and ensure it does not escape.
    """
    resolved = os.path.realpath(os.path.join(_APP_ROOT, path))
    app_root_real = os.path.realpath(_APP_ROOT)
    if not resolved.startswith(app_root_real + os.sep) and resolved != app_root_real:
        raise ValueError(f"Path '{path}' escapes the app directory")
    return resolved


# ── Emulator I/O ──────────────────────────────────────────────────────────────


@router.post(
    "/emulator/push",
    response_model=MessageResponse,
    summary="Push a file to the emulator",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"message": "File pushed to '/sdcard/automation/input.txt'"}
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid destination path",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Destination path must start with one of: ['/sdcard/', '/data/local/tmp/']"
                    }
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "ADB push failed",
            "content": {
                "application/json": {
                    "example": {"detail": "ADB push failed: No space left on device"}
                }
            },
        },
    },
)
async def push_to_emulator(
    file: UploadFile = File(..., description="File to upload and push to the emulator"),
    dest: str = Query(
        ...,
        description="Absolute destination path on the emulator. Must start with `/sdcard/` or `/data/local/tmp/`.",
        examples=["/sdcard/automation/payload.txt"],
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
    Upload a file from the client, save it temporarily in the container, then push it
    to the given path on the emulator via `adb push`.

    Allowed destination prefixes: `/sdcard/`, `/data/local/tmp/`
    """
    _validate_emulator_dest(dest)

    suffix = os.path.splitext(file.filename or "")[1] or ".bin"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, dir=config.TEMP_DIR)
    try:
        os.write(fd, await file.read())
    finally:
        os.close(fd)

    try:
        fs.push_to_emulator(tmp_path, dest, device_id=device_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        os.unlink(tmp_path)

    return {"message": f"File pushed to '{dest}'"}


@router.get(
    "/emulator/pull",
    summary="Pull a file from the emulator",
    responses={
        200: {
            "description": "The requested file as a binary download",
            "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
        },
        503: {
            "model": ErrorResponse,
            "description": "ADB pull failed",
            "content": {
                "application/json": {
                    "example": {"detail": "ADB pull failed: remote object '/sdcard/missing.txt' does not exist"}
                }
            },
        },
    },
)
def pull_from_emulator(
    path: str = Query(
        ...,
        description="Absolute path of the file on the emulator",
        examples=["/sdcard/Pictures/screenshot.png"],
    ),
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Pull a file from the emulator via `adb pull` and stream it to the client.

    The file is saved to a temporary location in the container and deleted after
    the response has been transmitted.
    """
    try:
        local_path = fs.pull_from_emulator(path, device_id=device_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    background_tasks.add_task(os.unlink, local_path)
    return FileResponse(
        path=local_path,
        filename=os.path.basename(path),
        background=background_tasks,
    )


# ── Container file store ──────────────────────────────────────────────────────


@router.get(
    "/container",
    summary="List or download container files",
    responses={
        200: {
            "description": "File listing (when `path` is omitted) or file download (when `path` is given)",
            "content": {
                "application/json": {
                    "example": {
                        "files": ["app-debug.apk", "captures/screen.png"]
                    }
                },
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}},
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "Path escapes the container storage directory",
            "content": {
                "application/json": {
                    "example": {"detail": "Path '../../etc/passwd' escapes the allowed directory"}
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "File not found",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found: report.xml"}
                }
            },
        },
    },
)
def container_get(
    path: Optional[str] = Query(
        None,
        description=(
            "Path to download. Supports: "
            "1) container storage-relative paths, "
            "2) app-root-relative paths, "
            "3) absolute paths. "
            "Omit to list all files in container storage."
        ),
        examples=[
            "captures/screenshot.png",
            "bugreport-sdk_phone64_x86_64-UE1A.230829.036.A1-2026-04-17-19-07-32.zip",
            "/home/ubuntu/app/bugreport-sdk_phone64_x86_64-UE1A.230829.036.A1-2026-04-17-19-07-32.zip",
        ],
    ),
):
    """
    - **Omit `path`**: returns a JSON list of all files in the container storage area.
    - **Provide `path`**: streams the specified file as a binary download.
    """
    if path is None:
        return {"files": fs.list_container_files()}

    if os.path.isabs(path):
        abs_path = os.path.realpath(path)
        if not os.path.isfile(abs_path):
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        return FileResponse(path=abs_path, filename=os.path.basename(abs_path))

    try:
        data = fs.read_from_container(path)
        filename = os.path.basename(path)
        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError:
        try:
            abs_path = _resolve_relative_to_app(path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        if not os.path.isfile(abs_path):
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

        return FileResponse(path=abs_path, filename=os.path.basename(abs_path))


@router.post(
    "/container",
    response_model=ContainerSaveResponse,
    summary="Upload a file to container storage",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"message": "File saved", "path": "artifacts/report.xml"}
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Path traversal detected",
            "content": {
                "application/json": {
                    "example": {"detail": "Path '../../etc/passwd' escapes the allowed directory"}
                }
            },
        },
    },
)
async def container_post(
    file: UploadFile = File(..., description="File to store in the container"),
    path: Optional[str] = Query(
        None,
        description="Optional subdirectory inside container storage (e.g. `artifacts`)",
        examples=["artifacts"],
    ),
):
    """
    Upload a file and save it inside the container's persistent storage area.

    Useful for storing test artefacts (APKs, configs, reports) that can later be
    downloaded via `GET /files/container?path=<filename>`.
    """
    filename = file.filename or "upload.bin"
    rel_path = os.path.join(path, filename) if path else filename

    data = await file.read()
    try:
        saved = fs.save_to_container(rel_path, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"message": "File saved", "path": os.path.relpath(saved, fs.CONTAINER_DIR)}


@router.post(
    "/tmp/clean",
    response_model=TmpCleanResponse,
    summary="Clean /tmp folder contents",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Tmp directory cleanup complete",
                        "cleaned_root": "/tmp/emulator_api",
                        "deleted": ["/tmp/emulator_api/bugreports", "/tmp/emulator_api/tmpfyd0b1ze"],
                        "failed": [],
                    }
                }
            }
        },
        500: {
            "model": ErrorResponse,
            "description": "Cleanup root validation failed",
            "content": {
                "application/json": {
                    "example": {"detail": "Cleanup root mismatch: expected '/tmp/emulator_api'"}
                }
            },
        },
    },
)
def clean_tmp_folder():
    """
    Remove all files and directories inside `/tmp/emulator_api`.

    The `/tmp/emulator_api` directory itself is preserved.
    """
    root = os.path.realpath(_TMP_CLEAN_ROOT)
    if root != _TMP_CLEAN_ROOT:
        raise HTTPException(status_code=500, detail="Cleanup root mismatch: expected '/tmp/emulator_api'")

    if not os.path.isdir(root):
        raise HTTPException(status_code=500, detail="Cleanup root not found: '/tmp/emulator_api'")

    deleted: list[str] = []
    failed: list[str] = []

    with os.scandir(root) as entries:
        for entry in entries:
            target_path = entry.path
            try:
                if entry.is_dir(follow_symlinks=False):
                    shutil.rmtree(target_path)
                else:
                    os.unlink(target_path)
                deleted.append(target_path)
            except FileNotFoundError:
                # Entry disappeared between scan and delete.
                continue
            except OSError as exc:
                failed.append(f"{target_path}: {exc}")

    logger.info("/tmp cleanup finished: deleted=%d failed=%d", len(deleted), len(failed))
    return {
        "message": "Tmp directory cleanup complete",
        "cleaned_root": root,
        "deleted": deleted,
        "failed": failed,
    }
