#!/bin/bash

export ANDROID_HOME="$(pwd)"
export ANDROID_AVD_HOME="$ANDROID_HOME/.android/avd"
export ANDROID_AVDMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export ANDROID_SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
export ANDROID_EMULATOR="$ANDROID_HOME/emulator/emulator"
export ANDROID_ADB="$ANDROID_HOME/platform-tools/adb"

installCommandlineTools() {
    local android_cmd="commandlinetools-linux-14742923_latest.zip"
    rm -rf ./cmdline-tools
    mkdir -p ./cmdline-tools/latest
    wget https://dl.google.com/android/repository/$android_cmd
    unzip $android_cmd
    mv ./cmdline-tools/NOTICE.txt ./cmdline-tools/source.properties ./cmdline-tools/bin ./cmdline-tools/lib ./cmdline-tools/latest/
    rm -rf $android_cmd
}

installPackagesWithSdkManager() {
    yes Y | $ANDROID_SDKMANAGER --licenses
    yes Y | $ANDROID_SDKMANAGER --verbose "emulator" "platform-tools" "build-tools;34.0.0" "platforms;android-34" "system-images;android-34;default;x86_64"
    # $ANDROID_SDKMANAGER --list | grep android-34
}

createEmulator() {
    cd $ANDROID_AVD_HOME
    # $ANDROID_AVDMANAGER list devices | grep medium_tablet
    $ANDROID_AVDMANAGER --verbose create avd --force -n tablet -d medium_tablet -k "system-images;android-34;default;x86_64"
    sed -i "s/hw.lcd.height=1600/hw.lcd.height=1080/g" "$ANDROID_AVD_HOME/tablet.avd/config.ini"
    sed -i "s/hw.initialOrientation=portrait/hw.initialOrientation=landscape/g" "$ANDROID_AVD_HOME/tablet.avd/config.ini"
    sed -i "s/hw.lcd.width=2560/hw.lcd.width=1920/g" "$ANDROID_AVD_HOME/tablet.avd/config.ini"
    cd $ANDROID_HOME
}


installCommandlineTools
installPackagesWithSdkManager
createEmulator

echo "finished..."
