from src.services.hyprland_keybinds.common import (
    KeyBind, main_mod, Category,
    make_exec
)

key_binds = (
    KeyBind(
        (main_mod, "RETURN"),
        make_exec("hypryouctl apps terminal"),
        "Terminal",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "B"),
        make_exec("hypryouctl apps browser"),
        "Browser",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "H"),
        make_exec("pamac-manager"),
        "Pamac manager (if installed)",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "SHIFT", "M"),
        make_exec("gnome-system-monitor"),
        "Gnome system monitor",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "E"),
        make_exec("hypryouctl apps files"),
        "File Manager",
        Category.APPS
    ),
    KeyBind(
        (main_mod, "SHIFT", "L"),
        make_exec("sh -c \"TERM=$(hypryouctl apps terminal); $TERM -e sh -c 'btop; read' & sleep 0.1; $TERM -e sh -c 'fastfetch; read' & sleep 0.1; $TERM -e sh -c 'htop; read' & sleep 0.1; $TERM -e sh -c 'cava; read' & sleep 0.1; $TERM -e sh -c 'cmatrix; read'\""),
        "Launch system dashboard",
        Category.APPS
    )
)
