#!/bin/bash

GENERATOR="$HOME/dotfiles/material-colors/generate.py"
SETTINGS_FILE="$HOME/dotfiles/.settings/settings.json"

# Function to read a value from the JSON file
get_json_value() {
    local key=$1
    jq -r --arg key "$key" '.[$key]' $SETTINGS_FILE
}

# Function to update a value in the JSON file
update_json_value() {
    local key=$1
    local value=$2
    jq --arg key "$key" --arg value "$value" \
        '.[$key] = $value' $SETTINGS_FILE > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" $SETTINGS_FILE
}

toggle() {
    local color_scheme=$(get_json_value "color-scheme")
    local generation_scheme=$(get_json_value "generation-scheme")

    if [ "$color_scheme" == "dark" ]; then
        python -O $GENERATOR -R --color-scheme light --scheme $generation_scheme
        update_json_value "color-scheme" "light"
    elif [ "$color_scheme" == "light" ]; then
        python -O $GENERATOR -R --color-scheme dark --scheme $generation_scheme
        update_json_value "color-scheme" "dark"
    else
        echo "Unknown color scheme: $color_scheme"
    fi
}

set() {
    local new_scheme=$1
    local generation_scheme=$(get_json_value "generation-scheme")
    python -O $GENERATOR -R --color-scheme $new_scheme --scheme $generation_scheme
    update_json_value "color-scheme" $new_scheme
}

# Process arguments
if [[ "$1" == "--toggle" ]]; then
    toggle
elif [[ "$1" == "--set" ]]; then
    set $2
else
    echo "Usage: $0 --toggle | --set <color-scheme>"
fi
