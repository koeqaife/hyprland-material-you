#!/bin/bash

"$HOME"/dotfiles/install.sh packages
cp -f $HOME/dotfiles/setup/wl-gammarelay.service $HOME/.config/systemd/user/

exit 0
