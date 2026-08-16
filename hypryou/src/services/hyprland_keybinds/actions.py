from src.services.hyprland_keybinds.common import (
    KeyBind, main_mod, Category,
    make_exec
)
key_binds = (
    KeyBind(
        (main_mod, "SHIFT", "S"),
        make_exec("hypryouctl screenshot region"),
        "Screenshot",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "SHIFT", "F"),
        make_exec("hypryouctl screenshot region freeze"),
        "Screenshot and freeze",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "CTRL", "S"),
        make_exec("hypryouctl screenshot window"),
        "Screenshot of window",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "CTRL", "F"),
        make_exec("hypryouctl screenshot window freeze"),
        "Screenshot of window and freeze",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "ALT", "S"),
        make_exec("hypryouctl screenshot active"),
        "Screenshot of active screen",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "ALT", "F"),
        make_exec("hypryouctl screenshot active freeze"),
        "Screenshot of active screen and freeze",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "SHIFT", "A"),
        make_exec("hypryouctl toggle_animations"),
        "Toggle all animations",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "SHIFT", "W"),
        make_exec("hypryouctl wallpaper random"),
        "Change wallpaper to random one",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "SHIFT", "R"),
        make_exec("hypryouctl reload"),
        "Restart HyprYou",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "L"),
        make_exec("hypryouctl lock"),
        "Lock screen",
        Category.ACTIONS
    )
)
