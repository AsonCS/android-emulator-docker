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

# export APKS="'http://files.boxcontrol.io/s/MMZXzCP8zgwfWKb/download/DEV_WeUpdate_v.2.0.43.1_1115_release.apk'"
# export PRIV_APKS="'DeviceControl' 'http://files.boxcontrol.io/s/gga35cHKNazneLN/download/DEV_DC_2.0.80.4_1385_A9_debug_ADM-4135_5d24e5569d7e2f260274c40dc5ef6bf365e524ca.apk' 'http://files.boxcontrol.io/s/SLYxgKgd8KkgxHE/download/privapp-permissions-com.wetek.devicecontrol.xml' 'AppPersister' 'http://files.boxcontrol.io/s/LBGiTBFXZn64wD4/download/DEV_AP_FirmwareBuild_1.1.0_15_debug_test_f24b0944222aeead6b0ecc4f79d807642bd6eae0.apk' 'SelfProvision' 'http://files.boxcontrol.io/s/GLxZAWRJyDwYeGL/download/DEV_SP_9b43e74b-1402-4fc2-b8e1-dd6b7f3e5d92_1.3_15_debug_test_375570a6ad0ea5fab7063e20edcb6cdb4199069a.apk' 'WeUpdate' 'http://files.boxcontrol.io/s/MMZXzCP8zgwfWKb/download/DEV_WeUpdate_v.2.0.43.1_1115_release.apk' 'http://files.boxcontrol.io/s/2XmC84MArMoXdxm/download/privapp-permissions-com.wetek.weupdate.xml'"

./root/sdk/android/setup.sh
nohup ./root/sdk/android/build_image.sh

export API_PORT=8000
./app/start_server.sh

echo "finished..."
