#!/bin/bash
# I tried to make it smooth, but it didn't work
wl_gammarelay() {
    if ! busctl --user list | grep rs.wl.gammarelay; then
        systemctl --user restart wl-gammarelay.service
    fi
}
wl_gammarelay >/dev/null

LOCKFILE=/tmp/brightness.lock

get_brightness() {
    busctl --user get-property rs.wl-gammarelay / rs.wl.gammarelay Brightness | awk '{print $2}'
}

set_brightness() {
    # if [ -e "$LOCKFILE" ] && kill -0 "$(cat $LOCKFILE)"; then
    #     exit 0
    # fi
    # trap "rm -f $LOCKFILE; exit" INT TERM EXIT
    # echo $$ > "$LOCKFILE"
    if (($(echo "$1 < 0.05" | bc -l))); then
        BRIGHTNESS=0.05
    else
        BRIGHTNESS=$1
    fi
    busctl --user -- set-property rs.wl-gammarelay / rs.wl.gammarelay Brightness d $BRIGHTNESS
    # rm -f "$LOCKFILE"
    # trap - INT TERM EXIT
}

set() {
    if [ -n "$1" ]; then
        set_brightness $1
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
    percentage=$(get_brightness)

    echo "$percentage"
}

if [[ "$1" == "--set" ]]; then
    set $2
elif [[ "$1" == "--get" ]]; then
    get
fi
