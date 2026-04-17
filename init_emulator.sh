#!/bin/bash

docker build \
    -t=android-emulator-docker-emulator \
    -f=Dockerfile.emulator . \
    > build.log \
    || exit 1

runAndAwait() {
    docker run \
        --rm \
        --device /dev/kvm \
        --name=android-emulator-docker-emulator \
        --add-host=host.docker.internal:172.17.0.1 \
        -p=8000:80 \
        -p=5554:5554 \
        -p=5555:5555 \
        -v ./android-sdk/cmdline-tools:/home/ubuntu/android-sdk/cmdline-tools \
        -v ./android-sdk/licenses:/home/ubuntu/android-sdk/licenses \
        -v ./android-sdk/platform-tools:/home/ubuntu/android-sdk/platform-tools \
        -e ADB_KEY="$(cat ~/.android/adbkey)" \
        android-emulator-docker-emulator \
        ./entrypoint.sh \
        || exit 1
}

runAndSleep() {
    docker run \
        -d \
        --rm \
        --device /dev/kvm \
        --name=android-emulator-docker-emulator \
        --add-host=host.docker.internal:172.17.0.1 \
        -p=8000:80 \
        -p=5554:5554 \
        -p=5555:5555 \
        -v ./android-sdk/cmdline-tools:/home/ubuntu/android-sdk/cmdline-tools \
        -v ./android-sdk/licenses:/home/ubuntu/android-sdk/licenses \
        -v ./android-sdk/platform-tools:/home/ubuntu/android-sdk/platform-tools \
        -e ADB_KEY="$(cat ~/.android/adbkey)" \
        android-emulator-docker-emulator \
        sleep infinity \
        || exit 1
}

run() {
    docker run \
        -d \
        --rm \
        --device /dev/kvm \
        --name=android-emulator-docker-emulator \
        --add-host=host.docker.internal:172.17.0.1 \
        -p=8000:80 \
        -p=5554:5554 \
        -p=5555:5555 \
        -v ./android-sdk/cmdline-tools:/home/ubuntu/android-sdk/cmdline-tools \
        -v ./android-sdk/licenses:/home/ubuntu/android-sdk/licenses \
        -v ./android-sdk/platform-tools:/home/ubuntu/android-sdk/platform-tools \
        -e ADB_KEY="$(cat ~/.android/adbkey)" \
        android-emulator-docker-emulator \
        || exit 1
}

# runAndAwait
runAndSleep
# run

# Linux/ Mac: /etc/hosts                              -> 127.0.0.1 host.docker.internal
# Windows:    "C:/Windows/System32/drivers/etc/hosts" -> 127.0.0.1 host.docker.internal

# nohup docker exec \
#     android-emulator-docker-emulator \
#     ./entrypoint.sh \
#     > exec.log 2>&1 && echo "Executed" \
#     || exit 1

echo "finished..."
