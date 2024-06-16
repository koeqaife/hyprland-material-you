install_yay() {
    echo ":: Installing yay..."
    sudo pacman -Syu
    sudo pacman -S --needed base-devel git
    git clone https://aur.archlinux.org/yay.git /tmp/yay
    cd /tmp/yay
    makepkg -si --noconfirm --needed
}



if command -v yay &> /dev/null
then
    echo ":: Yay is installed"
    sleep 2
else
    echo ":: Yay is not installed!"
    sleep 2
    install_yay
fi

echo :: Installing packages
sleep 2

yay -S --noconfirm --needed \
    hyprland hyprshot hyprcursor hypridle hyprlang hyprpaper hyprpicker \
    hyprutils hyprwayland-scanner xdg-dbus-proxy xdg-desktop-portal \
    xdg-desktop-portal-gtk xdg-desktop-portal-hyprland xdg-user-dirs \
    xdg-utils libxdg-basedir python-pyxdg aylurs-gtk-shell swww gtk3 gtk4 \
    adw-gtk3 adw-gtk-theme libdbusmenu-gtk3 python-pip python-pillow sddm \
    sddm-theme-corners-git nautilus nm-connection-editor network-manager-applet \
    networkmanager gnome-bluetooth-3.0 wl-gammarelay bluez bluez-libs bluez-utils \
    cliphist wl-clipboard pywal-16-colors libadwaita swappy nwg-look alacritty \
    pavucontrol polkit-gnome brightnessctl man-pages gvfs xarchiver zip imagemagick \
    blueman fastfetch bibata-cursor-theme gum python-pywayland brave dbus \
    libdrm mesa fwupd

sleep 2

CHECK_FOLDERS="ags alacritty hypr swappy wal"
EXIT="NO"

for dir in $CHECK_FOLDERS; do
  if [ -d "$HOME/.config/$dir" ]; then
    echo ":: Error: directory $dir already exists in .config"
    EXIT="YES"
  fi
done
if [[ $EXIT == "YES" ]]; then
    echo ":: Please remove it or make a backup of it"
    exit 1
fi

pip install --break-system-packages https://github.com/T-Dynamos/materialyoucolor-python/archive/master.zip

echo ":: Setting SDDM and colors"
ln -s -f $HOME/dotfiles/wal $HOME/.config/wal
python -O $HOME/dotfiles/material-colors/generate.py --color "#00FF00"
sudo mkdir -p /etc/sddm.conf.d
sudo cp $HOME/dotfiles/sddm/sddm.conf /etc/sddm.conf.d/
sudo cp $HOME/dotfiles/sddm/sddm.conf /etc/
sudo chmod 777 /etc/sddm.conf.d/sddm.conf
sudo chmod 777 /etc/sddm.conf
chmod -R 777 /usr/share/sddm/themes/corners/backgrounds/
chmod 777 /usr/share/sddm/themes/corners/theme.conf
sh $HOME/dotfiles/sddm/scripts/wallpaper.sh

echo ":: Copying files"
sh $HOME/dotfiles/setup/copy.sh

echo ":: Creating links"
ln -s $HOME/dotfiles/ags $HOME/.config/ags
ln -s $HOME/dotfiles/alacritty $HOME/.config/alacritty
ln -s $HOME/dotfiles/hypr $HOME/.config/hypr
ln -s $HOME/dotfiles/swappy $HOME/.config/swappy

echo ":: Plugins"
sh $HOME/dotfiles/plugins.sh

echo ":: Vencord"
sh -c "$(curl -sS https://raw.githubusercontent.com/Vendicated/VencordInstaller/main/install.sh)"

echo ":: Services"

if [[ $(systemctl list-units --all -t service --full --no-legend "bluetooth.service" | sed 's/^\s*//g' | cut -f1 -d' ') == "bluetooth.service" ]];then
    echo ":: bluetooth.service already running."
else
    sudo systemctl enable bluetooth.service
    sudo systemctl start bluetooth.service
    echo ":: bluetooth.service activated successfully."    
fi

if [[ $(systemctl list-units --all -t service --full --no-legend "NetworkManager.service" | sed 's/^\s*//g' | cut -f1 -d' ') == "NetworkManager.service" ]];then
    echo ":: NetworkManager.service already running."
else
    sudo systemctl enable NetworkManager.service
    sudo systemctl start NetworkManager.service
    echo ":: NetworkManager.service activated successfully."    
fi

echo ":: User dirs"
xdg-user-dirs-update
echo ":: Done"


echo ":: Misc"
hyprctl reload
ags --init