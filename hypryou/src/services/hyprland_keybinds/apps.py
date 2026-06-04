from src.services.hyprland_keybinds.common import KeyBind, main_mod, Category

key_binds = (
    KeyBind(
        (main_mod, "RETURN"),
        ("exec", "hypryouctl apps terminal"),
        "Terminal",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "B"),
        ("exec", "hypryouctl apps browser"),
        "Browser",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "H"),
        ("exec", "pamac-manager"),
        "Pamac manager (if installed)",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "SHIFT", "M"),
        ("exec", "gnome-system-monitor"),
        "Gnome system monitor",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "E"),
        ("exec", "hypryouctl apps files"),
        "File Manager",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "SHIFT", "L"),
        ("exec", "sh -c \"TERM=$(hypryouctl apps terminal); $TERM -e sh -c 'fastfetch; read' & $TERM -e sh -c 'btop; read' & $TERM -e sh -c 'cava; read' & $TERM -e sh -c 'cmatrix; read'\""),
        "Launch system dashboard",
        Category.APPS
    )
)
