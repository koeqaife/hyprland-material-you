dark_icon="Tela-nord-dark"
light_icon="Tela-nord-light"

if [ "$1" == "--light" ]; then
  gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3
  gsettings set org.gnome.desktop.interface icon-theme "$light_icon"
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
else
  gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3-dark
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
  gsettings set org.gnome.desktop.interface icon-theme "$dark_icon"
fi
