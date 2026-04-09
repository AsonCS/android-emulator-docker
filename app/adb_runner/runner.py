"""
Low-level ADB subprocess wrapper.

All commands are executed via list arguments (never shell=True) to prevent
container-level shell injection. The run_raw() entry-point additionally enforces
an allowlist of permitted top-level ADB subcommands.
"""
import logging
import shlex
import subprocess
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Subcommands permitted when a caller supplies a raw command string.
ALLOWED_SUBCOMMANDS: frozenset[str] = frozenset(
    {
        "shell",
        "install",
        "uninstall",
        "push",
        "pull",
        "logcat",
        "bugreport",
        "devices",
        "forward",
        "reverse",
        "exec-out",
        "am",
        "pm",
    }
)


class ADBError(Exception):
    """Raised when an ADB operation cannot be completed."""


# ── Internal helpers ──────────────────────────────────────────────────────────


def _base() -> list[str]:
    return [config.ADB_PATH, "-s", config.EMULATOR_SERIAL]


# ── Public API ────────────────────────────────────────────────────────────────


def run(args: list[str], timeout: int = 30) -> tuple[str, str]:
    """Run ``adb -s <serial> <args>`` and return ``(stdout, stderr)`` as text."""
    cmd = _base() + args
    logger.debug("ADB run: %s", cmd)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        raise ADBError(f"ADB command timed out after {timeout}s: {args}")
    except FileNotFoundError:
        raise ADBError(f"ADB binary not found at '{config.ADB_PATH}'")


def run_binary(args: list[str], timeout: int = 30) -> bytes:
    """Run an ADB command and return raw bytes from stdout (for binary output)."""
    cmd = _base() + args
    logger.debug("ADB run_binary: %s", cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return result.stdout
    except subprocess.TimeoutExpired:
        raise ADBError(f"ADB command timed out after {timeout}s: {args}")
    except FileNotFoundError:
        raise ADBError(f"ADB binary not found at '{config.ADB_PATH}'")


def run_raw(command_str: str, timeout: int = 30) -> tuple[str, str]:
    """
    Safely parse and execute a caller-supplied ADB command string.

    Security measures applied:
    - Uses shlex.split (no shell=True) to avoid container shell injection.
    - Strips any -s / -H / -P flags to prevent serial/host override.
    - Validates the first subcommand against ALLOWED_SUBCOMMANDS.
    """
    try:
        tokens = shlex.split(command_str)
    except ValueError as exc:
        raise ADBError(f"Malformed command: {exc}") from exc

    if not tokens:
        raise ADBError("Empty command")

    # Remove leading 'adb' token if the caller included it.
    if tokens[0] in ("adb", config.ADB_PATH):
        tokens = tokens[1:]

    if not tokens:
        raise ADBError("No subcommand provided")

    # Strip -s / -H / -P flag pairs to prevent serial/host override.
    filtered: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] in ("-s", "-H", "-P") and i + 1 < len(tokens):
            i += 2
        else:
            filtered.append(tokens[i])
            i += 1

    if not filtered:
        raise ADBError("No subcommand after filtering flags")

    subcommand = filtered[0]
    if subcommand not in ALLOWED_SUBCOMMANDS:
        raise ADBError(
            f"Subcommand '{subcommand}' is not permitted. "
            f"Allowed: {sorted(ALLOWED_SUBCOMMANDS)}"
        )

    return run(filtered, timeout=timeout)


def start_process(args: list[str]) -> subprocess.Popen:
    """Start an ADB command as a non-blocking background process."""
    cmd = _base() + args
    logger.debug("ADB Popen: %s", cmd)
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
