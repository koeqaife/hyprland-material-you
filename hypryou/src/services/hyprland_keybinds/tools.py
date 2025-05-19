from src.services.hyprland_keybinds.common import KeyBind, main_mod, Category

key_binds = (
    KeyBind(
        (main_mod, "Z"),
        ("exec", "hypryouctl toggle_window players"),
        "Players",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "period"),
        ("exec", "hypryouctl open_window emojis"),
        "Emoji picker",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "CTRL", "C"),
        ("exec", "hypryouctl toggle_window cliphist"),
    ),
    KeyBind(
        (main_mod, "V"),
        ("exec", "hypryouctl toggle_window cliphist"),
        "Clipboard history",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "SLASH"),
        ("exec", "hypryouctl toggle_window keybindings"),
        "List of keybindings",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "CTRL", "W"),
        ("exec", "hypryouctl settings wallpaper"),
        "Open wallpaper settings",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "X"),
        ("exec", "hypryouctl toggle_window apps_menu"),
        "App Launcher",
        Category.TOOLS
    ),
    KeyBind(
        (main_mod, "W"),
        ("exec", "hypryouctl toggle_window sidebar"),
        "Sidebar",
        Category.TOOLS
    )
)
