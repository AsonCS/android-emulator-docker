"""
Raw ADB command execution route.

POST /adb/execute – runs a sanitised ADB command against the emulator
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

import adb_runner.runner as adb

router = APIRouter()


# ── Request / Response models ─────────────────────────────────────────────────


class ADBExecuteRequest(BaseModel):
    command: str = Field(
        ...,
        description=(
            "ADB command to execute. The leading 'adb' token and any "
            "-s/-H/-P flags are stripped automatically. "
            "Only a permitted set of subcommands is accepted."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"command": "shell dumpsys battery"}
        }
    )


class ADBExecuteResponse(BaseModel):
    stdout: str
    stderr: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stdout": "Current Battery Service state:\n  level: 100\n  status: 5\n",
                "stderr": "",
            }
        }
    )


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Subcommand 'rm' is not permitted. Allowed: ['am', 'bugreport', ...]"
            }
        }
    )


# ── Route ──────────────────────────────────────────────────────────────────────


@router.post(
    "/execute",
    response_model=ADBExecuteResponse,
    summary="Execute a raw ADB command",
    responses={
        200: {
            "description": "Command output (stdout and stderr)",
            "content": {
                "application/json": {
                    "examples": {
                        "battery": {
                            "summary": "battery dump",
                            "value": {
                                "stdout": "Current Battery Service state:\n  level: 100\n  status: 5\n",
                                "stderr": "",
                            },
                        },
                        "packages": {
                            "summary": "package listing",
                            "value": {
                                "stdout": "package:com.android.settings\npackage:com.android.chrome\n",
                                "stderr": "",
                            },
                        },
                    }
                }
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "Command rejected (disallowed subcommand or malformed input)",
            "content": {
                "application/json": {
                    "examples": {
                        "disallowed": {
                            "summary": "Disallowed subcommand",
                            "value": {
                                "detail": "Subcommand 'rm' is not permitted. Allowed: ['am', 'bugreport', 'devices', 'exec-out', 'forward', 'install', 'logcat', 'pm', 'pull', 'push', 'reverse', 'shell', 'uninstall']"
                            },
                        },
                        "empty": {
                            "summary": "Empty command",
                            "value": {"detail": "Empty command"},
                        },
                    }
                }
            },
        },
    },
)
def execute(req: ADBExecuteRequest):
    """
    Execute a raw ADB command against the connected emulator and return its output.

    **Permitted subcommands:** `shell`, `install`, `uninstall`, `push`, `pull`,
    `logcat`, `bugreport`, `devices`, `forward`, `reverse`, `exec-out`, `am`, `pm`.

    Any `-s`, `-H`, or `-P` flags in the supplied command are silently stripped
    to prevent serial/host override. The command is never passed to a shell
    (`shell=False`), preventing container-level injection.
    """
    try:
        stdout, stderr = adb.run_raw(req.command)
    except adb.ADBError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"stdout": stdout, "stderr": stderr}
