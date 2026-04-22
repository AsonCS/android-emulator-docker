#!/bin/bash

# $(export PYTHONPATH=$(pwd)/../.venv && pyinstaller --onefile --add-data ./static:./static --hidden-import fastapi --hidden-import uvicorn --hidden-import python3.12 --hidden-import websockets --collect-all fastapi --collect-all uvicorn --collect-all python3.12 --collect-all websockets main.py)

API_PORT=${1:-8001}

echo "Updating source..."
git pull origin main

cd ./app

echo "Creating virtual environment..."
python3 -m venv .venv

bin=./.venv/bin
if [ ! "$(ls $bin)" ];then
    bin=./.venv/Scripts
fi

echo "Refreshing dependencies..."
$bin/pip3 install -r ./requirements.txt > requirements.log

$bin/python3 main.py
