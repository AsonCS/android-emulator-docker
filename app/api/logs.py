"""
Logcat and telemetry routes.

GET /logs/logcat         – fetch the logcat buffer
GET /logs/logcat/search  – fetch logcat filtered by grep string and/or log level
GET /logs/logcat/search/regex – fetch logcat filtered by regex and/or log level
"""
import re
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
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
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
        stdout, _ = adb.run(args, timeout=30, device_id=device_id)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if clear:
        try:
            adb.run(["logcat", "-c"], timeout=10, device_id=device_id)
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
    device_id: Optional[str] = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port). "
            "If omitted, the first online device is used."
        ),
    ),
):
    """
    Retrieve logcat output filtered by a keyword and/or minimum log level.

    Both filters are applied server-side:
    - `grep` performs a case-insensitive substring match on each line.
    - `level` maps to Android logcat priority (`*:E`, `*:W`, etc.).

    Examples:
    - `?grep=okhttp.OkHttpClient`: For app's requests
    - `?grep=E%20AndroidRuntime`: For "FATAL EXCEPTIONS"
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
        stdout, _ = adb.run(args, timeout=30, device_id=device_id)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    log_lines = stdout.splitlines()
    if grep:
        needle = grep.lower()
        log_lines = [line for line in log_lines if needle in line.lower()]

    return "\n".join(log_lines)


@router.get(
    "/logcat/search/regex",
    response_class=PlainTextResponse,
    summary="Search logcat output using regex",
    responses={
        200: {
            "description": "Regex-filtered logcat lines as plain text",
            "content": {
                "text/plain": {
                    "examples": {
                        "regex_only": {
                            "summary": "Filtered by regex",
                            "value": "04-09 12:00:02.000  1234  1234 E AndroidRuntime: FATAL EXCEPTION: main\n",
                        },
                        "regex_with_level": {
                            "summary": "Regex + minimum level",
                            "value": "04-09 12:00:02.000  1234  1234 E AndroidRuntime: FATAL EXCEPTION: main\n",
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
            "description": "Invalid regex, flags, or log level",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_regex": {
                            "summary": "Regex failed to compile",
                            "value": {
                                "detail": "Invalid regex pattern '(error': missing ), unterminated subpattern at position 0"
                            },
                        },
                        "invalid_flags": {
                            "summary": "Unsupported regex flags",
                            "value": {
                                "detail": "Invalid regex flags 'x'. Valid flags: i, m, s"
                            },
                        },
                        "invalid_level": {
                            "summary": "Invalid log level",
                            "value": {
                                "detail": "Invalid level 'trace'. Valid values: ['verbose', 'debug', 'info', 'warning', 'warn', 'error', 'fatal', 'silent']"
                            },
                        },
                    }
                }
            },
        },
        503: {"model": ErrorResponse, "description": "ADB unreachable"},
    },
)
def logcat_search_regex(
    pattern: str = Query(
        ...,
        min_length=1,
        description="Python regex pattern to match against each log line",
    ),
    flags: Optional[str] = Query(
        None,
        description=(
            "Optional regex flags as characters. Supported: "
            "`i` (ignore case), `m` (multiline), `s` (dotall)."
        ),
    ),
    level: Optional[str] = Query(
        None,
        description=(
            "Minimum log level to include. "
            "One of: `verbose`, `debug`, `info`, `warning`, `error`, `fatal`"
        ),
    ),
    lines: Optional[int] = Query(
        None, ge=1, description="Return only the last **N** lines before regex filtering"
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
    Retrieve logcat output filtered by a Python regular expression.

    Behavior:
    - `pattern` is compiled server-side and matched against each log line.
    - `flags` supports `i`, `m`, and `s`.
    - `level` maps to Android logcat priority (`*:E`, `*:W`, etc.).
    - Device selection/connection is delegated to the shared ADB runner.
    
    Regex Examples:
    - `.*(okhttp.OkHttpClient: --> [^(end)]).*` Catch the entire single line of an OkHttp request, but not the response.
    - `okhttp.OkHttpClient: --> [^(end)]` Same as above.
    - `19:39(.)*okhttp` hour and minute filer
    - `18:[2-4](.)*okhttp` minutes range
    - `04-17 18:[2-4](.)*okhttp` minutes range with day
    - `((19:09)|(19:39))(.)*okhttp` "or" operator
    """
    regex_flags = 0
    supported_flags = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}
    if flags:
        for flag in flags.lower():
            mapped = supported_flags.get(flag)
            if mapped is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid regex flags '{flags}'. Valid flags: i, m, s",
                )
            regex_flags |= mapped

    try:
        compiled = re.compile(pattern, regex_flags)
    except re.error as exc:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern '{pattern}': {exc}")

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

    if lines is not None:
        args += ["-t", str(lines)]

    try:
        stdout, _ = adb.run(args, timeout=30, device_id=device_id)
    except adb.ADBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    matched_lines = [line for line in stdout.splitlines() if compiled.search(line)]
    return "\n".join(matched_lines)
