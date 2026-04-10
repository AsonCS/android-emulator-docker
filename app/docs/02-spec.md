# Specification: Android Emulator REST API Wrapper

## 1. Overview
This project provides a REST API interface written in Python to control, monitor, and interact with an Android Emulator running inside a Docker container. It is designed specifically for automated testing, allowing continuous integration pipelines or external test runners to interact with the emulator via standard HTTP requests.

## 2. Architecture & Design
* **Modular Python Project:** The codebase is structured into logical modules (e.g., `api`, `adb_runner`, `emulator_manager`, `file_system`).
* **Lightweight Scripts:** Underlying operations are handled by small, focused Python scripts wrapping `subprocess` calls to ADB.
* **Dependency Management:** Standard Python dependency files (`requirements.txt` or `pyproject.toml`) will be used.
* **Stateless API:** The REST API should remain as stateless as possible, reflecting the real-time state of the emulator.

## 3. Technology Stack
* **Language:** Python 3.9+
* **API Framework:** FastAPI or Flask (Industry standard, highly adopted for Python REST services)
* **Android Tools:** Android Debug Bridge (ADB), Android Emulator CLI
* **Environment:** Docker Container (Linux-based, containing the Android SDK and Python environment)

## 4. System Behavior & Lifecycle
* **Initialization:** The system relies on a root `.sh` file (e.g., `entrypoint.sh`) executed at container startup.
* **Startup Sequence:** 1. The `.sh` script initializes the virtual display (if required, e.g., Xvfb).
    2. Starts the Android Emulator process in the background.
    3. Waits for the emulator to boot (or proceeds asynchronously).
    4. Starts the Python REST API server (e.g., using Uvicorn or Gunicorn).
* **Teardown:** Graceful shutdown endpoints or container termination signals will cleanly kill the emulator and API server to prevent corrupted AVD states.

## 5. Feature Specifications

### 5.1. Emulator State Management
* **Status Polling (`GET /emulator/status`):** * *Description:* Retrieves the current state of the emulator.
    * *Returns:* JSON indicating status (`Offline`, `Booting`, `Online`, `Ready`).
* **Reboot (`POST /emulator/reboot`):** * *Description:* Safely restarts the Android emulator environment.
* **Wipe Data (`POST /emulator/wipe`):**
    * *Description:* Restores the emulator to a clean slate (requires emulator restart).

### 5.2. ADB Command Execution
* **Raw Execution (`POST /adb/execute`):**
    * *Description:* Accepts a raw string command, runs it against the connected emulator, and retrieves the text output (STDOUT/STDERR).
    * *Security/Validation:* Must implement basic sanitization to prevent container-level shell injection.

### 5.3. Screen Capture & Media
* **Screenshot (`GET /screen/image`):**
    * *Description:* Captures a real-time screenshot of the emulator.
    * *Returns:* A binary stream of the image file (e.g., `image/png`).
* **Screen Record Start/Stop (`POST /screen/record/start`, `POST /screen/record/stop`):**
    * *Description:* Starts an `adb shell screenrecord` process. The stop endpoint halts the recording, pulls the `.mp4` file from the device to the container, and returns a download link or the binary file.

### 5.4. Logcat & Telemetry
* **Retrieve Logs (`GET /logs/logcat`):**
    * *Description:* Fetches the current logcat buffer.
    * *Parameters:* `lines` (number of tail lines), `clear` (boolean to wipe logs after fetching).
    * *Returns:* Plain text response (`text/plain`) containing logcat lines.
* **Filtered Logs (`GET /logs/logcat/search`):**
    * *Description:* Retrieves logcat outputs filtered by a specific query parameter.
    * *Parameters:* `grep` (string to filter), `level` (e.g., Error, Warning, Info).
    * *Returns:* Plain text response (`text/plain`) containing filtered logcat lines.

### 5.5. File System Management
* **Push to Emulator (`POST /files/emulator/push`):**
    * *Description:* Uploads a file from the client to the container, then pushes it via ADB to a specified path on the emulator.
* **Pull from Emulator (`GET /files/emulator/pull`):**
    * *Description:* Pulls a file from a specified path on the emulator to the container, then downloads it to the client.
* **Container File Access (`GET /files/container`, `POST /files/container`):**
    * *Description:* Direct management of files inside the Docker container (useful for test artifacts, configuration files, or temporary APK storage).

### 5.6. Application Management (Added Feature)
* **Install APK (`POST /app/install`):**
    * *Description:* Uploads and installs an APK onto the emulator. Supports `-r` (reinstall) and `-g` (grant permissions) flags.
* **Uninstall APK (`POST /app/uninstall`):**
    * *Description:* Removes a package from the device via its package name (e.g., `com.example.app`).
* **Clear App Data (`POST /app/clear`):**
    * *Description:* Wipes the user data and cache for a specific package name.

### 5.7. Input & Interaction Simulation (Added Feature)
* **Touch / Tap (`POST /input/tap`):**
    * *Description:* Simulates a touch event at specific `x` and `y` coordinates.
* **Swipe (`POST /input/swipe`):**
    * *Description:* Simulates a swipe from `x1, y1` to `x2, y2` with a specified duration.
* **Text Input (`POST /input/text`):**
    * *Description:* Types a given string into the currently focused text field.
* **Key Event (`POST /input/key`):**
    * *Description:* Simulates physical hardware buttons (e.g., `KEYCODE_HOME`, `KEYCODE_BACK`, `KEYCODE_POWER`).

### 5.8. Environment Simulation (Added Feature)
* **Mock Location (`POST /env/location`):**
    * *Description:* Sets the GPS coordinates (Latitude, Longitude) of the emulator using `adb emu geo fix`.
* **Network Toggles (`POST /env/network`):**
    * *Description:* Toggles Airplane mode, Wi-Fi, or mobile data on/off to test app behavior offline.