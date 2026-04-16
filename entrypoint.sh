#!/bin/bash

./build_image.sh "-no-audio -no-window"

cd ./app

./entrypoint.sh
