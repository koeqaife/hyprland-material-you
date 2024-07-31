#!/bin/bash

cd $HOME/dotfiles

OLD_SETTINGS=$HOME/dotfiles/.settings/old

# Remove $OLD_SETTINGS folder if it is empty
if [ -z "$(ls -A "$OLD_SETTINGS")" ]; then
  rmdir "$OLD_SETTINGS"
fi

git update-index --skip-worktree $HOME/dotfiles/.settings/*
git update-index --skip-worktree $HOME/dotfiles/hypr/conf/custom/*
git update-index --skip-worktree $HOME/dotfiles/hypr/conf/apps.conf
git update-index --skip-worktree $HOME/dotfiles/alacritty/alacritty.toml
git update-index --skip-worktree $HOME/dotfiles/wallpapers/*
git update-index --skip-worktree $HOME/dotfiles/hypr/hypridle.conf
git update-index --skip-worktree $HOME/dotfiles/electron-flags.conf
git update-index --skip-worktree $HOME/dotfiles/ags/README.md
git update-index --skip-worktree $HOME/dotfiles/ags/tsconfig.json

git fetch
UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")
BASE=$(git merge-base @ "$UPSTREAM")

if git diff-index --quiet HEAD --; then
    echo "The files have not been modified. You can update"
else
    echo "The files have been modified. You can't update"
    echo "You can write \"$ git diff-index --name-only HEAD --\" to see which files have changed"
    exit 1
fi

if [ $LOCAL = $REMOTE ]; then
    echo "You have the latest version"
    exit 0
elif [ $LOCAL = $BASE ]; then
    echo "You can run $ git pull"
    exit 2
else
    echo "Your branch and the remote branch have diverged."
    exit 3
fi
