#!/bin/bash

if ! grep -q "arch" /etc/os-release; then
    echo ":: This script is designed to run on Arch Linux."
    exit 1
fi

if [ ! -d "$HOME/dotfiles" ]; then
    echo ":: The directory $HOME/dotfiles does not exist."
    exit 1
fi

ask_continue() {
    local message=$1
    local exit_on_no=${2:-true}
    if gum confirm "$message"; then
        return 0
    else
        echo ":: Skipping $message."
        if $exit_on_no; then
            echo ":: Exiting script."
            exit 0
        else
            return 1
        fi
    fi
}

preference_select() {
    local type=$1
    shift
    local app_type=$1
    shift
    local options=("$@")

    gum style \
        --foreground 212 --border-foreground 212 --border normal \
        --align center --width 50 --margin "0 2" --padding "1 2" \
        "Select a(n) $type to install"

    CHOICE=$(gum choose "${options[@]}" "NONE")

    if [[ $CHOICE != "NONE" ]]; then
        yay -Syu --noconfirm --needed
        yay -S --noconfirm --needed $CHOICE
        python -O "$HOME"/dotfiles/ags/scripts/apps.py --"$app_type" $CHOICE
    else
        echo "Not installing a(n) $type..."
        sleep .4
    fi
}

install_yay() {
    echo ":: Installing yay..."
    sudo pacman -Syu --noconfirm
    sudo pacman -S --needed --noconfirm base-devel git
    git clone https://aur.archlinux.org/yay.git /tmp/yay
    cd /tmp/yay
    makepkg -si --noconfirm --needed
}

install_microtex() {
    cd ~/dotfiles/setup/MicroTex/
    makepkg -si
}

install_packages() {
    echo ":: Installing packages"
    sleep 1
    yay -Syu --noconfirm --needed
    yay -S --needed \
        hyprland hyprshot hyprcursor hypridle hyprlang hyprpaper hyprpicker hyprlock \
        hyprutils hyprwayland-scanner xdg-dbus-proxy xdg-desktop-portal \
        xdg-desktop-portal-gtk xdg-desktop-portal-hyprland xdg-user-dirs \
        xdg-utils libxdg-basedir python-pyxdg aylurs-gtk-shell swww gtk3 gtk4 \
        adw-gtk3 adw-gtk-theme libdbusmenu-gtk3 python-pip python-pillow sddm \
        sddm-theme-corners-git nm-connection-editor network-manager-applet \
        networkmanager gnome-bluetooth-3.0 wl-gammarelay-rs bluez bluez-libs bluez-utils \
        cliphist wl-clipboard libadwaita swappy nwg-look \
        pavucontrol polkit-gnome brightnessctl man-pages gvfs xarchiver zip imagemagick \
        blueman fastfetch bibata-cursor-theme gum python-pywayland dbus \
        libdrm mesa fwupd bun-bin pipewire wireplumber udiskie \
        lm_sensors gnome-system-monitor playerctl ttf-meslo-nerd ttf-google-sans \
        ttf-font-awesome ttf-opensans ttf-roboto lshw ttf-material-symbols-variable-git \
        fontconfig dart-sass ttf-meslo-nerd-font-powerlevel10k cpio meson cmake \
        python-materialyoucolor-git gtksourceview3 gtksourceviewmm cairomm \
        gtkmm3 tinyxml2 python-requests python-numpy
}

setup_yay() {
    if command -v yay &>/dev/null; then
        echo ":: Yay is installed"
        sleep 1
    else
        echo ":: Yay is not installed!"
        sleep 1
        install_yay
    fi
}

setup_sensors() {
    sudo sensors-detect --auto >/dev/null
}

check_config_folders() {
    local CHECK_CONFIG_FOLDERS="ags alacritty hypr swappy"
    local DATETIME=$(date '+%Y-%m-%d %H:%M:%S')
    local EXISTING="NO"

    mkdir -p "$HOME/.backup/$DATETIME/"

    for dir in $CHECK_CONFIG_FOLDERS; do
        if [ -d "$HOME/.config/$dir" ]; then
            echo ":: Attention: directory $dir already exists in .config"
            mv $HOME/.config/$dir "$HOME/.backup/$DATETIME/"
            EXISTING="YES"
        fi
    done

    if [[ $EXISTING == "YES" ]]; then
        echo ":: Old config folder(s) backed up at ~/.backup folder"
    fi
}

install_icon_theme() {
    gum style \
        --foreground 212 --border-foreground 212 --border normal \
        --align center --width 50 --margin "0 2" --padding "1 2" \
        "Select an icon theme to install"

    CHOICE=$(gum choose "Tela Icon Theme" "Papirus Icon Theme" "Adwaita Icon Theme")

    if [[ $CHOICE == "Tela Icon Theme" ]]; then
        echo ":: Installing Tela icons..."
        mkdir -p /tmp/install
        cd /tmp/install
        git clone https://github.com/vinceliuice/Tela-icon-theme
        cd Tela-icon-theme

        gum style \
            --foreground 212 --border-foreground 212 --border normal \
            --align center --width 50 --margin "0 2" --padding "1 2" \
            "Select a color theme"

        COLOR_CHOICE=$(gum choose --height=20 "nord" "black" "blue" "green" "grey" "orange" \
            "pink" "purple" "red" "yellow" "brown")

        ./install.sh $COLOR_CHOICE
        echo -e "Tela-$COLOR_CHOICE-dark\nTela-$COLOR_CHOICE-light" >$HOME/dotfiles/.settings/icon-theme
        cd $HOME/dotfiles

    elif [[ $CHOICE == "Papirus Icon Theme" ]]; then
        yay -S --noconfirm --needed papirus-icon-theme papirus-folders

        echo -e "Papirus-Dark\nPapirus-Light" >$HOME/dotfiles/.settings/icon-theme

        gum style \
            --foreground 212 --border-foreground 212 --border normal \
            --align center --width 50 --margin "0 2" --padding "1 2" \
            "Select a color theme"

        COLOR_CHOICE=$(gum choose --height=20 "black" "blue" "cyan" "green" "grey" "indigo" \
            "brown" "purple" "nordic" "pink" "red" "deeporange" "white" "yellow")

        papirus-folders -C $COLOR_CHOICE

    else
        yay -S --noconfirm --needed adwaita-icon-theme
        echo -e "Adwaita\nAdwaita" >$HOME/dotfiles/.settings/icon-theme
    fi
}

setup_colors() {
    echo ":: Setting colors"
    python -O $HOME/dotfiles/material-colors/generate.py --color "#0000FF"
}

setup_sddm() {
    echo ":: Setting SDDM"
    sudo mkdir -p /etc/sddm.conf.d
    sudo cp $HOME/dotfiles/sddm/sddm.conf /etc/sddm.conf.d/
    sudo cp $HOME/dotfiles/sddm/sddm.conf /etc/
    sudo chmod 777 /etc/sddm.conf.d/sddm.conf
    sudo chmod 777 /etc/sddm.conf
    sudo chmod -R 777 /usr/share/sddm/themes/corners/
    "$HOME"/dotfiles/sddm/scripts/wallpaper.sh
}

copy_files() {
    echo ":: Copying files"
    mkdir -p $HOME/.config
    "$HOME"/dotfiles/setup/copy.sh
}

create_links() {
    echo ":: Creating links"
    ln -f $HOME/dotfiles/electron-flags.conf $HOME/.config/electron-flags.conf
    if [ -d "$HOME/wallpaper" ]; then
        echo ":: Error: directory wallpaper already exists in home"
    else
        cp -r $HOME/dotfiles/wallpapers $HOME/wallpaper
    fi
    ln -s $HOME/dotfiles/ags $HOME/.config/ags
    ln -s $HOME/dotfiles/alacritty $HOME/.config/alacritty
    ln -s $HOME/dotfiles/hypr $HOME/.config/hypr
    ln -s $HOME/dotfiles/swappy $HOME/.config/swappy
}

install_vencord() {
    echo ":: Vencord"
    sh -c "$(curl -sS https://raw.githubusercontent.com/Vendicated/VencordInstaller/main/install.sh)"
    mkdir -p $HOME/.config/Vencord/settings/
    ln -f $HOME/.cache/material/material-discord.css $HOME/.config/Vencord/settings/quickCss.css
}

remove_gtk_buttons() {
    echo ":: Remove window close and minimize buttons in GTK"
    gsettings set org.gnome.desktop.wm.preferences button-layout ':'
}

setup_services() {
    echo ":: Services"

    if systemctl is-active --quiet bluetooth.service; then
        echo ":: bluetooth.service already running."
    else
        sudo systemctl enable bluetooth.service
        sudo systemctl start bluetooth.service
        echo ":: bluetooth.service activated successfully."
    fi

    if systemctl is-active --quiet NetworkManager.service; then
        echo ":: NetworkManager.service already running."
    else
        sudo systemctl enable NetworkManager.service
        sudo systemctl start NetworkManager.service
        echo ":: NetworkManager.service activated successfully."
    fi
}

update_user_dirs() {
    echo ":: User dirs"
    xdg-user-dirs-update
}

misc_tasks() {
    echo ":: Misc"
    hyprctl reload
    ags --init
}

main() {
    if [[ $1 == "packages" ]]; then
        setup_yay
        install_packages
        exit 0
    fi

    setup_yay
    if ! command -v gum &>/dev/null; then
        echo ":: gum not installed"
        sudo pacman -S gum
    fi

    ask_continue "Proceed with installing packages?" false && install_packages
    preference_select "file manager" "filemanager" "nautilus" "dolphin" "thunar"
    preference_select "internet browser" "browser" "brave" "firefox" "google-chrome" "chromium"
    preference_select "terminal emulator" "terminal" "alacritty" "kitty" "konsole"
    ask_continue "Proceed with installing MicroTex?" false && install_microtex
    ask_continue "Proceed with setting up sensors?" false && setup_sensors
    ask_continue "Proceed with checking config folders?*" && check_config_folders
    ask_continue "Proceed with installing icon themes?" false && install_icon_theme
    ask_continue "Proceed with setting up colors?*" && setup_colors
    ask_continue "Proceed with setting up SDDM?" false && setup_sddm
    ask_continue "Proceed with copying files?*" && copy_files
    ask_continue "Proceed with creating links?*" && create_links
    ask_continue "Proceed with installing Vencord?" false && install_vencord
    ask_continue "Proceed with removing GTK buttons?" false && remove_gtk_buttons
    ask_continue "Proceed with setting up services?*" && setup_services
    ask_continue "Proceed with updating user directories?*" && update_user_dirs
    ask_continue "Proceed with miscellaneous tasks?*" && misc_tasks

    echo "Please restart your PC"
}

main "$@"
