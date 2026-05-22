#!/bin/bash

export API_PORT=${1:-8001}

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
