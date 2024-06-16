wal_folder="$HOME"/.cache/wal
telegram_theme_cache="$HOME"/.cache/telegram-theme

bg_color_file="$HOME/.cache/wal/bg-color"
bg_color=$(cat "$bg_color_file")
magick -size 256x256 "xc:$bg_color" ~/.cache/wal/colors-tiled.png

mkdir -p $telegram_theme_cache

cp $wal_folder/colors.tdesktop-theme $telegram_theme_cache/colors.tdesktop-theme
cp $wal_folder/colors-tiled.png $telegram_theme_cache/tiled.png

zip -q -j $telegram_theme_cache/pallete.tdesktop-theme  $telegram_theme_cache/tiled.png $telegram_theme_cache/colors.tdesktop-theme