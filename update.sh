#!/bin/bash
NOTIFICATION_SENT_FILE="/tmp/git_update_notification_sent"
FORCE_UPDATE=false

if [ "$1" == "--force" ]; then
    FORCE_UPDATE=true
fi

perform_update() {
    echo ":: Performing git pull..."
    git pull && "$HOME/dotfiles/setup/after_update.sh"
    rm -f $NOTIFICATION_SENT_FILE
}

"$HOME/dotfiles/scripts/check_updates.sh" >/dev/null
status=$?

case $status in
0)
    echo ":: No updates available."
    ;;
1)
    if [ "$FORCE_UPDATE" == true ]; then
        perform_update
    else
        echo ":: Cannot update: Changes detected in files."
        echo ":: You can write \"$ git diff-index --name-only HEAD --\" to see which files have changed"
        echo ":: use --force to ignore changes"
        exit 1
    fi
    ;;
2)
    echo ":: Updates are available."
    perform_update
    ;;
3)
    echo ":: Branches have diverged. Manual intervention may be required."
    ;;
*)
    echo ":: Unknown error."
    ;;
esac
