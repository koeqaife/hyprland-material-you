from src.services.hyprland_keybinds.common import KeyBind

key_binds = (
    KeyBind(
        ("", "XF86AudioPlay"),
        ("exec", "hypryouctl player play-pause")
    ),
    KeyBind(
        ("", "XF86AudioPause"),
        ("exec", "hypryouctl player pause")
    ),
    KeyBind(
        ("", "XF86AudioNext"),
        ("exec", "hypryouctl player next")
    ),
    KeyBind(
        ("", "XF86AudioPrev"),
        ("exec", "hypryouctl player previous")
    ),
    KeyBind(
        ("", "XF86Lock"),
        ("exec", "hypryouctl lock")
    ),
    KeyBind(
        ("", "XF86Tools"),
        ("exec", "hypryouctl settings")
    ),
    KeyBind(
        ("", "XF86Calculator"),
        ("exec", "hypryouctl qalculate-gtk")
    )
)
