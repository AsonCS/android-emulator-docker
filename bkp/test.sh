#!/bin/bash

# touch "$(date "+%Y%m%d%H%M%S").log"
# echo test test test
# echo test test test
# echo test test test

if [ ! -f "created.txt" ]; then
    echo "Created.txt exists"
    cat created.txt
    exit 0
else
    echo "Created.txt not exists"
    echo 1 > created.txt
fi

echo "finished..."
