#!/bin/bash

configureAdbKey() {
    echo "configureAdbKey | ${ADB_KEY:0:92}"
    if [ ! -z "$ADB_KEY" ]; then
        mkdir -p /root/.android
        echo $ADB_KEY > /root/.android/adbkey
        mkdir -p /home/ubuntu/.android
        echo $ADB_KEY > /home/ubuntu/.android/adbkey
    fi
}

configureAdbKey
chmod -R 777 /dev/kvm
chmod -R 777 /root/.android
chmod -R 777 /home/ubuntu/.android
su ubuntu -c './build_image.sh "-no-audio -no-window"'

cd ./app

./entrypoint.sh
