pkgname=hypryou
_pkgname=hyprland-material-you
pkgver=2.0.0
pkgrel=1
pkgdesc="Dynamic and elegant desktop setup inspired by Material You, featuring auto-generated colors, fluid animations, and customizable user experience."
arch=('x86_64')
url="https://github.com/koeqaife/hyprland-material-you"
license=('GPL3')

depends=(
  'python'
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

  'gtk4-layer-shell'
  'python-materialyoucolor-git'
  'libastal-bluetooth-git'
  'libastal-wireplumber-git'
  'ttf-material-symbols-variable-git'
)

optdepends=(
  'hypryou-utils: A replacement of hyprland-qtutils with MaterialYou style'
  'hypryou-greeter: Config for Greetd'
)

makedepends=(
  'dart-sass'
  'cython'
)

prepare() {
  rm -rf "$srcdir/$_pkgname"
  git clone --depth=1 https://github.com/koeqaife/hyprland-material-you.git "$srcdir/$_pkgname" # We don't need the full history for this repository that's why I don't use source=()
}


build() {
  cd "$srcdir/$_pkgname/$pkgname"
  python utils_cy/setup.py build_ext --build-lib utils_cy --build-temp $(mktemp -d)
  cd "$srcdir/$_pkgname/build"

  gcc -Wall -Wextra -Wpedantic -Wshadow -Wformat=2 -Wcast-align -Wconversion -Wstrict-overflow=5 -O3 -march=native -flto -fno-plt client.c -o hypryouctl
  gcc -O3 -march=native -flto -fno-plt $(pkg-config --cflags --libs gtk4) -Wall -Wextra -Wpedantic -Wshadow -Wformat=2 -Wcast-align -Wconversion -Wstrict-overflow=5 -o hypryou-start hypryou-start.c
  gcc -O3 -march=native -flto -fno-plt $(pkg-config --cflags --libs gtk4) -Wall -Wextra -Wpedantic -Wshadow -Wformat=2 -Wcast-align -Wconversion -Wstrict-overflow=5 -o hypryou-crash-dialog crash-dialog.c
}

package() {
  mkdir -pv "$pkgdir/usr/bin"
  mkdir -pv "$pkgdir/usr/lib/$pkgname"
  mkdir -pv "$pkgdir/usr/share/licenses/$pkgname"
  mkdir -pv "$pkgdir/usr/share/wayland-sessions"

  cp -a "$srcdir/$_pkgname/$pkgname/." "$pkgdir/usr/lib/$pkgname/"

  install -Dm755 "$srcdir/$_pkgname/build/hypryouctl" "$pkgdir/usr/bin/hypryouctl"
  install -Dm755 "$srcdir/$_pkgname/build/hypryou-start" "$pkgdir/usr/bin/hypryou-start"
  install -Dm755 "$srcdir/$_pkgname/build/hypryou-crash-dialog" "$pkgdir/usr/bin/hypryou-crash-dialog"

  install -Dm644 "$srcdir/$_pkgname/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 "$srcdir/$_pkgname/assets/hypryou.desktop" "$pkgdir/usr/share/wayland-sessions/hypryou.desktop"
}
