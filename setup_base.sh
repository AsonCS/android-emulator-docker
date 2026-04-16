#!/bin/bash

if [ -z "$ANDROID_HOME" ] ||
    [ -z "$ANDROID_CMD" ] ||
    [ -z "$ANDROID_PATH_CMDLINE_TOOLS" ]; then
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

installPlatformTools() {
    echo "installPackagesWithSdkManager | $ANDROID_PATH_CMDLINE_TOOLS"
    yes Y | $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --licenses
    yes Y | $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --verbose "platform-tools"
}

installCommandlineTools
installPlatformTools

echo "ls $ANDROID_HOME"
ls $ANDROID_HOME

echo "finished..."
