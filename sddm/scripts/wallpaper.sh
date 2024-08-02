#!/bin/bash
cache_file="$HOME/.cache/current_wallpaper"
if [ ! -d /etc/sddm.conf.d/ ]; then
    sudo mkdir /etc/sddm.conf.d
    echo "Folder /etc/sddm.conf.d created."
fi

cp $HOME/dotfiles/sddm/sddm.conf /etc/sddm.conf.d/
cp $HOME/dotfiles/sddm/sddm.conf /etc/
if [ "$1" != "init" ]; then
    echo "File /etc/sddm.conf.d/sddm.conf updated."
fi

current_wallpaper=$(cat "$cache_file")
extension="${current_wallpaper##*.}"

cp $current_wallpaper /usr/share/sddm/themes/corners/backgrounds/current_wallpaper.$extension

if [ "$1" != "init" ]; then
    echo "Current wallpaper copied into /usr/share/sddm/themes/corners/backgrounds/"
fi

new_wall=$(echo $current_wallpaper | sed "s|$HOME/wallpaper/||g")
cp $HOME/.cache/material/colors-sddm-style.conf /usr/share/sddm/themes/corners/theme.conf
sed -i 's/CURRENTWALLPAPER/'"current_wallpaper.$extension"'/' /usr/share/sddm/themes/corners/theme.conf

if [ "$1" != "init" ]; then
    echo "File theme.conf updated in /usr/share/sddm/themes/corners/"

    echo "DONE! Please logout to test sddm."
fi
