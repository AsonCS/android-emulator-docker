#!/bin/bash

API_PORT=${1:-8001}

echo "Updating source..."
git pull origin main

echo "Creating virtual environment..."
python3 -m venv .venv

cd ./app

bin=../.venv/bin
if [ ! "$(ls $bin)" ];then
    bin=../.venv/Scripts
fi

echo "Refreshing dependencies..."
$bin/pip3 install -r ./requirements.txt > requirements.log

exec $bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --workers 1
