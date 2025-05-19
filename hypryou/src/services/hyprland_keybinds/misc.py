from src.services.hyprland_keybinds.common import (
    KeyBindHint, main_mod, Category
)

key_binds = (
    KeyBindHint(
        (main_mod, "P"),
        f"Passthrough {main_mod} key to VM",
        Category.MISC
    ),
    KeyBindHint(
        (main_mod, "Escape"),
        "Cancel passthrough",
        Category.MISC
    )
)
