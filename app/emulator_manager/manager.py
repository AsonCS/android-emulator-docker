"""
Emulator lifecycle management: status polling, reboot, and wipe-data restart.
"""
import logging
import subprocess
from enum import Enum
from typing import Optional

import config
import adb_runner.runner as adb

logger = logging.getLogger(__name__)


class EmulatorStatus(str, Enum):
    OFFLINE = "Offline"
    BOOTING = "Booting"
    ONLINE = "Online"
    READY = "Ready"


# ── Status ────────────────────────────────────────────────────────────────────


def get_status(device_id: Optional[str] = None) -> EmulatorStatus:
    """Determine the current emulator status via ADB."""
    # run() resolves/auto-connects the target device and executes against it.
    try:
        stdout, _ = adb.run(
            ["shell", "getprop", "sys.boot_completed"],
            timeout=10,
            device_id=device_id,
        )
        if stdout.strip() == "1":
            return EmulatorStatus.READY
        return EmulatorStatus.BOOTING
    except adb.ADBError:
        return EmulatorStatus.OFFLINE


# ── Lifecycle ─────────────────────────────────────────────────────────────────


def reboot(device_id: Optional[str] = None) -> None:
    """Reboot the Android OS inside the emulator (non-destructive)."""
    stdout, stderr = adb.run(["reboot"], timeout=15, device_id=device_id)
    logger.info("Emulator reboot triggered. stdout=%r stderr=%r", stdout, stderr)


def wipe(device_id: Optional[str] = None) -> None:
    """
    Wipe the emulator's data partition and restart it.

    Steps:
    1. Gracefully stop the running emulator via ADB.
    2. Fallback: kill the OS process if ADB kill fails.
    3. Start a new emulator process with ``-wipe-data``.
    """
    # 1. Ask the emulator to exit gracefully.
    try:
        adb.run(["emu", "kill"], timeout=15, device_id=device_id)
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
