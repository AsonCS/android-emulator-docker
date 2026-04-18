#!/bin/bash

if [ -z "$ANDROID_AVD_HOME" ] ||
    [ -z "$EMULATOR_NAME" ] ||
    [ -z "$EMULATOR_DEVICE" ] ||
    [ -z "$ANDROID_API_VERSION" ] ||
    [ -z "$EMULATOR_TARGET" ] ||
    [ -z "$EMULATOR_ARCH" ] ||
    [ -z "$ANDROID_PATH_CMDLINE_TOOLS" ] ||
    [ -z "$ANDROID_PATH_PLATFORM_TOOLS" ] ||
    [ -z "$ANDROID_PATH_EMULATOR" ] ||
    [ -z "$ANDROID_HOME" ]; then
    echo "Required variables are missing."
    exit 1
fi

EMULATOR_ARGS=$1
echo "EMULATOR_ARGS $EMULATOR_ARGS"
RUN_ONLY=$2
echo "RUN_ONLY $RUN_ONLY"

createEmulator() {
    echo "createEmulator | $ANDROID_PATH_CMDLINE_TOOLS $ANDROID_AVD_HOME $EMULATOR_NAME $EMULATOR_DEVICE $ANDROID_API_VERSION $EMULATOR_TARGET $EMULATOR_ARCH"
    mkdir -p $ANDROID_AVD_HOME || echo "$ANDROID_AVD_HOME exixts"
    $ANDROID_PATH_CMDLINE_TOOLS/avdmanager --verbose create avd --force -n $EMULATOR_NAME -d $EMULATOR_DEVICE -k "system-images;android-$ANDROID_API_VERSION;$EMULATOR_TARGET;$EMULATOR_ARCH"
    sed -i "s/hw.lcd.height=1600/hw.lcd.height=1080/g" "$ANDROID_AVD_HOME/$EMULATOR_NAME.avd/config.ini"
    sed -i "s/hw.initialOrientation=portrait/hw.initialOrientation=landscape/g" "$ANDROID_AVD_HOME/$EMULATOR_NAME.avd/config.ini"
    sed -i "s/hw.lcd.width=2560/hw.lcd.width=1920/g" "$ANDROID_AVD_HOME/$EMULATOR_NAME.avd/config.ini"
}

waitForDevice() {
    echo "Waiting for ADB device | $ANDROID_PATH_PLATFORM_TOOLS"
    $ANDROID_PATH_PLATFORM_TOOLS/adb wait-for-device
    until [ "$($ANDROID_PATH_PLATFORM_TOOLS/adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
        sleep 5
    done
}

runEmulator() {
    echo "runEmulator | $ANDROID_PATH_EMULATOR $EMULATOR_NAME"
    file="./$EMULATOR_NAME-$(date "+%Y%m%d%H%M%S").log"
    touch $file
    $ANDROID_PATH_EMULATOR/emulator \
        -avd "$EMULATOR_NAME" \
        -port 5554 \
        -skip-adb-auth \
        -no-boot-anim \
        -writable-system \
        -no-snapshot \
        -no-snapshot-save \
        -wipe-data \
        -feature AllowSnapshotMigration \
        -gpu swiftshader_indirect \
        $EMULATOR_ARGS &> $file \
        & echo "Emulator logs in $file" 
    waitForDevice
}

pushFile() {
    remote_dir="$1"
    remote_file="$remote_dir/$2"
    file="$3"
    echo "pushFile | $remote_dir $remote_file $file"
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell mkdir -p $remote_dir
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell chmod 777 $remote_dir
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell rm $remote_file
    $ANDROID_PATH_PLATFORM_TOOLS/adb push $file $remote_file
    $ANDROID_PATH_PLATFORM_TOOLS/adb shell chmod 777 $remote_file
}

configApks() {
    echo "configApks | $ANDROID_PATH_PLATFORM_TOOLS $ANDROID_HOME"
    if [ ! "$(ls "$ANDROID_HOME/apks")" ]; then
        echo "Empty"
        return
    fi
    for apk in $ANDROID_HOME/apks/*; do
        if [ -f "$apk" ]; then
            echo "install $apk"
            $ANDROID_PATH_PLATFORM_TOOLS/adb install -d -r "$apk"
        fi
    done
}

configPrivApks() {
    echo "configPrivApks | $ANDROID_HOME $ANDROID_PATH_PLATFORM_TOOLS"
    if [ ! "$(ls "$ANDROID_HOME/priv-apks")" ]; then
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
    for folder in $ANDROID_HOME/priv-apks/*; do
        if [ -d "$folder" ]; then
            package=$(basename $folder)
            echo $package
            remote_apks_dir="/system/priv-app"
            remote_permissions_dir="/system/etc/permissions"
            for file in $ANDROID_HOME/priv-apks/$package/*; do
                if [ -f "$file" ]; then
                    if [ "${file##*.}" == "apk" ]; then
                        apk=$(basename $file)
                        apk_name="${apk%%.*}"
                        remote_dir="$remote_apks_dir/$apk_name"
                        pushFile $remote_dir $apk $file
                    fi
                    if [ "${file##*.}" == "xml" ]; then
                        xml=$(basename $file)
                        pushFile $remote_permissions_dir $xml $file
                    fi
                fi
            done
        fi
    done
    $ANDROID_PATH_PLATFORM_TOOLS/adb reboot
    waitForDevice
}

if [ "$RUN_ONLY" == "true" ]; then
    runEmulator
elif [ "$RUN_ONLY" == "false" ]; then
    createEmulator
    runEmulator
    configApks
    configPrivApks
    $ANDROID_PATH_PLATFORM_TOOLS/adb emu kill
else
    createEmulator
    runEmulator
    configApks
    configPrivApks
fi

echo "build_image finished..."
