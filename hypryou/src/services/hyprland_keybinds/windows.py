from src.services.hyprland_keybinds.common import KeyBind, main_mod, Category

key_binds = (
    KeyBind(
        (main_mod, "Q"),
        "killactive",
        "Close window",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "F"),
        "fullscreen",
        "Open window in fullscreen mode",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "T"),
        "togglefloating",
        "Toggle floating mode",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "J"),
        "togglesplit",
        "Toggle split mode",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "left"),
        ("movefocus", "l")
    ),
    KeyBind(
        (main_mod, "right"),
        ("movefocus", "r")
    ),
    KeyBind(
        (main_mod, "up"),
        ("movefocus", "u")
    ),
    KeyBind(
        (main_mod, "down"),
        ("movefocus", "d")
    ),
    KeyBind(
        (main_mod, "mouse:272"),
        "movewindow"
    ),
    KeyBind(
        (main_mod, "mouse:273"),
        "resizewindow"
    ),
    KeyBind(
        (main_mod, "SHIFT", "right"),
        ("resizeactive", "100 0")
    ),
    KeyBind(
        (main_mod, "SHIFT", "left"),
        ("resizeactive", "-100 0")
    ),
    KeyBind(
        (main_mod, "SHIFT", "up"),
        ("resizeactive", "0 -100")
    ),
    KeyBind(
        (main_mod, "SHIFT", "down"),
        ("resizeactive", "0 100")
    ),
    KeyBind(
        (main_mod, "G"),
        "togglegroup",
        "Toggle group",
        Category.WINDOWS
    )
)
