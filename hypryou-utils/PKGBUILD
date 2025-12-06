# Maintainer: koeqaife
pkgname=hypryou-utils
pkgver=1.0.0
pkgrel=3
pkgdesc="Replacement for hyprland-qtutils as part of HyprYou project"
arch=('x86_64' 'aarch64')
url="https://github.com/koeqaife/hyprland-material-you"
license=('GPL3')
depends=('gtk4')
provides=('hyprland-qtutils' 'hyprland-guiutils')
conflicts=('hyprland-qtutils' 'hyprland-guiutils')
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/koeqaife/hyprland-material-you/archive/refs/heads/v2.tar.gz")
sha256sums=('SKIP')
makedepends=(
  'git'
  'gcc'
)

build() {
    gcc "${srcdir}/hyprland-material-you-2/hypryou-utils/hyprland-dialog.c" -o hyprland-dialog $(pkg-config --cflags --libs gtk4) \
        -Wall -Wextra -Wpedantic -Wshadow -Wformat=2 -Wcast-align -Wconversion -Wstrict-overflow=5 -O2
}

package() {
    install -Dm755 hyprland-dialog "${pkgdir}/usr/bin/hyprland-dialog"
}
