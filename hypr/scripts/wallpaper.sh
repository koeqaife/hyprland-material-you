#!/bin/bash
# Cache file for holding the current wallpaper
cache_file="$HOME/.cache/current_wallpaper"
blurred="$HOME/.cache/blurred_wallpaper.png"
square="$HOME/.cache/square_wallpaper.png"
rasi_file="$HOME/.cache/current_wallpaper.rasi"
blur_file="$HOME/dotfiles/.settings/blur.sh"
color_scheme_file="$HOME/dotfiles/.settings/color-scheme"

blur="50x30"
blur=$(cat $blur_file)
color_scheme=$(cat $color_scheme_file)
generator="$HOME/dotfiles/material-colors/generate.py"

# Create cache file if not exists
if [ ! -f $cache_file ] ;then
    touch $cache_file
    echo "$HOME/wallpaper/default.jpg" > "$cache_file"
fi

# Create rasi file if not exists
if [ ! -f $rasi_file ] ;then
    touch $rasi_file
    echo "* { current-image: url(\"$HOME/wallpaper/default.jpg\", height); }" > "$rasi_file"
fi

current_wallpaper=$(cat "$cache_file")

case $1 in

    # Load wallpaper from .cache of last session 
    "init")
        sleep 1
        if [ -f $cache_file ]; then
            python -O $generator --image $current_wallpaper --color-scheme $color_scheme 
        else
            python -O $generator --image ~/wallpaper/ --color-scheme $color_scheme 
        fi
    ;;

    # Select wallpaper with rofi
    "select")
        sleep 0.2
        selected=$( find "$HOME/wallpaper" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) -exec basename {} \; | sort -R | while read rfile
        do
            echo -en "$rfile\x00icon\x1f$HOME/wallpaper/${rfile}\n"
        done | rofi -dmenu -i -replace -config ~/dotfiles/rofi/config-wallpaper.rasi)
        if [ ! "$selected" ]; then
            echo "No wallpaper selected"
            exit
        fi
        python -O $generator --image ~/wallpaper/$selected --color-scheme $color_scheme 
    ;;

    # Randomly select wallpaper 
    *)
        python -O $generator --image ~/wallpaper/ --color-scheme $color_scheme 
    ;;

esac

# ----------------------------------------------------- 
# Load current pywal color scheme
# ----------------------------------------------------- 
source "$HOME/.cache/wal/colors.sh"
echo ":: Wallpaper: $wallpaper"

# ----------------------------------------------------- 
# get wallpaper image name
# ----------------------------------------------------- 
newwall=$(echo $wallpaper | sed "s|$HOME/wallpaper/||g")

# ----------------------------------------------------- 
# Set the new wallpaper
# -----------------------------------------------------
transition_type="wipe"
# transition_type="outer"
# transition_type="random"

wallpaper_engine=$(cat $HOME/dotfiles/.settings/wallpaper-engine.sh)
if [ "$wallpaper_engine" == "swww" ] ;then
    # swww
    echo ":: Using swww"
    swww img $wallpaper \
        --transition-bezier .43,1.19,1,.4 \
        --transition-fps=60 \
        --transition-type=$transition_type \
        --transition-duration=0.7 \
        --transition-pos "$( hyprctl cursorpos )"
elif [ "$wallpaper_engine" == "hyprpaper" ] ;then
    # hyprpaper
    echo ":: Using hyprpaper"
    killall hyprpaper
    wal_tpl=$(cat $HOME/dotfiles/.settings/hyprpaper.tpl)
    output=${wal_tpl//WALLPAPER/$wallpaper}
    echo "$output" > $HOME/dotfiles/hypr/hyprpaper.conf
    hyprpaper &
else
    echo ":: Wallpaper Engine disabled"
fi

if [ "$1" == "init" ] ;then
    echo ":: Init"
else
    sleep 1
    notify-send "Changing wallpaper ..." "with image $newwall"  
    
    # ----------------------------------------------------- 
    # Reload Hyprctl.sh
    # -----------------------------------------------------
    $HOME/.config/ml4w-hyprland-settings/hyprctl.sh &
fi

# ----------------------------------------------------- 
# Created blurred wallpaper
# -----------------------------------------------------
if [ "$1" == "init" ] ;then
    echo ":: Init"
else
    notify-send "Creating blurred version ..." "with image $newwall"  
fi

magick $wallpaper -resize 75% $blurred
echo ":: Resized to 75%"
if [ ! "$blur" == "0x0" ] ;then
    magick $blurred -blur $blur $blurred
    echo ":: Blurred"
fi

# ----------------------------------------------------- 
# Created quare wallpaper
# -----------------------------------------------------
if [ "$1" == "init" ] ;then
    echo ":: Init"
else
    notify-send "Creating square version ..." "with image $newwall"  
fi
magick $wallpaper -gravity Center -extent 1:1 $square
echo ":: Square version created"

# ----------------------------------------------------- 
# Write selected wallpaper into .cache files
# ----------------------------------------------------- 
echo "$wallpaper" > "$cache_file"
echo "* { current-image: url(\"$blurred\", height); }" > "$rasi_file"

# ----------------------------------------------------- 
# Send notification
# ----------------------------------------------------- 

if [ "$1" == "init" ] ;then
    echo ":: Init"
else
    notify-send "Changing SDDM theme..." "with image $newwall"  
fi

if [ "$1" == "init" ] ;then
    echo ":: Init"
    /home/mrdan/dotfiles/sddm/scripts/wallpaper.sh init
else
    /home/mrdan/dotfiles/sddm/scripts/wallpaper.sh
    notify-send "Wallpaper procedure complete!" "with image $newwall"  
fi
echo ":: SDDM theme changed"

echo "DONE!"
