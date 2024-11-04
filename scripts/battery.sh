#!/bin/bash

# This script is used for the lockscreen battery indicator.

battery=true
source /sys/class/power_supply/BAT1/uevent || battery=false

info() {
    if $battery; then
        cat /sys/class/power_supply/BAT1/uevent
    else
        echo "POWER_SUPPLY_PRESENT=0"
    fi
}

icon() {
    if ! $battery; then return; fi

    local battery_charging="󰂄 "
    local battery_alert="󰂃 "
    local battery_100="󰁹 "
    local battery_90="󰂂 "
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

    # Percentage-based icon mapping
    if [ "$POWER_SUPPLY_CAPACITY" -le 9 ]; then
        local icon="battery_0"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 19 ]; then
        local icon="battery_10"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 29 ]; then
        local icon="battery_20"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 39 ]; then
        local icon="battery_30"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 49 ]; then
        local icon="battery_40"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 59 ]; then
        local icon="battery_50"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 69 ]; then
        local icon="battery_60"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 79 ]; then
        local icon="battery_70"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 89 ]; then
        local icon="battery_80"
    elif [ "$POWER_SUPPLY_CAPACITY" -le 99 ]; then
        local icon="battery_90"
    else
        local icon="battery_100"
    fi

    # Status-based icon mapping
    case $POWER_SUPPLY_STATUS in
        Charging) local icon="battery_charging";;
        Full) local icon="battery_full";;
    esac

    echo "${!icon} "
}

status() {
    if ! $battery; then return; fi

    echo "$POWER_SUPPLY_CAPACITY%"
}

case $1 in
    (info) info;;
    (icon) icon;;
    (status) status;;
esac