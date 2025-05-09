#!/bin/bash

MAX_RETRIES=5
RETRY_COUNT=0
RETRY_TIMEOUT=10

START_TIME=0

python utils_cy/setup.py build_ext --build-lib utils_cy --build-temp utils_cy/build

while true; do
    CURRENT_TIME=$(date +%s)

    if (( CURRENT_TIME - START_TIME > RETRY_TIMEOUT )); then
        RETRY_COUNT=0
    fi
    
    START_TIME=$(date +%s)

    python -OO hypryou_ui.py
    EXIT_CODE=$?

    if [[ $EXIT_CODE -eq 0 ]]; then
        exit 0
    fi

    if [[ $EXIT_CODE -eq 100 ]]; then
        echo "App asked for reload (exit code: $EXIT_CODE)"
        continue
    fi

    ((RETRY_COUNT++))

    if (( RETRY_COUNT >= MAX_RETRIES )); then
        # TODO: Open some window with crash info
        echo "App used all attempts to start, bye."
        exit 1
    fi

    echo "App exited with $EXIT_CODE, retrying ($RETRY_COUNT/$MAX_RETRIES)..."
    sleep 1
done
