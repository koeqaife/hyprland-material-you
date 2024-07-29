#!/bin/bash

# Path to your JSON file
JSON_FILE="$HOME/dotfiles/.settings/apps.json"

# Read the application type from the argument
APP_TYPE=$1

# Extract the corresponding application value from the JSON file using jq
APP=$(jq -r ".$APP_TYPE" "$JSON_FILE")

# Check if the application is defined in the JSON file
if [ "$APP" != "null" ]; then
    # Open the specified application
    $APP
else
    echo "No application defined for $APP_TYPE in $JSON_FILE"
fi
