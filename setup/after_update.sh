#!/bin/bash

ask_continue() {
    local message=$1
    local exit_on_no=${2:-false}
    if gum confirm "$message"; then
        return 0
    else
        echo ":: Skipping $message."
        if $exit_on_no; then
            echo ":: Exiting script."
            exit 0
        else
            return 1
        fi
    fi
}

install_microtex() {
    cd ~/dotfiles/setup/MicroTex/
    makepkg -si
}


cp -f $HOME/dotfiles/setup/wl-gammarelay.service $HOME/.config/systemd/user/
ask_continue "Proceed with installing/updating packages?" && "$HOME"/dotfiles/install.sh packages
ask_continue "Proceed with installing MicroTex?" && install_microtex


exit 0
