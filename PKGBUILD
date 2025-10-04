# Maintainer: Koeqaife
pkgname=hypryou
_pkgname=hyprland-material-you
pkgver=2.1.5
pkgrel=1
pkgdesc="Dynamic and elegant desktop setup inspired by Material You, featuring auto-generated colors, fluid animations, and customizable user experience."
arch=('x86_64')
url="https://github.com/koeqaife/hyprland-material-you"
install=hypryou.install
license=('GPL3')
source=("$_pkgname::git+https://github.com/koeqaife/hyprland-material-you.git")
sha256sums=('SKIP')

depends=(
  'python'
  'dart-sass'
  'python-gobject'
  'python-pam'
  'gtk4'
  'libgirepository'
  'hyprland'
  'dbus'
  'dbus-glib'
  'python-pillow'
  'cairo'
  'libnm'
  'hyprsunset'
  'upower'
  'python-pywayland'
  'cliphist'
  'xdg-dbus-proxy'
  'xdg-desktop-portal'
  'xdg-desktop-portal-gtk'
  'xdg-desktop-portal-hyprland'
  'xdg-utils'
  'polkit-gnome'
  'adw-gtk-theme'
  'python-cairo'
  'networkmanager'
  'hyprshot'

  'gtk4-layer-shell'
  'python-materialyoucolor-git'
  'libastal-bluetooth-git'
  'libastal-wireplumber-git'
  'ttf-material-symbols-variable-git'
)

optdepends=(
  'hypryou-utils: A replacement of hyprland-qtutils with MaterialYou style'
  'hypryou-greeter: Config for Greetd'
  'ttf-meslo-nerd-font-powerlevel10k: Font for alacritty'
  'alacritty: I recommend to use this terminal'
  'tela-circle-icon-theme-nord: Default icons'
)

makedepends=(
  'cython'
  'git'
  'gcc'
  'python-setuptools'
)

build() {
  cd "$srcdir/$_pkgname/$pkgname"
  python utils_cy/setup.py build_ext --build-lib utils_cy --build-temp "$(mktemp -d)"
  cd "$srcdir/$_pkgname/build"

  COMMON_FLAGS="-Wall -Wextra -Wpedantic -Wshadow -Wformat=2 -Wcast-align -Wconversion -Wstrict-overflow=5 -O3 -flto -fno-plt -march=x86-64 -mtune=generic"

  gcc $COMMON_FLAGS client.c -o hypryouctl
  gcc $COMMON_FLAGS $(pkg-config --cflags --libs gtk4) -o hypryou-start hypryou-start.c
  gcc $COMMON_FLAGS $(pkg-config --cflags --libs gtk4) -o hypryou-crash-dialog crash-dialog.c
}

package() {
  mkdir -pv "$pkgdir/usr/bin"
  mkdir -pv "$pkgdir/usr/share/$pkgname"
  mkdir -pv "$pkgdir/usr/share/fonts/$pkgname"
  mkdir -pv "$pkgdir/usr/lib/$pkgname"
  mkdir -pv "$pkgdir/usr/share/licenses/$pkgname"
  mkdir -pv "$pkgdir/usr/share/wayland-sessions"

  cp -a "$srcdir/$_pkgname/$pkgname/." "$pkgdir/usr/lib/$pkgname/"
  cp -a "$srcdir/$_pkgname/$pkgname-assets/." "$pkgdir/usr/share/$pkgname/"
  cp -a "$srcdir/$_pkgname/assets/Google Sans/." "$pkgdir/usr/share/fonts/$pkgname/Google Sans/"
  cp -a "$srcdir/$_pkgname/assets/Google Sans Display/." "$pkgdir/usr/share/fonts/$pkgname/Google Sans Display/"
  cp -a "$srcdir/$_pkgname/assets/Google Sans Text/." "$pkgdir/usr/share/fonts/$pkgname/Google Sans Text/"

  install -Dm755 "$srcdir/$_pkgname/build/hypryouctl" "$pkgdir/usr/bin/hypryouctl"
  install -Dm755 "$srcdir/$_pkgname/build/hypryou-start" "$pkgdir/usr/bin/hypryou-start"
  install -Dm755 "$srcdir/$_pkgname/build/hypryou-crash-dialog" "$pkgdir/usr/bin/hypryou-crash-dialog"

  install -Dm644 "$srcdir/$_pkgname/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 "$srcdir/$_pkgname/assets/hypryou.desktop" "$pkgdir/usr/share/wayland-sessions/hypryou.desktop"
}
