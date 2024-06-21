#!/bin/bash
NOTIFICATION_SENT_FILE="/tmp/git_update_notification_sent"

"$HOME"/dotfiles/scripts/check_updates.sh > /dev/null
status=$?

if [ $status -eq 0 ]; then
    echo ":: No updates available."
elif [ $status -eq 1 ]; then
    echo ":: Cannot update: Changes detected in files."
    echo ":: You can write \"$ git diff-index --name-only HEAD --\" to see which files have changed"
elif [ $status -eq 2 ]; then
    echo ":: Updates are available. Performing git pull..."
    git pull && $HOME/dotfiles/setup/after_update.sh
    rm -f $NOTIFICATION_SENT_FILE
elif [ $status -eq 3 ]; then
    echo ":: Branches have diverged. Manual intervention may be required."
else
    echo ":: Unknown error."
fi