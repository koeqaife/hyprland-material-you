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

declare -A battery_icons_charging=(
    [100]="battery_charging_full"
    [90]="battery_charging_90"
    [80]="battery_charging_80"
    [70]="battery_charging_80"
    [60]="battery_charging_60"
    [50]="battery_charging_50"
    [40]="battery_charging_30"
    [30]="battery_charging_30"
    [20]="battery_charging_20"
    [10]="battery_charging_20"
    [0]="battery_charging_20"
)

declare -A battery_icons=(
    [100]="battery_full"
    [90]="battery_6_bar"
    [80]="battery_5_bar"
    [70]="battery_5_bar"
    [60]="battery_4_bar"
    [50]="battery_3_bar"
    [40]="battery_2_bar"
    [30]="battery_2_bar"
    [20]="battery_1_bar"
    [10]="battery_1_bar"
    [0]="battery_alert"
)

get_closest_battery_icon() {
    local level="$1"
    local charging="$2"
    local -n icons_array

    if [ "$charging" = "true" ]; then
        icons_array=battery_icons_charging
    else
        icons_array=battery_icons
    fi

    local levels=($(for key in "${!icons_array[@]}"; do echo "$key"; done | sort -nr))

    for threshold in "${levels[@]}"; do
        if [ "$level" -ge "$threshold" ]; then
            echo "${icons_array[$threshold]}"
            return
        fi
    done

    echo "${icons_array[${levels[-1]}]}"
}

icon() {
    local capacity="$POWER_SUPPLY_CAPACITY"
    local charging="false"

    if [ "$POWER_SUPPLY_STATUS" = "Charging" ]; then
        charging="true"
    fi

    get_closest_battery_icon "$capacity" "$charging"
}

info() {
    cat "$BAT_PATH/uevent"
}

status() {
    echo "$POWER_SUPPLY_CAPACITY%"
}

case $1 in
info) info ;;
icon) icon ;;
status) status ;;
*)
    echo "Usage: $0 {info|icon|status}"
    exit 1
    ;;
esac
