"""
Emulator lifecycle management: status polling, reboot, and wipe-data restart.
"""
import logging
import subprocess
from enum import Enum

import config
import adb_runner.runner as adb

logger = logging.getLogger(__name__)


class EmulatorStatus(str, Enum):
    OFFLINE = "Offline"
    BOOTING = "Booting"
    ONLINE = "Online"
    READY = "Ready"


# ── Status ────────────────────────────────────────────────────────────────────


def get_status() -> EmulatorStatus:
    """Determine the current emulator status via ADB."""
    try:
        result = subprocess.run(
            [config.ADB_PATH, "devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return EmulatorStatus.OFFLINE

    device_lines = result.stdout.splitlines()[1:]
    connected = {
        line.split()[0]
        for line in device_lines
        if len(line.split()) >= 2 and line.split()[1] != "offline"
    }

    if config.EMULATOR_SERIAL not in connected:
        return EmulatorStatus.OFFLINE

    # Device is visible – check boot completion.
    try:
        stdout, _ = adb.run(["shell", "getprop", "sys.boot_completed"], timeout=10)
        if stdout.strip() == "1":
            return EmulatorStatus.READY
        return EmulatorStatus.BOOTING
    except adb.ADBError:
        return EmulatorStatus.BOOTING


# ── Lifecycle ─────────────────────────────────────────────────────────────────


def reboot() -> None:
    """Reboot the Android OS inside the emulator (non-destructive)."""
    stdout, stderr = adb.run(["reboot"], timeout=15)
    logger.info("Emulator reboot triggered. stdout=%r stderr=%r", stdout, stderr)


def wipe() -> None:
    """
    Wipe the emulator's data partition and restart it.

    Steps:
    1. Gracefully stop the running emulator via ADB.
    2. Fallback: kill the OS process if ADB kill fails.
    3. Start a new emulator process with ``-wipe-data``.
    """
    # 1. Ask the emulator to exit gracefully.
    try:
        adb.run(["emu", "kill"], timeout=15)
        logger.info("Emulator stopped via 'emu kill'.")
    except adb.ADBError as exc:
        logger.warning("Could not stop emulator via ADB: %s", exc)

    # 2. Fallback: kill the OS process.
    try:
        subprocess.run(
            ["pkill", "-f", f"emulator.*-avd.*{config.EMULATOR_NAME}"],
            timeout=10,
        )
    except Exception as exc:
        logger.debug("pkill fallback: %s", exc)

    # 3. Restart with -wipe-data.
    cmd = [
        config.EMULATOR_PATH,
        "-avd", config.EMULATOR_NAME,
        "-no-audio",
        "-no-window",
        "-gpu", "swiftshader_indirect",
        "-no-snapshot",
        "-wipe-data",
    ]
    logger.info("Starting emulator with -wipe-data: %s", " ".join(cmd))
    subprocess.Popen(cmd)
