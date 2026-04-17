1. Done: On [logs](/app/api/logs.py), implemented `logcat_search_regex` endpoint
    - Added `GET /logs/logcat/search/regex`
    - Supports `pattern` (required regex), optional `flags` (`i`, `m`, `s`), optional `level`, optional `lines`, optional `device_id`
    - Uses shared ADB runner device resolution: if `device_id` is not connected, API attempts `adb connect <device_id>`
    - OpenAPI updated through endpoint signature, parameter descriptions, and response examples
2. Done: Connect with any device via adb, device identifier via parameter or first one if no parameter passed
    - Implemented optional `device_id` query parameter in ADB-backed endpoints
    - Added `device_id` support in emulator endpoints (`/emulator/status`, `/emulator/reboot`, `/emulator/wipe`)
    - If target device is not currently connected, the API attempts `adb connect <device_id>` automatically
    - If `device_id` is omitted, the first online device from `adb devices` is used
    - OpenAPI updated via endpoint signatures and query parameter descriptions
3. Endpoint dumpsys (all, netstats, bluetooth_manager, alarm, window, location, package <pkg_name>, procstats, activity, battery ...), dumpstate, bug report ...
