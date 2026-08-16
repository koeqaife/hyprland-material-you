from src.services.hyprland_keybinds.common import KeyBind, make_exec

key_binds = (
    KeyBind(
        ("XF86AudioPlay"),
        make_exec("hypryouctl player play-pause")
    ),
    KeyBind(
        ("XF86AudioPause"),
        make_exec("hypryouctl player pause")
    ),
    KeyBind(
        ("XF86AudioNext"),
        make_exec("hypryouctl player next")
    ),
    KeyBind(
        ("XF86AudioPrev"),
        make_exec("hypryouctl player previous")
    ),
    KeyBind(
        ("XF86Lock"),
        make_exec("hypryouctl lock")
    ),
    KeyBind(
        ("XF86Tools"),
        make_exec("hypryouctl settings")
    ),
    KeyBind(
        ("XF86Calculator"),
        make_exec("hypryouctl qalculate-gtk")
    )
)
