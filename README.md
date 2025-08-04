# HyprYou

![GitHub commit activity](https://img.shields.io/github/commit-activity/m/koeqaife/hyprland-material-you?style=for-the-badge&labelColor=%23424242&color=%23B2FF59)
![GitHub repo size](https://img.shields.io/github/repo-size/koeqaife/hyprland-material-you?style=for-the-badge&labelColor=%23424242&color=%2384FFFF)
![GitHub Repo stars](https://img.shields.io/github/stars/koeqaife/hyprland-material-you?style=for-the-badge&labelColor=%23424242&color=%23B9F6CA)
![GitHub contributors](https://img.shields.io/github/contributors/koeqaife/hyprland-material-you?style=for-the-badge&labelColor=%23424242&color=%23FFAB40)
![GitHub License](https://img.shields.io/github/license/koeqaife/hyprland-material-you?style=for-the-badge&labelColor=%23424242&color=%23FF9E80)

HyprYou (hyprland-material-you v2). It aims to provide a modern, feature-rich, and visually appealing desktop configuration. Here are some key features:

- **Material You Colors**: The project generates colors for your apps based on you wallpapers or settings.
- **Fluid Animations**: Expect natural and fluid animations throughout the desktop experience.
- **Design**: The design wherever possible is made by [Material 3 design](https://m3.material.io/)

> [!WARNING]
> This is **beta** version.

> [!NOTE]
> I'm doing everything by myself and **for free**.  
> If you want to support me, you can buy me a coffee on [**ko-fi**](https://ko-fi.com/koeqaife).

> [!NOTE]
> If you want to talk or to check devlogs go to our Discord server  
> <https://discord.gg/nCK3sh8mNU>

## How to install

<details>
    <summary>Manual installation</summary>

- Clone repository: `git clone --depth=1 https://github.com/koeqaife/hyprland-material-you.git`
- Install all dependencies from depends.txt
- Build Cython code by using `build.sh` in `hypryou/`
- Then copy `hypryou` to `/usr/lib/hypryou`
- Then use `build.sh` in `build`
- Move `hypryouctl`, `hypryou-start`, `hypryou-crash-dialog` to `/usr/bin`
- Copy `assets/hypryou.desktop` to `/usr/share/wayland-sessions/`
- And run it as `HyprYou` from your window manager (Not `Hyprland`!!)
- Optional:
  - You can build `hypryou-utils` or `hypryou-greeter` if you want  
    > By using `makepkg -si` in `greeter` for `hypryou-greeter` or in `hypryou-utils`

</details>
<details>
    <summary>Automatic installation (Arch)</summary>

Use `makepkg -si`
</details>

## Things left to do

> Almost everything is done, you can already use everything

- DBus menu for tray
- Code improvements
