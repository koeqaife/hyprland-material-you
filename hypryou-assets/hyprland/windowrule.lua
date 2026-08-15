-- ######## Window rules ########

hl.window_rule({
    match = { class = "^(Microsoft-edge)$" },
    tile = true,
})

hl.window_rule({
    match = { class = "^(Brave-browser)$" },
    tile = true,
})

hl.window_rule({
    match = { class = "^(Chromium)$" },
    tile = true,
})

hl.window_rule({
    match = { class = "^(blueman-manager)$" },
    float = true,
})

hl.window_rule({
    match = { class = "^(blueberry.py)$" },
    float = true,
})

hl.window_rule({
    match = { class = "^(nm-connection-editor)$" },
    float = true,
})

hl.window_rule({
    match = { class = "^(qalculate-gtk)$" },
    float = true,
})

hl.window_rule({
    match = { class = "^(steam)$" },
    float = true,
})

hl.window_rule({
    match = { class = "^(com.koeqaife.hypryou)$" },
    float = true,
})

hl.window_rule({
    match = { title = "^(Volume Control)(.*)$" },
    float = true,
})

-- Xwaylandvideobridge (if installed)

hl.window_rule({
    match = { class = "^(xwaylandvideobridge)$" },
    opacity = "0 override",
})

hl.window_rule({
    match = { class = "^(xwaylandvideobridge)$" },
    no_anim = true,
})

hl.window_rule({
    match = { class = "^(xwaylandvideobridge)$" },
    no_initial_focus = true,
})

hl.window_rule({
    match = { class = "^(xwaylandvideobridge)$" },
    max_size = "1 1",
})

hl.window_rule({
    match = { class = "^(xwaylandvideobridge)$" },
    no_blur = true,
})

-- Dialogs

hl.window_rule({
    match = { title = "^(Open File)(.*)$" },
    float = true,
})

hl.window_rule({
    match = { title = "^(Select a File)(.*)$" },
    float = true,
})

hl.window_rule({
    match = { title = "^(Choose wallpaper)(.*)$" },
    float = true,
})

hl.window_rule({
    match = { title = "^(Open Folder)(.*)$" },
    float = true,
})

hl.window_rule({
    match = { title = "^(Save As)(.*)$" },
    float = true,
})

hl.window_rule({
    match = { title = "^(Library)(.*)$" },
    float = true,
})

hl.window_rule({
    match = { title = "^(File Upload)(.*)$" },
    float = true,
})

-- Tearing

hl.window_rule({
    match = { class = ".*\\.exe" },
    immediate = true,
})

hl.window_rule({
    match = { class = "(steam_app)455" },
    immediate = true,
})

-- ######## Layer rules ########

hl.layer_rule({
    match = { namespace = "selection" },
    no_anim = true,
})

hl.layer_rule({
    match = { namespace = "popup.*" },
    no_anim = true,
    xray = true,
    blur = true,
    ignore_alpha = 0.85
})

hl.layer_rule({
    match = { namespace = "hyprpicker" },
    no_anim = true,
})

hl.layer_rule({
    match = { namespace = "noanim" },
    no_anim = true,
})

hl.layer_rule({
    match = { namespace = "wallpapers" },
    no_anim = true,
})