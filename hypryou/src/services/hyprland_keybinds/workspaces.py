from src.services.hyprland_keybinds.common import (
    KeyBindHint, main_mod, Category
)

key_binds = (
    KeyBindHint(
        (main_mod, "0-9"),
        "Switch workspace",
        Category.WORKSPACES
    ),
    KeyBindHint(
        (main_mod, "0-9"),
        "Move window to workspace",
        Category.WORKSPACES
    ),
    KeyBindHint(
        (main_mod, "CTRL", "down"),
        "Switch to empty workspace",
        Category.WORKSPACES
    )
)
