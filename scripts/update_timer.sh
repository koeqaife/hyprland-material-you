NOTIFICATION_SENT_FILE="/tmp/git_update_notification_sent"

dotfiles_update() {
    notify-send -u critical --icon "software-update-available-symbolic" \
        "Dotfiles update available" \
        "If you haven't changed the dotfiles folder, you can write \n\$ ~/dotfiles/update.sh"
}

check_and_notify_update() {
    cd "$DOTFILES_DIR" || exit 1
    $HOME/dotfiles/scripts/check_updates.sh >/dev/null
    status=$?

    if [ $status -eq 2 ]; then
        if ! [ -f "$NOTIFICATION_SENT_FILE" ]; then
            dotfiles_update
            touch "$NOTIFICATION_SENT_FILE"
        fi
    elif [ $status -eq 1 ]; then
        exit 1
    fi
}

while true; do
    check_and_notify_update
    sleep 60
done
