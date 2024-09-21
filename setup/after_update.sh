#!/bin/bash

BACKUP_DIR="$HOME/dotfiles/.backup"

FILES_TO_RESTORE=(
    "./hypr/conf/custom/*"
    "./.settings/*"
    "./hypr/conf/apps.conf"
    "./wallpapers/*"
    "./hypr/hypridle.conf"
    "./ags/README.md"
    "./ags/tsconfig.json"
)

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

restore_files() {
    for file_pattern in "${FILES_TO_RESTORE[@]}"; do
        for file in $BACKUP_DIR/$file_pattern; do
            if [ -e "$file" ]; then
                original_path="${file/$BACKUP_DIR\//}"
                cp "$file" "$original_path"
                echo "Restored: $original_path"
                git update-index --skip-worktree "$original_path"
            fi
        done
    done
}

git ls-files -v | grep '^S' | awk '{print $2}' | xargs git update-index --no-skip-worktree
restore_files

cp -f $HOME/dotfiles/setup/wl-gammarelay.service $HOME/.config/systemd/user/
ask_continue "Import the old settings into the new settings?" && python "$HOME"/dotfiles/setup/import_settings.py
ask_continue "Proceed with installing/updating packages?" && "$HOME"/dotfiles/install.sh packages
ask_continue "Proceed with installing MicroTex?" && install_microtex

exit 0
