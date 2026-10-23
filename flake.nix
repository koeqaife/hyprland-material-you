{
  description = "HyprYou (hyprland-material-you v2) - Material You Hyprland shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (s: f nixpkgs.legacyPackages.${s});

      mkHypryou = pkgs:
        let
          inherit (pkgs) lib;

          pythonRuntime = pkgs.python3.withPackages (ps: with ps; [
            pygobject3
            pycairo
            pyvips
            pywayland
            python-pam
            materialyoucolor
          ]);

          pythonBuild = pkgs.python3.withPackages (ps: with ps; [
            cython
            setuptools
          ]);

          runtimeTools = with pkgs; [
            pythonRuntime
            dart-sass
            hyprsunset
            hyprshot
            cliphist
            upower
            xdg-utils
            xdg-dbus-proxy
            polkit_gnome
            networkmanager
          ];
        in
        pkgs.stdenv.mkDerivation {
          pname = "hypryou";
          version = "2-${self.shortRev or self.dirtyShortRev or "dirty"}";
          src = self;

          nativeBuildInputs = with pkgs; [
            pkg-config
            gobject-introspection
            wrapGAppsHook4
            pythonBuild
          ];

          buildInputs = with pkgs; [
            gtk4
            glib
            cairo
            gdk-pixbuf
            pango
            graphene
            libadwaita
            gtk4-layer-shell
            networkmanager # libnm typelib
            upower
            dbus
            dbus-glib
            astal.io
            astal.astal4
            astal.bluetooth
            astal.wireplumber
            adw-gtk3
            vips
          ];

          postPatch = ''
            grep -rIl --exclude=flake.nix --exclude=flake.lock --exclude=PKGBUILD \
              -e '/usr/lib/hypryou' \
              -e '/usr/share/hypryou' \
              -e '/usr/bin/hypryou' \
              . | while read -r f; do
                sed -i \
                  -e "s|/usr/lib/hypryou|$out/lib/hypryou|g" \
                  -e "s|/usr/share/hypryou|$out/share/hypryou|g" \
                  -e "s|/usr/bin/hypryou|$out/bin/hypryou|g" \
                  "$f"
              done

            grep -rIl --include='*.py' '/usr/share/X11/xkb' . | while read -r f; do
              sed -i "s|/usr/share/X11/xkb|${pkgs.xkeyboard_config}/share/X11/xkb|g" "$f"
            done

            grep -rIl --include='*.py' 'libgtk4-layer-shell.so' . | while read -r f; do
              sed -i "s|libgtk4-layer-shell.so|${pkgs.gtk4-layer-shell}/lib/libgtk4-layer-shell.so|g" "$f"
            done
          '';

          buildPhase = ''
            runHook preBuild

            (cd hypryou && python utils_cy/setup.py build_ext \
              --build-lib utils_cy --build-temp "$(mktemp -d)")

            cd build
            CFLAGS="-Wall -Wextra -O3"
            gcc $CFLAGS client.c -o hypryouctl
            gcc $CFLAGS $(pkg-config --cflags --libs gtk4) -o hypryou-start hypryou-start.c
            gcc $CFLAGS $(pkg-config --cflags --libs gtk4) -o hypryou-crash-dialog crash-dialog.c
            cd ..

            runHook postBuild
          '';

          installPhase = ''
            runHook preInstall

            mkdir -p $out/bin $out/lib/hypryou $out/share/hypryou \
                     $out/share/fonts/hypryou $out/share/wayland-sessions

            cp -a hypryou/. $out/lib/hypryou/
            cp -a hypryou-assets/. $out/share/hypryou/

            cp -a "assets/Google Sans"         $out/share/fonts/hypryou/
            cp -a "assets/Google Sans Display" $out/share/fonts/hypryou/
            cp -a "assets/Google Sans Text"    $out/share/fonts/hypryou/

            install -Dm755 build/hypryouctl           $out/bin/hypryouctl
            install -Dm755 build/hypryou-start        $out/bin/hypryou-start
            install -Dm755 build/hypryou-crash-dialog $out/bin/hypryou-crash-dialog

            install -Dm644 assets/hypryou.desktop \
              $out/share/wayland-sessions/hypryou.desktop

            runHook postInstall
          '';

          preFixup = ''
            gappsWrapperArgs+=(
              --prefix PATH : ${lib.makeBinPath runtimeTools}
              --prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [
                pkgs.gtk4-layer-shell
                pkgs.gtk4
                pkgs.glib
                pkgs.vips
              ]}
            )
          '';

          passthru.providedSessions = [ "hypryou" ];

          meta = {
            description = "Material You inspired Hyprland desktop shell";
            homepage = "https://github.com/koeqaife/hyprland-material-you";
            license = lib.licenses.gpl3Only;
            platforms = lib.platforms.linux;
            mainProgram = "hypryou-start";
          };
        };
    in
    {
      packages = forAllSystems (pkgs: rec {
        hypryou = mkHypryou pkgs;
        default = hypryou;
      });

      overlays.default = final: _prev: { hypryou = mkHypryou final; };

      nixosModules.default = { config, lib, pkgs, ... }:
        let cfg = config.programs.hypryou; in
        {
          options.programs.hypryou = {
            enable = lib.mkEnableOption "the HyprYou (Material You) Hyprland session";

            package = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
              defaultText = lib.literalExpression "hypryou.packages.\${system}.default";
              description = "The hypryou package to use.";
            };

            extraPackages = lib.mkOption {
              type = lib.types.listOf lib.types.package;
              default = with pkgs; [ alacritty satty ];
              description = "Optional packages recommended upstream (terminal, screenshot editor).";
            };
          };

          config = lib.mkIf cfg.enable {
            services.displayManager.sessionPackages = [ cfg.package ];

            environment.systemPackages =
              [ cfg.package pkgs.adw-gtk3 ] ++ cfg.extraPackages;

            fonts.packages = [ cfg.package pkgs.material-symbols ];

            programs.hyprland.enable = lib.mkDefault true;
            networking.networkmanager.enable = lib.mkDefault true;
            services.upower.enable = lib.mkDefault true;
            security.polkit.enable = lib.mkDefault true;
            programs.dconf.enable = lib.mkDefault true;

            xdg.portal = {
              enable = true;
              extraPortals = [ pkgs.xdg-desktop-portal-gtk ];
            };
          };
        };
    };
}
