#!/bin/bash
cache_folder="$HOME"/.cache/material
telegram_theme_cache="$HOME"/.cache/telegram-theme

bg_color_file="$cache_folder/bg-color"
bg_color=$(cat "$bg_color_file")
magick -size 256x256 "xc:$bg_color" $telegram_theme_cache/tiled.png

mkdir -p $telegram_theme_cache

cp $cache_folder/colors.tdesktop-theme $telegram_theme_cache/colors.tdesktop-theme

zip -q -j $telegram_theme_cache/pallete.tdesktop-theme $telegram_theme_cache/tiled.png $telegram_theme_cache/colors.tdesktop-theme
