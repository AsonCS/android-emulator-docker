#!/bin/bash

if [ -z "$ANDROID_HOME" ] ||
    [ -z "$ANDROID_CMD" ] ||
    [ -z "$ANDROID_PATH_CMDLINE_TOOLS" ] ||
    [ -z "$ANDROID_BUILD_TOOLS" ] ||
    [ -z "$ANDROID_API_VERSION" ] ||
    [ -z "$EMULATOR_TARGET" ] ||
    [ -z "$EMULATOR_ARCH" ]; then
    echo "Required variables are missing."
    exit 1
fi

mkdir -p $ANDROID_HOME

installCommandlineTools() {
    echo "installCommandlineTools | $ANDROID_CMD $ANDROID_HOME"
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
    echo "installPackagesWithSdkManager | $ANDROID_PATH_CMDLINE_TOOLS $ANDROID_BUILD_TOOLS $ANDROID_API_VERSION $EMULATOR_TARGET $EMULATOR_ARCH"
    yes Y | $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --licenses
    yes Y | $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --verbose "emulator" "platform-tools" "build-tools;$ANDROID_BUILD_TOOLS" "platforms;android-$ANDROID_API_VERSION" "system-images;android-$ANDROID_API_VERSION;$EMULATOR_TARGET;$EMULATOR_ARCH"
    # $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --list | grep android-${ANDROID_API_VERSION}
}

mkdir -p $ANDROID_HOME/apks
mkdir -p $ANDROID_HOME/priv-apks

installCommandlineTools
installPackagesWithSdkManager

echo "ls $ANDROID_HOME"
ls $ANDROID_HOME

echo "finished..."
