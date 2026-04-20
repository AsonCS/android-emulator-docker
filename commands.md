## Geral

- `$(set -a && source .env && set +a && docker buildx bake)`
- `docker compose up -d`

## App

### Manual
- `docker build -t=android-emulator-docker-app -f=Dockerfile.app .`
- `docker build --no-cache --progress=plain -t=android-emulator-docker-app -f=Dockerfile.app .`
- `docker run -d --rm --name=android-emulator-docker-app -p=8001:80 -e ADB_KEY="$(cat ~/.android/adbkey)" android-emulator-docker-app sleep infinity`

## Base

- `docker build -t=android-emulator-docker-base -f=Dockerfile.base .`
- `docker build --no-cache --progress=plain -t=android-emulator-docker-base -f=Dockerfile.base .`
- `docker run -d --rm --name=android-emulator-docker-base android-emulator-docker-base`

## Emulator

### Android
- `$ANDROID_PATH_CMDLINE_TOOLS/avdmanager list devices | grep $EMULATOR_DEVICE`
- `$ANDROID_PATH_EMULATOR/emulator -list-avds`
- `$ANDROID_PATH_CMDLINE_TOOLS/avdmanager delete avd -n $EMULATOR_NAME`
- `$ANDROID_PATH_PLATFORM_TOOLS/adb shell settings put global adb_wifi_enabled 1`
    - `$ANDROID_PATH_PLATFORM_TOOLS/adb shell input tap 428 590` Checkbox button
    - `$ANDROID_PATH_PLATFORM_TOOLS/adb shell input tap 1453 707` Allow button
- `$ANDROID_PATH_PLATFORM_TOOLS/adb shell settings put global stay_on_while_plugged_in 0`
- `$ANDROID_PATH_PLATFORM_TOOLS/adb shell settings put system screen_off_timeout 60000`
- `echo $($ANDROID_PATH_PLATFORM_TOOLS/adb uninstall $package 2>&1)`
- `$ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --list | grep android-${ANDROID_API_VERSION}`

### Manual
- `docker build -t=android-emulator-docker-emulator -f=Dockerfile.emulator .`
- `docker build --no-cache --progress=plain -t=android-emulator-docker-emulator -f=Dockerfile.emulator .`
- `docker run -d --rm --device /dev/kvm --name=android-emulator-docker-emulator -p=8000:80 -p=5595:5595 -e ADB_KEY="$(cat ~/.android/adbkey)" android-emulator-docker-emulator sleep infinity`
- `docker exec -it android-emulator-docker-emulator bash`
- `docker exec -uroot -it android-emulator-docker-emulator bash`

## Others

- `docker builder prune`
- `docker builder prune -a`
- `docker image prune`

```sh
    export ADB_KEY=$(cat ~/.android/adbkey)
    
    # ---

    docker run --network host
```

```yaml
    extra_hosts:
      - host.docker.internal:172.17.0.1
    
    # ---
    
    extra_hosts:
      - host.docker.internal:host-gateway
    
    # ---
    
    network_mode: host
    
    # ---
    
    privileged: true
```

### Host config

| Env         | Local                                   | Config                         |
| ----------- | --------------------------------------- | ------------------------------ |
| Linux/ Mac: | /etc/hosts                              | 127.0.0.1 host.docker.internal |
| Windows:    | "C:/Windows/System32/drivers/etc/hosts" | 127.0.0.1 host.docker.internal |
