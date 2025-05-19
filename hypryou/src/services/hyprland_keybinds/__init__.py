from src.services.hyprland_keybinds import (
    actions, apps, fn_keys, misc, tools, windows, workspaces
)

key_binds = (
    *actions.key_binds,
    *apps.key_binds,
    *fn_keys.key_binds,
    *misc.key_binds,
    *tools.key_binds,
    *windows.key_binds,
    *workspaces.key_binds
)
