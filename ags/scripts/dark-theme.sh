#!/bin/bash
GENERATOR="$HOME/dotfiles/material-colors/generate.py"
FILE="$HOME/dotfiles/.settings/color-scheme"
toggle() {
    VALUE=$(cat $FILE)

    if [ "$VALUE" == "dark" ]; then
        python -O $GENERATOR -R --color-scheme light
        echo "light" > $FILE
        
    elif [ "$VALUE" == "light" ]; then
        python -O $GENERATOR -R --color-scheme dark
        echo "dark" > $FILE
    else
        echo "Unknown value: $VALUE"
    fi
}

set() {
    python -O $GENERATOR -R --color-scheme $1
    echo $1 > $FILE
}

if [[ "$1" == "--toggle" ]]; then
    toggle
    elif [[ "$1" == "--set" ]]; then
    set $2
fi

