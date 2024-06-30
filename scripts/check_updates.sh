#!/bin/bash

cd $HOME/dotfiles

git update-index --skip-worktree $HOME/dotfiles/.settings/*
git update-index --skip-worktree $HOME/dotfiles/hypr/conf/custom.conf
git update-index --skip-worktree $HOME/dotfiles/hypr/conf/apps.conf
git update-index --skip-worktree $HOME/dotfiles/alacritty/alacritty.toml
git update-index --skip-worktree $HOME/dotfiles/wallpapers/*
git update-index --skip-worktree $HOME/dotfiles/hypr/hypridle.conf

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


