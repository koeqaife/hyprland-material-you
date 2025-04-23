#!/bin/bash

MAX_RETRIES=5
RETRY_COUNT=0
RETRY_TIMEOUT=10

LAST_FAILURE_TIME=0

while true; do
    CURRENT_TIME=$(date +%s)

    if (( CURRENT_TIME - LAST_FAILURE_TIME > RETRY_TIMEOUT )); then
        RETRY_COUNT=0
    fi
    
    python hypryou_ui.py
    EXIT_CODE=$?

    if [[ $EXIT_CODE -eq 0 ]]; then
        exit 0
    fi

    ((RETRY_COUNT++))
    LAST_FAILURE_TIME=$(date +%s)

    if (( RETRY_COUNT >= MAX_RETRIES )); then
        # TODO: Open some window with crash info
        echo "App used all attempts to start, bye."
        exit 1
    fi

    echo "App exited with $EXIT_CODE, retrying..."
    sleep 1
done
