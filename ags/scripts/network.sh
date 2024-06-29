#!/bin/bash
get_uuid() {
    local SSID="$1"
    local UUID=$(nmcli connection show | grep "$SSID" | grep wifi | awk '{print $2}')
    if [ -z "$UUID" ]; then
        echo undefined
        exit 1
    else
        echo $UUID
    fi
}

edit_by_ssid() {
    local SSID="$1"
    local UUID=$(get_uuid $SSID)
    nm-connection-editor -e $UUID
}

saved_networks() {
    nmcli connection show | grep "$SSID" | grep wifi | awk '{print $1}'
}

if [[ "$1" == "--get" ]]; then
    get_uuid $2
elif [[ "$1" == "--edit" ]]; then
    edit_by_ssid $2
elif [[ "$1" == "--saved" ]]; then
    saved_networks
fi
