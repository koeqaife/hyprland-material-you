local mainMod = "SUPER"

hl.bind(
    mainMod .. " + mouse_down",
    hl.dsp.focus({ workspace = "e+1" })
)

hl.bind(
    mainMod .. " + mouse_up",
    hl.dsp.focus({ workspace = "e+1" })
)

hl.bind(
    "XF86MonBrightnessUp",
    hl.dsp.exec_cmd("brightnessctl -q s +10%")
)

hl.bind(
    "XF86MonBrightnessDown",
    hl.dsp.exec_cmd("brightnessctl -q s 10%-")
)

hl.bind(
    "XF86AudioRaiseVolume",
    hl.dsp.exec_cmd("pactl set-sink-volume @DEFAULT_SINK@ +5%")
)

hl.bind(
    "XF86AudioLowerVolume",
    hl.dsp.exec_cmd("pactl set-sink-volume @DEFAULT_SINK@ -5%")
)

hl.bind(
    "XF86AudioMute",
    hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle")
)

hl.bind(
    "XF86AudioMicMute",
    hl.dsp.exec_cmd("pactl set-source-mute @DEFAULT_SOURCE@ toggle")
)

hl.bind(
    mainMod .. " + K",
    hl.dsp.exec_cmd([[bash -c 'term="${XDG_UTILS_TERMINAL:-}"; \
if [ -n "$term" ] && command -v "$term" >/dev/null 2>&1; then exec "$term"; \
else for t in kitty alacritty foot wezterm xterm; do \
command -v "$t" >/dev/null 2>&1 && exec "$t"; done; \
fi']])
)