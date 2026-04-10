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

source ./config.sh
mkdir -p $ANDROID_HOME

installCommandlineTools() {
    echo installCommandlineTools $ANDROID_CMD
    rm -rf $ANDROID_HOME/cmdline-tools
    mkdir -p $ANDROID_HOME/cmdline-tools/latest
    chmod -R 777 $ANDROID_HOME/cmdline-tools
    wget https://dl.google.com/android/repository/$ANDROID_CMD
    unzip $ANDROID_CMD
    mv ./cmdline-tools/NOTICE.txt ./cmdline-tools/source.properties ./cmdline-tools/bin ./cmdline-tools/lib $ANDROID_HOME/cmdline-tools/latest/
    chmod -R 777 $ANDROID_HOME/cmdline-tools
    rm -rf $ANDROID_CMD
    rm -rf ./cmdline-tools
}

installPackagesWithSdkManager() {
    echo installPackagesWithSdkManager $ANDROID_BUILD_TOOLS $ANDROID_API_VERSION $EMULATOR_TARGET $EMULATOR_ARCH
    yes Y | $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --licenses
    yes Y | $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --verbose "emulator" "platform-tools" "build-tools;$ANDROID_BUILD_TOOLS" "platforms;android-$ANDROID_API_VERSION" "system-images;android-$ANDROID_API_VERSION;$EMULATOR_TARGET;$EMULATOR_ARCH"
    # $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --list | grep android-${ANDROID_API_VERSION}
}

installCommandlineTools
installPackagesWithSdkManager
./build_image.sh

ls $ANDROID_HOME

echo "finished..."
