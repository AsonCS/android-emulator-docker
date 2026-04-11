#!/bin/bash

/root/sdk/android/setup.sh

/root/sdk/android/build_image.sh "-no-audio -no-window"

./start_server.sh
