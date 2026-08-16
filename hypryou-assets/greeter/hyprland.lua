hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
hl.env("XDG_SESSION_TYPE", "wayland")
hl.env("XDG_SESSION_DESKTOP", "Hyprland")
hl.env("GDK_SCALE", "1")
hl.env("XCURSOR_SIZE", "24")

hl.config({
    misc = {
        mouse_move_enables_dpms = true,
        key_press_enables_dpms = true,
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
        enable_anr_dialog = false,
        background_color = "0x000000",
    },

    ecosystem = {
        no_donation_nag = true,
        no_update_news = true,
    },
})

hl.monitor({
    output = "",
    mode = "preferred",
    position = "auto",
    scale = 1,
})

hl.on("hyprland.start", function ()
    hl.exec_cmd("hyprctl setcursor Bibata-Modern-Ice 24")

    hl.exec_cmd(
        "dbus-update-activation-environment --systemd "
        .. "WAYLAND_DISPLAY XDG_CURRENT_DESKTOP"
    )

    hl.exec_cmd(
        "bash -c 'python -O /usr/lib/hypryou/greeter_ui.py; "
        .. "hyprctl dispatch hl.dsp.exit()'"
    )
end)