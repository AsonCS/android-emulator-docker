#!/bin/bash

configureAdbKey() {
    echo "configureAdbKey | ${ADB_KEY:0:92}"
    if [ ! -z "$ADB_KEY" ]; then
        echo $ADB_KEY > /root/.android/adbkey
        echo $ADB_KEY > /home/ubuntu/.android/adbkey
    fi
}

echo "Giving permissions..."
python3 ./entrypoint.py

# if [ ! -f "configured.txt" ]; then
#     echo "Not configured"
#     echo 1 > configured.txt
#     configureAdbKey
#     ./build_image.sh "-no-audio -no-window" "false"
#     sleep infinity # To commit image
# else
#     ./build_image.sh "-no-audio -no-window" "true"
# fi

configureAdbKey
./build_image.sh "-no-audio -no-window"

nohup socat tcp-listen:5594,bind=0.0.0.0,reuseaddr,fork tcp:localhost:5554 &> socat_5594.log &
nohup socat tcp-listen:5595,bind=0.0.0.0,reuseaddr,fork tcp:localhost:5555 &> socat_5595.log &
# pkill socat

cd ./app

./entrypoint.sh
