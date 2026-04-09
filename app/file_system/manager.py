"""
File system helpers: push/pull to the emulator, and read/write container files.

All container paths are validated against CONTAINER_DIR to prevent directory
traversal attacks.
"""
import logging
import os
import tempfile

import config
import adb_runner.runner as adb

logger = logging.getLogger(__name__)

CONTAINER_DIR: str = os.path.join(config.TEMP_DIR, "container")


# ── Path safety ───────────────────────────────────────────────────────────────


def _safe_container_path(rel_path: str) -> str:
    """
    Resolve *rel_path* relative to CONTAINER_DIR and assert it stays inside.
    Raises ``ValueError`` on a directory traversal attempt.
    """
    resolved = os.path.realpath(os.path.join(CONTAINER_DIR, rel_path.lstrip("/")))
    container_real = os.path.realpath(CONTAINER_DIR)
    if not resolved.startswith(container_real + os.sep) and resolved != container_real:
        raise ValueError(f"Path '{rel_path}' escapes the allowed directory")
    return resolved


# ── Emulator I/O ──────────────────────────────────────────────────────────────


def push_to_emulator(src: str, dest: str) -> None:
    """Push a local *src* file to *dest* on the emulator via ADB."""
    stdout, stderr = adb.run(["push", src, dest])
    if "error" in stderr.lower():
        raise RuntimeError(f"ADB push failed: {stderr.strip()}")


def pull_from_emulator(device_path: str) -> str:
    """
    Pull *device_path* from the emulator to a temporary local file.
    Returns the absolute path of the downloaded file (caller owns cleanup).
    """
    filename = os.path.basename(device_path)
    fd, local_path = tempfile.mkstemp(
        suffix=f"_{filename}", dir=config.TEMP_DIR
    )
    os.close(fd)
    stdout, stderr = adb.run(["pull", device_path, local_path], timeout=60)
    if "error" in stderr.lower() or not os.path.exists(local_path):
        raise RuntimeError(f"ADB pull failed: {stderr.strip()}")
    return local_path


# ── Container file store ──────────────────────────────────────────────────────


def save_to_container(rel_path: str, data: bytes) -> str:
    """
    Write *data* to *rel_path* inside CONTAINER_DIR.
    Returns the absolute path of the saved file.
    """
    abs_path = _safe_container_path(rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as fh:
        fh.write(data)
    return abs_path


def read_from_container(rel_path: str) -> bytes:
    """Read and return the bytes of *rel_path* from CONTAINER_DIR."""
    abs_path = _safe_container_path(rel_path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"File not found: {rel_path}")
    with open(abs_path, "rb") as fh:
        return fh.read()


def list_container_files() -> list[str]:
    """Return a sorted list of relative file paths inside CONTAINER_DIR."""
    results: list[str] = []
    for root, _, filenames in os.walk(CONTAINER_DIR):
        for fname in filenames:
            full = os.path.join(root, fname)
            results.append(os.path.relpath(full, CONTAINER_DIR))
    return sorted(results)
