from src.services.hyprland_keybinds.common import (
    KeyBind, main_mod, Category,
    make_exec, make_dispatch, make_hyprctl_dispatch
)

key_binds = (
    KeyBind(
        (main_mod, "%N%"),
        make_exec(
            "hypryouctl change_workspace %N% || " +
            make_hyprctl_dispatch("focus({ workspace = %N% })")
        ),
        "Switch workspace",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "SHIFT", "%N%"),
        make_exec(
            "hypryouctl move_window %N% || " +
            make_hyprctl_dispatch('move({ workspace = %N%, follow = true })')
        ),
        "Move window to workspace",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "CTRL", "%N%"),
        make_exec(
            "hypryouctl move_window_silent %N% || " +
            make_hyprctl_dispatch('move({ workspace = %N%, follow = false })')
        ),
        "Move window to workspace silently",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "CTRL", "down"),
        make_dispatch("focus({ workspace = \"empty\" })"),
        "Switch to empty workspace",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "Q"),
        make_dispatch("window.close({})"),
        "Close window",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "F"),
        make_dispatch("window.fullscreen({})"),
        "Open window in fullscreen mode",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "T"),
        make_dispatch("window.float({})"),
        "Toggle floating mode",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "J"),
        make_dispatch("layout(\"togglesplit\")"),
        "Toggle split mode",
        Category.WINDOWS
    ),
    KeyBind(
        (main_mod, "left"),
        make_dispatch("focus({ direction = \"l\" })")
    ),
    KeyBind(
        (main_mod, "right"),
        make_dispatch("focus({ direction = \"r\" })")
    ),
    KeyBind(
        (main_mod, "up"),
        make_dispatch("focus({ direction = \"u\" })")
    ),
    KeyBind(
        (main_mod, "down"),
        make_dispatch("focus({ direction = \"d\" })")
    ),
    KeyBind(
        (main_mod, "mouse:272"),
        make_dispatch("window.drag()")
    ),
    KeyBind(
        (main_mod, "mouse:273"),
        make_dispatch("window.resize()")
    ),
    KeyBind(
        (main_mod, "SHIFT", "right"),
        make_dispatch("window.resize({ x = 100, y = 0, relative = true })")
    ),
    KeyBind(
        (main_mod, "SHIFT", "left"),
        make_dispatch("window.resize({ x = -100, y = 0, relative = true })")
    ),
    KeyBind(
        (main_mod, "SHIFT", "up"),
        make_dispatch("window.resize({ x = 0, y = -100, relative = true })")
    ),
    KeyBind(
        (main_mod, "SHIFT", "down"),
        make_dispatch("window.resize({ x = 0, y = 100, relative = true })")
    ),
    KeyBind(
        (main_mod, "G"),
        make_dispatch("group.toggle()"),
        "Toggle group",
        Category.WINDOWS
    )
)
