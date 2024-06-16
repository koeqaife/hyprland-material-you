#!/bin/bash
GENERATOR="$HOME/dotfiles/material-colors/generate.py"
FILE="$HOME/dotfiles/.settings/color-scheme"
VALUE=$(cat $FILE)

if [ "$VALUE" == "dark" ]; then
    python -O $GENERATOR -R --color-scheme light
    echo "light" > $FILE
    
elif [ "$VALUE" == "light" ]; then
    python -O $GENERATOR -R --color-scheme dark
    echo "dark" > $FILE
else
    echo "Неизвестное значение: $VALUE"
fi
