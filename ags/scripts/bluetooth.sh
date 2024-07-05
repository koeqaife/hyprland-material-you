#!/bin/bash

monitor() {
    old_status=$(bluetoothctl show | grep "Powered: " | awk '{print $2}')

    while true; do
        status=$(bluetoothctl show | grep "Powered: " | awk '{print $2}')

        if [ "$status" != "$old_status" ]; then
            echo $status
            old_status=$status
        fi

        sleep 1
    done
}

get_status() {
    status=$(bluetoothctl show | grep "Powered: " | awk '{print $2}')
    echo $status
}

set() {
    power=$1
    bluetoothctl power $power
}

toggle() {
    status=$(bluetoothctl show | grep "Powered: " | awk '{print $2}')
    if [[ $status == "yes" ]]; then
        bluetoothctl power off >/dev/null
        get_status
    else
        bluetoothctl power on >/dev/null
        get_status
    fi
}

if [[ "$1" == "--get" ]]; then
    get_status
elif [[ "$1" == "--set" ]]; then
    { set "$2"; }
elif [[ "$1" == "--monitor" ]]; then
    monitor
elif [[ "$1" == "--toggle" ]]; then
    toggle
fi
