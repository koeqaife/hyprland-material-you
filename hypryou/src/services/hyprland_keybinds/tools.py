from src.services.hyprland_keybinds.common import (
    KeyBind, main_mod, Category,
    make_exec
)

key_binds = (
    KeyBind(
        (main_mod, "Z"),
        make_exec("hypryouctl toggle_window players"),
        "Players",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "period"),
        make_exec("hypryouctl open_window emojis"),
        "Emoji picker",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "CTRL", "C"),
        make_exec("hypryouctl toggle_window cliphist"),
    ),
    KeyBind(
        (main_mod, "V"),
        make_exec("hypryouctl toggle_window cliphist"),
        "Clipboard history",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "SLASH"),
        make_exec("hypryouctl toggle_window keybindings"),
        "List of keybindings",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "CTRL", "W"),
        make_exec("hypryouctl settings wallpaper"),
        "Open wallpaper settings",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "SPACE"),
        make_exec("hypryouctl toggle_window apps_menu"),
        "App Launcher",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "W"),
        make_exec("hypryouctl toggle_window sidebar"),
        "Sidebar",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "A"),
        make_exec("hypryouctl toggle_window clients"),
        "Opened windows",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "D"),
        make_exec("hypryouctl settings"),
        "Open settings",
        Category.TOOLS
    )
)
