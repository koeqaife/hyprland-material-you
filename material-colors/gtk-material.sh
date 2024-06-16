#!/bin/bash

# if [ ! -d "$HOME"/.cache/gtkgen/generated ]; then
#     mkdir -p "$HOME"/.cache/gtkgen/generated
# fi
# export QT_QPA_PLATFORMTHEME=qt5ct 

# sassc "$HOME"/.cache/material/gtk.scss "$HOME"/.cache/gtkgen/generated/colors_classes.scss --style compact
# sed -i "s/ { color//g" "$HOME"/.cache/gtkgen/generated/colors_classes.scss 
# sed -i "s/\./$/g" "$HOME"/.cache/gtkgen/generated/colors_classes.scss 
# sed -i "s/}//g" "$HOME"/.cache/gtkgen/generated/colors_classes.scss 

# printf "\n""\$darkmode: true;""\n" >> "$HOME"/.cache/gtkgen/generated/colors_classes.scss

# cp "$HOME"/.cache/gtkgen/generated/colors_classes.scss "$HOME/.cache/gtkgen/_material.scss"


# colornames=$(cat "$HOME/.cache/gtkgen/_material.scss" | cut -d: -f1)
# colorstrings=$(cat "$HOME/.cache/gtkgen/_material.scss" | cut -d: -f2 | cut -d ' ' -f2 | cut -d ";" -f1)
# IFS=$'\n'
# # filearr=( $filelist ) # Get colors
# colorlist=( $colornames )
# colorvalues=( $colorstrings )


# mkdir -p "$HOME"/.cache/gtkgen/generated/gradience
# cp "$HOME/dotfiles/material-colors/gradience/preset.json" "$HOME"/.cache/gtkgen/generated/gradience/preset.json

# for i in "${!colorlist[@]}"; do
#     sed -i "s/{{ ${colorlist[$i]} }}/${colorvalues[$i]}/g" "$HOME"/.cache/gtkgen/generated/gradience/preset.json
# done

# mkdir -p "$HOME/.config/presets"
# gradience-cli import -p "$HOME"/.cache/gtkgen/generated/gradience/preset.json
# gradience-cli apply -n Material3_Generated --gtk both

# Set light/dark preference
# And set GTK theme manually as Gradience defaults to light adw-gtk3
# (which is unreadable when broken when you use dark mode)

if [ "$1" == "--light" ]; then
  gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
else
  gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3-dark
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'

fi
