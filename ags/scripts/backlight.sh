#!/bin/bash
LOCKFILE=/tmp/smooth_backlight.lock
BRIGHTNESS=/tmp/set_backlight
smooth() {
    if [ -n "$1" ]; then
        rounded_value=$(echo "scale=0; $1/1" | bc)
        echo $rounded_value >$BRIGHTNESS
    else
        echo "Not enough arguments"
        exit 1
    fi

    if [ -e "$LOCKFILE" ] && kill -0 "$(cat $LOCKFILE)"; then
        echo "locked"
        exit 0
    fi

    trap "rm -f $LOCKFILE; exit" INT TERM EXIT
    echo $$ >"$LOCKFILE"

    smooth_brightness() {
        local max_brightness=$(brightnessctl m)
        local step=$((max_brightness / 100))

        while true; do
            local target_brightness=$(cat $BRIGHTNESS)
            local current_brightness=$(brightnessctl g)
            target_brightness=$(echo "$max_brightness * $target_brightness / 100" | bc)

            if [ $current_brightness -eq $target_brightness ]; then
                exit 0
            fi
            while [ $current_brightness -ne $target_brightness ]; do
                if [ $current_brightness -lt $target_brightness ]; then
                    current_brightness=$((current_brightness + step))
                else
                    current_brightness=$((current_brightness - step))
                fi

                brightnessctl s $current_brightness >/dev/null 2>&1
                sleep 0.001

                local new_target_brightness=$(cat $BRIGHTNESS)
                new_target_brightness=$(echo "$max_brightness * $new_target_brightness / 100" | bc)
                if [ $new_target_brightness -ne $target_brightness ]; then
                    target_brightness=$new_target_brightness
                    break
                fi
            done

        done
    }

    smooth_brightness

    rm -f "$LOCKFILE"
    trap - INT TERM EXIT
}

set() {
    if [ -n "$1" ]; then
        brightnessctl s $1
    else
        echo "Not enough arguments"
        exit 1
    fi
}

get() {
    if [ -e "$LOCKFILE" ] && kill -0 "$(cat $LOCKFILE)"; then
        local target_brightness=$(cat $BRIGHTNESS)
        echo $target_brightness
        exit 0
    fi
    brightness=$(brightnessctl g)
    max_brightness=$(brightnessctl m)
    percentage=$((100 * brightness / max_brightness))

    echo "$percentage"
}

if [[ "$1" == "--smooth" ]]; then
    smooth $2
elif [[ "$1" == "--set" ]]; then
    set $2
elif [[ "$1" == "--get" ]]; then
    get
fi
