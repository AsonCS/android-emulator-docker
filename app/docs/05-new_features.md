1. On [logs](/app/api/logs.py), implemente a `logcat_search_regex` endpoint
    - Update docs and OpenAPI
2. Connect with any device via adb, device identifier via parameter or first one if no parameter passed
    - Should connect to the device if it is not connected via adb
3. Endpoint dumpsys (all, netstats, bluetooth_manager, alarm, window, location, package <pkg_name>, procstats, activity, battery ...), dumpstate, bug report ...
