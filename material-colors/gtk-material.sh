#!/bin/bash

if [ "$1" == "--light" ]; then
  gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
else
  gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3-dark
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'

fi
