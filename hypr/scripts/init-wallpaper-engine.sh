#!/bin/bash
wallpaper_engine=$(cat $HOME/dotfiles/.settings/wallpaper-engine.sh)
if [ "$wallpaper_engine" == "swww" ] ;then
    # swww
    echo ":: Using swww"
    swww-daemon
    swww-daemon --format xrgb
    sleep 0.5
    python -O ~/dotfiles/hypr/scripts/wallpaper.py -P
elif [ "$wallpaper_engine" == "hyprpaper" ] ;then    
    # hyprpaper
    echo ":: Using hyprpaper"
    sleep 0.5
    python -O ~/dotfiles/hypr/scripts/wallpaper.py -P
else
    echo ":: Wallpaper Engine disabled"
    python -O ~/dotfiles/hypr/scripts/wallpaper.py -P
fi

