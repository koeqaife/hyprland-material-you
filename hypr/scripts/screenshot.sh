#!/bin/bash
DIR="$HOME/Pictures/screenshots/"
NAME="screenshot_$(date +%d%m%Y_%H%M%S).png"

# hyprshot -z -m region -o "/tmp" -f "$NAME" -s

if [[ "$1" == "--window" ]]; then
	hyprshot -m window -o "/tmp" -f "$NAME" -s
elif [[ "$1" == "--active" ]]; then
	hyprshot -m active -m output -o "/tmp" -f "$NAME" -s
else
	hyprshot -m region -o "/tmp" -f "$NAME" -s --
fi

swappy -f "/tmp/$NAME" -o "$DIR$NAME"
