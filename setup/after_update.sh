#!/bin/bash

"$HOME"/dotfiles/install.sh packages

echo ":: Remove window close and minimize buttons in GTK"
gsettings set org.gnome.desktop.wm.preferences button-layout ':'

echo "Nothing to do"
exit 0
