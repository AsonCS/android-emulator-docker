#!/bin/bash

API_PORT=${1:-8001}

python3 -m venv .venv

cd ./app

../.venv/bin/pip3 install -r ./requirements.txt

exec ../.venv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --workers 1
