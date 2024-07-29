#!/bin/bash

# Path to your settings JSON file
settings_file="$HOME/dotfiles/.settings/settings.json"

# Read wallpaper engine from the JSON file
wallpaper_engine=$(jq -r '.["wallpaper-engine"]' "$settings_file")

if [ "$wallpaper_engine" == "swww" ]; then
    # swww
    echo ":: Using swww"
    swww-daemon
    swww-daemon --format xrgb
    sleep 0.5
    python -O ~/dotfiles/hypr/scripts/wallpaper.py -P
elif [ "$wallpaper_engine" == "hyprpaper" ]; then
    # hyprpaper
    echo ":: Using hyprpaper"
    sleep 0.5
    python -O ~/dotfiles/hypr/scripts/wallpaper.py -P
else
    echo ":: Wallpaper Engine disabled"
    python -O ~/dotfiles/hypr/scripts/wallpaper.py -P
fi
