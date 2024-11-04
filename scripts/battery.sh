#!/bin/bash

# This script is used for the lockscreen battery indicator.

for bat in /sys/class/power_supply/BAT*; do
    if [ -e "$bat/uevent" ]; then
        BAT_PATH="$bat"
        break
    fi
done

if [ -z "$BAT_PATH" ]; then
    echo "No battery found."
    exit 1
fi

source "$BAT_PATH/uevent"

info() {
    cat "$BAT_PATH/uevent"
}

icon() {
    local battery_charging="󰂄 "
    local battery_alert="󰂃 "
    local battery_100="󰁹 "
    local battery_90="󰂂 "
    local battery_80="󰂁 "
    local battery_70="󰂀 "
    local battery_60="󰁿 "
    local battery_50="󰁾 "
    local battery_40="󰁽 "
    local battery_30="󰁼 "
    local battery_20="󰁻 "
    local battery_10="󰁺 "
    local battery_0="󰂎 "

    if [ "$POWER_SUPPLY_CAPACITY" -le 9 ]; then
        icon="battery_0"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 19 ]; then
        icon="battery_10"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 29 ]; then
        icon="battery_20"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 39 ]; then
        icon="battery_30"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 49 ]; then
        icon="battery_40"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 59 ]; then
        icon="battery_50"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 69 ]; then
        icon="battery_60"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 79 ]; then
        icon="battery_70"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 89 ]; then
        icon="battery_80"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 99 ]; then
        icon="battery_90"
    else
        icon="battery_100"
    fi

    case $POWER_SUPPLY_STATUS in
        Charging) icon="battery_charging";;
        Full) icon="battery_100";;
    esac

    echo "${!icon} "
}

status() {
    echo "$POWER_SUPPLY_CAPACITY%"
}

case $1 in
    info) info;;
    icon) icon;;
    status) status;;
    *) echo "Usage: $0 {info|icon|status}"; exit 1;;
esac
