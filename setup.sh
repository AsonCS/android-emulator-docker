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

mkdir -p $ANDROID_HOME/apks
mkdir -p $ANDROID_HOME/priv-apks

installPackagesWithSdkManager() {
    echo "installPackagesWithSdkManager | $ANDROID_PATH_CMDLINE_TOOLS $ANDROID_BUILD_TOOLS $ANDROID_API_VERSION $EMULATOR_TARGET $EMULATOR_ARCH"
    yes Y | $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --verbose "emulator" "build-tools;$ANDROID_BUILD_TOOLS" "platforms;android-$ANDROID_API_VERSION" "system-images;android-$ANDROID_API_VERSION;$EMULATOR_TARGET;$EMULATOR_ARCH"
    # $ANDROID_PATH_CMDLINE_TOOLS/sdkmanager --list | grep android-${ANDROID_API_VERSION}
}

downloadApks() {
    echo "downloadApks | $APKS $ANDROID_HOME"
    if [ -z "$APKS" ];then
        return
    fi
    for apk in $APKS; do
        url="${apk#\'}"
        url="${url%\'}"
        wget -P "$ANDROID_HOME/apks" $url
    done
}

downloadPrivApks() {
    echo "downloadPrivApks | $PRIV_APKS $ANDROID_HOME"
    if [ -z "$PRIV_APKS" ];then
        return
    fi
    folder=""
    for file in $PRIV_APKS; do
        file="${file#\'}"
        file="${file%\'}"
        if [ "${file##*.}" == "apk" ]; then
            wget -O "$ANDROID_HOME/priv-apks/$folder/$folder.apk" $file
        elif [ "${file##*.}" == "xml" ]; then
            wget -P "$ANDROID_HOME/priv-apks/$folder" $file
        else
            folder=$file
            mkdir -p $ANDROID_HOME/priv-apks/$folder
        fi
    done
}

installPackagesWithSdkManager
downloadApks
downloadPrivApks

echo "ls $ANDROID_HOME"
ls $ANDROID_HOME

echo "finished..."
