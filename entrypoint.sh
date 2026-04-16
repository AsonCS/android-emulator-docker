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
# nohup su ubuntu -c './build_image.sh "-no-audio -no-window"' > out.log 2>&1 &
file="./build_image.log"
touch $file
nohup su ubuntu -c './build_image.sh "-no-audio -no-window"' &> $file \
    & echo "Build images logs in $file"
# su ubuntu -c './build_image.sh "-no-audio -no-window"'

cd ./app

./entrypoint.sh
