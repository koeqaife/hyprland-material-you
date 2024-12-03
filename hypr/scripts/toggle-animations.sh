#!/bin/bash
cache_file="/tmp/toggle_animation"
if [ -f $cache_file ]; then
    hyprctl keyword animations:enabled true
    agsv1 -r 'enableAnimations(true)'
    rm $cache_file
else
    hyprctl keyword animations:enabled false
    agsv1 -r 'enableAnimations(false)'
    touch $cache_file
fi
