#!/bin/bash

API_PORT=${1:-8001}

python3 -m venv .venv

cd ./app

bin=../.venv/bin
if [ ! "$(ls $bin)" ];then
    bin=../.venv/Scripts
fi
if [ ! "$(ls $bin)" ];then
    bin=../.venv/Scripts
fi

ls $bin

$bin/pip3 install -r ./requirements.txt

exec $bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --workers 1
