#!/bin/bash

cd ..

source ./config.sh
export API_PORT=8000

# nohup ./app/build_image.sh

cd ./app

./start_server.sh
