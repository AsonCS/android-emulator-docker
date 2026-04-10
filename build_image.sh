#!/bin/bash

createEmulator() {
    echo createEmulator $ANDROID_AVD_HOME $EMULATOR_NAME $EMULATOR_DEVICE $ANDROID_API_VERSION $EMULATOR_TARGET $EMULATOR_ARCH
    mkdir -p $ANDROID_AVD_HOME || echo "$ANDROID_AVD_HOME exixts"
    chmod -R 777 $ANDROID_AVD_HOME
    # $ANDROID_PATH_CMDLINE_TOOLS/avdmanager list devices | grep $EMULATOR_DEVICE
    # $ANDROID_PATH_EMULATOR/emulator -list-avds
    # $ANDROID_PATH_CMDLINE_TOOLS/avdmanager delete avd -n $EMULATOR_NAME
    $ANDROID_PATH_CMDLINE_TOOLS/avdmanager --verbose create avd --force -n $EMULATOR_NAME -d $EMULATOR_DEVICE -k "system-images;android-$ANDROID_API_VERSION;$EMULATOR_TARGET;$EMULATOR_ARCH"
    sed -i "s/hw.lcd.height=1600/hw.lcd.height=1080/g" "$ANDROID_AVD_HOME/$EMULATOR_NAME.avd/config.ini"
    sed -i "s/hw.initialOrientation=portrait/hw.initialOrientation=landscape/g" "$ANDROID_AVD_HOME/$EMULATOR_NAME.avd/config.ini"
    sed -i "s/hw.lcd.width=2560/hw.lcd.width=1920/g" "$ANDROID_AVD_HOME/$EMULATOR_NAME.avd/config.ini"
}

waitForDevice() {
    echo "Waiting for ADB device"
    $ANDROID_PATH_PLATFORM_TOOLS/adb wait-for-device
    until [ "$($ANDROID_PATH_PLATFORM_TOOLS/adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
        sleep 5
    done
}

runEmulator() {
    echo runEmulator $EMULATOR_NAME $EMULATOR_PORT
    # $ANDROID_PATH_EMULATOR/emulator -list-avds
    file="./$EMULATOR_NAME-$(date "+%Y%m%d%H%M%S").log"
    touch $file
    $ANDROID_PATH_EMULATOR/emulator \
        -avd "$EMULATOR_NAME" \
        -port $EMULATOR_PORT \
        -no-audio \
        -no-window \
        -no-boot-anim \
        -writable-system \
        -no-boot-anim \
        -gpu swiftshader_indirect \
        -no-snapshot &> $file \
        & echo "Emulator logs in $file" 
    waitForDevice
}

pushFile() {
    remote_dir="$1"
    remote_file="$remote_dir/$2"
    file="$3"
    echo pushFile $remote_dir $remote_file $file
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell mkdir -p $remote_dir
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell chmod 777 $remote_dir
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell rm $remote_file
    $ANDROID_PATH_PLATFORM_TOOLS/adb push $file $remote_file
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell chmod 777 $remote_file
}

configEmulator() {
    echo configEmulator
    if [ ! "$(ls "$ANDROID_HOME/.apks")" ]; then
        echo "Empty"
        return
    fi
    $ANDROID_PATH_PLATFORM_TOOLS/adb root
    output=$($ANDROID_PATH_PLATFORM_TOOLS/adb remount 2>&1)
    echo $output
    if [[ $output == *"reboot"* ]]; then
        $ANDROID_PATH_PLATFORM_TOOLS/adb reboot
        waitForDevice
        $ANDROID_PATH_PLATFORM_TOOLS/adb root
        echo $($ANDROID_PATH_PLATFORM_TOOLS/adb remount 2>&1)
    fi
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell chmod 777 "/system/priv-app"
    for folder in $ANDROID_HOME/.apks/*; do
        if [ -d "$folder" ]; then
            package=$(basename $folder)
            echo $package
            # echo $($ANDROID_PATH_PLATFORM_TOOLS/adb uninstall $package 2>&1)
            remote_apks_dir="/system/priv-app"
            remote_permissions_dir="/system/etc/permissions"
            for file in $ANDROID_HOME/.apks/$package/*; do
                if [ -f "$file" ]; then
                    if [ "${file##*.}" == "apk" ]; then
                        apk=$(basename $file)
                        apk_name="${apk%%.*}"
                        remote_dir="$remote_apks_dir/$apk_name"
                        pushFile $remote_dir $apk $file
                        echo "ls $remote_apks_dir: $($ANDROID_PATH_PLATFORM_TOOLS/adb shell ls "$remote_apks_dir" | grep "$apk_name")"
                        echo "ls $remote_dir: $($ANDROID_PATH_PLATFORM_TOOLS/adb shell ls "$remote_dir")"
                    fi
                    if [ "${file##*.}" == "xml" ]; then
                        xml=$(basename $file)
                        pushFile $remote_permissions_dir $xml $file
                        echo "ls $remote_permissions_dir: $($ANDROID_PATH_PLATFORM_TOOLS/adb shell ls "$remote_permissions_dir" | grep "$package")"
                    fi
                fi
            done
        fi
    done
    $ANDROID_PATH_PLATFORM_TOOLS/adb reboot
    waitForDevice
}

createEmulator
runEmulator
configEmulator

# $ANDROID_PATH_PLATFORM_TOOLS/adb emu kill

echo "finished..."
