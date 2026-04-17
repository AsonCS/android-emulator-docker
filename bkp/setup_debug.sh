#!/bin/bash

export ANDROID_CMD="commandlinetools-linux-14742923_latest.zip"

export ANDROID_HOME="./android-sdk"
export ANDROID_AVD_HOME="$ANDROID_HOME/.android/avd"
export ANDROID_SDK_ROOT=$ANDROID_HOME

export ANDROID_PATH_BUILD_TOOLS="$ANDROID_HOME/build-tools/$ANDROID_BUILD_TOOLS"
export ANDROID_PATH_CMDLINE_TOOLS="$ANDROID_HOME/cmdline-tools/latest/bin"
export ANDROID_PATH_EMULATOR="$ANDROID_HOME/emulator"
export ANDROID_PATH_PLATFORM_TOOLS="$ANDROID_HOME/platform-tools"

./setup_base.sh

echo "finished..."
