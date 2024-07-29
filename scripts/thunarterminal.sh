#!/bin/bash
clear

settings_file=~/dotfiles/.settings/apps.json

echo "Checking for settings file: $settings_file"
if [ -f "$settings_file" ]; then
    echo "Settings file found."
    terminal=$(jq -r '.terminal' "$settings_file")
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to parse JSON file with jq."
        exit 1
    fi
    echo ":: Installing $terminal"
    if [ -d ~/.config/xfce4 ]; then
        if [ ! -f ~/.config/xfce4/helpers.rc ]; then
            touch ~/.config/xfce4/helpers.rc
        fi
        echo "TerminalEmulator=$terminal" > ~/.config/xfce4/helpers.rc
        echo ":: $terminal defined as Thunar Terminal Emulator."
    else
        echo "ERROR: ~/.config/xfce4 not found. Please open Thunar once to create it."
        echo "Then start this script again."
    fi
else
    echo "ERROR: $settings_file not found"
fi
sleep 3
