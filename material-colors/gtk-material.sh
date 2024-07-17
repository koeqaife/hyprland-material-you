#!/bin/bash

ICON_THEME_DARK=$(sed -n "1p" "$HOME"/dotfiles/.settings/icon-theme)
ICON_THEME_LIGHT=$(sed -n "2p" "$HOME"/dotfiles/.settings/icon-theme)

if [ "$1" == "--light" ]; then
  gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
  gsettings set org.gnome.desktop.interface icon-theme "$ICON_THEME_LIGHT"
else
  gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3-dark
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
  gsettings set org.gnome.desktop.interface icon-theme "$ICON_THEME_DARK"
fi
