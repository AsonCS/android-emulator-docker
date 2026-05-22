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
    selected_device = _resolve_target_device()
    return [config.ADB_PATH, "-s", selected_device]


def _device_matches(candidate: str, target: str) -> bool:
    """Return True when a listed device serial corresponds to target."""
    if candidate == target:
        return True
    # Some adb outputs append transport decorations; preserve exact and prefix match.
    return candidate.startswith(target)


def _list_online_devices() -> list[str]:
    """Return serials currently reported as online by `adb devices`."""
    try:
        result = subprocess.run(
            [config.ADB_PATH, "devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise ADBError("ADB command timed out after 10s: ['devices']")
    except FileNotFoundError:
        raise ADBError(f"ADB binary not found at '{config.ADB_PATH}'")

    devices: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def _connect_device(target_device: str) -> None:
    """Attempt to connect to a remote adb target (typically host:port)."""
    try:
        result = subprocess.run(
            [config.ADB_PATH, "connect", target_device],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        raise ADBError(f"ADB command timed out after 15s: ['connect', '{target_device}']")
    except FileNotFoundError:
        raise ADBError(f"ADB binary not found at '{config.ADB_PATH}'")

    output = (result.stdout + "\n" + result.stderr).lower()
    if "connected to" in output or "already connected to" in output:
        return

    raise ADBError(
        f"Failed to connect to adb target '{target_device}': "
        f"{(result.stdout or result.stderr).strip() or 'unknown error'}"
    )


def _resolve_target_device(device_id: Optional[str] = None) -> str:
    """
    Resolve which device should receive commands.

    Behavior:
    - If `device_id` is provided, use it; connect first if needed.
    - If omitted, use the first online device.
    - If none are online, attempt to connect to the configured default target.
    """
    online_devices = _list_online_devices()

    if device_id:
        if any(_device_matches(d, device_id) for d in online_devices):
            return device_id
        _connect_device(device_id)
        refreshed = _list_online_devices()
        if any(_device_matches(d, device_id) for d in refreshed):
            return device_id
        raise ADBError(f"Device '{device_id}' is not available after adb connect")

    if online_devices:
        return online_devices[0]

    default_target = "emulator-5554"
    _connect_device(default_target)
    refreshed = _list_online_devices()
    if any(_device_matches(d, default_target) for d in refreshed):
        return default_target
    raise ADBError("No ADB devices available. Provide 'device_id' or connect a device.")


# ── Public API ────────────────────────────────────────────────────────────────


def run(args: list[str], timeout: int = 30, device_id: Optional[str] = None) -> tuple[str, str]:
    """Run ``adb -s <serial> <args>`` and return ``(stdout, stderr)`` as text."""
    selected_device = _resolve_target_device(device_id)
    cmd = [config.ADB_PATH, "-s", selected_device] + args
    logger.debug("ADB run: %s", cmd)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8"
        )
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        raise ADBError(f"ADB command timed out after {timeout}s: {args}")
    except FileNotFoundError:
        raise ADBError(f"ADB binary not found at '{config.ADB_PATH}'")


def run_binary(args: list[str], timeout: int = 30, device_id: Optional[str] = None) -> bytes:
    """Run an ADB command and return raw bytes from stdout (for binary output)."""
    selected_device = _resolve_target_device(device_id)
    cmd = [config.ADB_PATH, "-s", selected_device] + args
    logger.debug("ADB run_binary: %s", cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return result.stdout
    except subprocess.TimeoutExpired:
        raise ADBError(f"ADB command timed out after {timeout}s: {args}")
    except FileNotFoundError:
        raise ADBError(f"ADB binary not found at '{config.ADB_PATH}'")


def run_raw(
    command_str: str,
    timeout: int = 30,
    device_id: Optional[str] = None,
) -> tuple[str, str]:
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

    return run(filtered, timeout=timeout, device_id=device_id)


def start_process(args: list[str], device_id: Optional[str] = None) -> subprocess.Popen:
    """Start an ADB command as a non-blocking background process."""
    selected_device = _resolve_target_device(device_id)
    cmd = [config.ADB_PATH, "-s", selected_device] + args
    logger.debug("ADB Popen: %s", cmd)
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
