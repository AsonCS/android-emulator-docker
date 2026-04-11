"""
Central configuration loaded from environment variables.
All modules import from here to avoid scattered os.environ calls.
"""
import os

ADB_PATH: str = os.environ.get("ADB_PATH", "adb")
EMULATOR_PATH: str = os.environ.get("EMULATOR_PATH", "emulator")
EMULATOR_SERIAL: str = os.environ.get("EMULATOR_SERIAL", "emulator-5554")
EMULATOR_NAME: str = os.environ.get("EMULATOR_NAME", "tablet")
TEMP_DIR: str = os.environ.get("TEMP_DIR", "/tmp/emulator_api")
API_PORT: int = int(os.environ.get("API_PORT", "8000"))
