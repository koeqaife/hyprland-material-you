#!/bin/bash
GENERATOR="$HOME/dotfiles/material-colors/generate.py"
FILE="$HOME/dotfiles/.settings/color-scheme"
SCHEME_FILE="$HOME/dotfiles/.settings/generation-scheme"
GENERATION_SCHEME="tonalSpot"
GENERATION_SCHEME=$(cat $SCHEME_FILE)
toggle() {
    VALUE=$(cat $FILE)

    if [ "$VALUE" == "dark" ]; then
        python -O $GENERATOR -R --color-scheme light --scheme $GENERATION_SCHEME
        echo "light" >$FILE

    elif [ "$VALUE" == "light" ]; then
        python -O $GENERATOR -R --color-scheme dark --scheme $GENERATION_SCHEME
        echo "dark" >$FILE
    else
        echo "Unknown value: $VALUE"
    fi
}

set() {
    python -O $GENERATOR -R --color-scheme $1 --scheme $GENERATION_SCHEME
    echo $1 >$FILE
}

if [[ "$1" == "--toggle" ]]; then
    toggle
elif [[ "$1" == "--set" ]]; then
    set $2
fi
