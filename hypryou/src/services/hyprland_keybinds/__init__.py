from src.services.hyprland_keybinds import (
    actions, apps, fn_keys, tools, windows
)

key_binds = (
    *actions.key_binds,
    *fn_keys.key_binds,
    *tools.key_binds,
    *windows.key_binds,
    *apps.key_binds,
)
