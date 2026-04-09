"""
File system management routes.

POST /files/emulator/push   – upload a file from client → container → emulator
GET  /files/emulator/pull   – pull a file from emulator → container → client
GET  /files/container        – list container files, or download one
POST /files/container        – upload a file into the container storage
"""
import os
import tempfile
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict

import config
import file_system.manager as fs

router = APIRouter()
logger = logging.getLogger(__name__)

_ALLOWED_DEST_PREFIXES = ("/sdcard/", "/data/local/tmp/")


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
        fs.push_to_emulator(tmp_path, dest)
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
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Pull a file from the emulator via `adb pull` and stream it to the client.

    The file is saved to a temporary location in the container and deleted after
    the response has been transmitted.
    """
    try:
        local_path = fs.pull_from_emulator(path)
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
        description="Relative file path inside container storage to download. Omit to list all files.",
        examples=["captures/screenshot.png"],
    ),
):
    """
    - **Omit `path`**: returns a JSON list of all files in the container storage area.
    - **Provide `path`**: streams the specified file as a binary download.
    """
    if path is None:
        return {"files": fs.list_container_files()}

    try:
        data = fs.read_from_container(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    filename = os.path.basename(path)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
