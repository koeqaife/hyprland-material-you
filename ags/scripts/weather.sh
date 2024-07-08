#!/bin/bash

KEY=$2
ID=$3
UNIT="metric"

cache_dir=$HOME/.cache/ags/weather
cache_file="$cache_dir/weather_cache.json"
cache_max_age=900
mkdir -p $cache_dir

get_weather_data() {
    current_time=$(date +%s)
    cache_key=$(echo "$KEY $ID $UNIT" | md5sum | awk '{ print $1 }')

    if [[ -f "$cache_file" ]]; then
        cached_key=$(cat "$cache_file" | jq -r '.cache_key')
        last_modified=$(stat -c %Y "$cache_file")

        if [[ "$cached_key" == "$cache_key" && $((current_time - last_modified)) < $cache_max_age ]]; then
            cat "$cache_file" | jq -r '.data'
            return
        fi
    fi

    weather=$(curl -sf "http://api.openweathermap.org/data/2.5/weather?APPID=$KEY&id=$ID&units=$UNIT")
    echo "{ \"cache_key\": \"$cache_key\", \"data\": $weather }" >"$cache_file"
    cat "$cache_file" | jq -r '.data'
}

if [[ "$1" == "weather" ]]; then
    get_weather_data
fi
