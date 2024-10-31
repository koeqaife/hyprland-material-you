#!/bin/bash
NOTIFICATION_SENT_FILE="/tmp/git_update_notification_sent"
FORCE_UPDATE=false

if [ "$1" == "--force" ]; then
    FORCE_UPDATE=true
fi

perform_update() {
    echo ":: Removing skip-worktree flags..."
    git ls-files -v | grep '^S' | awk '{print $2}' | xargs git update-index --no-skip-worktree

    BACKUP_DIR="$HOME/dotfiles/.backup"
    TIMESTAMP=$(date +%F_%H-%M-%S)

    if [ -d "$BACKUP_DIR" ]; then
        NEW_BACKUP_DIR="${BACKUP_DIR}_old/${TIMESTAMP}"
        mkdir -p "$NEW_BACKUP_DIR"
        echo ":: Moving existing backup to $NEW_BACKUP_DIR..."
        mv "$BACKUP_DIR" "$NEW_BACKUP_DIR"
    fi

    echo ":: Creating backup of modified files..."
    mkdir -p "$BACKUP_DIR"

    git diff --name-only | while read -r file; do
        if [ -f "$file" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$file" "$BACKUP_DIR/$file"
        fi
    done

    echo ":: Performing repository update..."
    git fetch origin

    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

    echo ":: Performing hard reset..."
    git reset --hard origin/$CURRENT_BRANCH

    echo ":: Running post-update script..."
    "$HOME/dotfiles/setup/after_update.sh"

    rm -f $NOTIFICATION_SENT_FILE
}

"$HOME/dotfiles/scripts/check_updates.sh" >/dev/null
status=$?

case $status in
0)
    echo ":: No updates available."
    if [ "$FORCE_UPDATE" == true ]; then
        echo ":: Forcing update despite no updates..."
        perform_update
    fi
    ;;
1)
    echo ":: Cannot update: Changes detected in files."
    if [ "$FORCE_UPDATE" == true ]; then
        echo ":: Forcing update despite local changes..."
        perform_update
    else
        echo ":: You can write \"$ git diff-index --name-only HEAD --\" to see which files have changed"
        echo ":: Use --force to ignore changes"
        exit 1
    fi
    ;;
2)
    echo ":: Updates are available."
    perform_update
    ;;
3)
    echo ":: Branches have diverged. Manual intervention may be required."
    if [ "$FORCE_UPDATE" == true ]; then
        echo ":: Forcing update despite branch divergence..."
        perform_update
    fi
    ;;
*)
    echo ":: Unknown error."
    ;;
esac
