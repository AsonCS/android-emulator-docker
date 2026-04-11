#!/bin/bash

export ANDROID_API_VERSION="34"
export ANDROID_BUILD_TOOLS="34.0.0"
export ANDROID_CMD="commandlinetools-linux-14742923_latest.zip"
export EMULATOR_ARCH="x86_64"
export EMULATOR_DEVICE="medium_tablet"
export EMULATOR_NAME="tablet"
export EMULATOR_PORT="5554"
export EMULATOR_SERIAL="emulator-${EMULATOR_PORT}"
export EMULATOR_TARGET="default"

export ANDROID_HOME="./root/sdk/android"
export ANDROID_AVD_HOME="$ANDROID_HOME/.android/avd"
export ANDROID_SDK_ROOT=$ANDROID_HOME

export ANDROID_PATH_BUILD_TOOLS="$ANDROID_HOME/build-tools/$ANDROID_BUILD_TOOLS"
export ANDROID_PATH_CMDLINE_TOOLS="$ANDROID_HOME/cmdline-tools/latest/bin"
export ANDROID_PATH_EMULATOR="$ANDROID_HOME/emulator"
export ANDROID_PATH_PLATFORM_TOOLS="$ANDROID_HOME/platform-tools"

./root/sdk/android/setup.sh
nohup ./root/sdk/android/build_image.sh

export API_PORT=8000
./app/start_server.sh

echo "finished..."
