from src.services.hyprland_keybinds.common import KeyBind, main_mod, Category

key_binds = (
    KeyBind(
        (main_mod, "SHIFT", "A"),
        ("exec", "hypryouctl toggle_animations"),
        "Toggle all animations",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "SHIFT", "S"),
        ("exec", "hypryouctl screenshot region"),
        "Screenshot",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "CTRL", "S"),
        ("exec", "hypryouctl screenshot window"),
        "Screenshot of window",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "ALT", "S"),
        ("exec", "hypryouctl screenshot active"),
        "Screenshot of active screen",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "SHIFT", "F"),
        ("exec", "hypryouctl screenshot region freeze"),
        "Screenshot",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "CTRL", "F"),
        ("exec", "hypryouctl screenshot window freeze"),
        "Screenshot of window",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "ALT", "F"),
        ("exec", "hypryouctl screenshot active freeze"),
        "Screenshot of active screen",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "SHIFT", "W"),
        ("exec", "hypryouctl wallpaper random"),
        "Change wallpaper to random one",
        Category.ACTIONS
    ),
    KeyBind(
        (main_mod, "L"),
        ("exec", "hypryouctl lock"),
        "Lock screen",
        Category.ACTIONS
    )
)
