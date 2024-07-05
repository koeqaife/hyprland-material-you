#!/bin/bash
wl_gammarelay() {
    if ! busctl --user list | grep rs.wl.gammarelay; then
        systemctl --user restart wl-gammarelay.service
    fi
}
wl_gammarelay >/dev/null

get_current_temperature() {
    busctl --user get-property rs.wl-gammarelay / rs.wl.gammarelay Temperature | awk '{print $2}'
}

set_temperature() {
    busctl --user set-property rs.wl-gammarelay / rs.wl.gammarelay Temperature q $1
}

toggle() {
    LOCKFILE=/tmp/smooth_toggle_night_light.lock
    ENABLE=/tmp/enable

    if [ -e "$LOCKFILE" ] && kill -0 "$(cat $LOCKFILE)"; then
        if [ -e "$ENABLE" ]; then
            if [[ $(cat $ENABLE) == "1" ]]; then
                echo 0 >$ENABLE
                echo "disabled"
            else
                echo 1 >$ENABLE
                echo "enabled"
            fi
        fi
        exit 0
    fi

    trap "rm -f $LOCKFILE; exit" INT TERM EXIT
    echo $$ >"$LOCKFILE"

    current_temp=$(get_current_temperature)

    day_temp=6500
    night_temp=3500
    step=50
    delay=0.005

    smooth_change() {
        local start_temp=$1
        local end_temp=$2
        local increment

        if [ "$start_temp" -lt "$end_temp" ]; then
            increment=$step
        else
            increment=-$step
        fi

        temp=$start_temp
        while [ "$temp" -ne "$end_temp" ]; do
            local mode=$(cat $ENABLE)

            if [ "$mode" -eq 0 ]; then
                end_temp=$day_temp
            else
                end_temp=$night_temp
            fi

            if [ "$temp" -eq "$end_temp" ]; then
                sleep 1
                continue
            fi

            set_temperature $temp

            if [ "$increment" -gt 0 ] && [ "$temp" -gt "$end_temp" ]; then
                temp=$end_temp
            elif [ "$increment" -lt 0 ] && [ "$temp" -lt "$end_temp" ]; then
                temp=$end_temp
            else
                temp=$((temp + increment))
            fi

            sleep $delay

            local new_mode=$(cat $ENABLE)

            if [ "$new_mode" -ne "$mode" ]; then
                if [ "$new_mode" -eq 0 ]; then
                    end_temp=$day_temp
                else
                    end_temp=$night_temp
                fi

                if [ "$temp" -lt "$end_temp" ]; then
                    increment=$step
                else
                    increment=-$step
                fi

                temp=$(get_current_temperature)
            fi
        done
        if [ -e "$ENABLE" ]; then
            if [[ $(cat $ENABLE) == "1" ]]; then
                echo "enabled"
            else
                echo "disabled"
            fi
        fi
        set_temperature $end_temp
    }

    if [ "$current_temp" -lt "$(((day_temp + night_temp) / 2))" ]; then
        echo 0 >$ENABLE
        smooth_change $current_temp $day_temp
    else
        echo 1 >$ENABLE
        smooth_change $current_temp $night_temp
    fi

    rm -f "$LOCKFILE"
    trap - INT TERM EXIT
}

get() {
    day_temp=6500
    night_temp=5000

    current_temp=$(get_current_temperature)

    if [ "$current_temp" -lt "$(((day_temp + night_temp) / 2))" ]; then
        echo "enabled"
    else
        echo "disabled"
    fi
}

if [[ "$1" == "--toggle" ]]; then
    toggle
elif [[ "$1" == "--get" ]]; then
    get
fi
