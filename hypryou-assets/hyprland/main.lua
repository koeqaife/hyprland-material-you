---@param path string
local function dofileOrCreate(path)
    local existing = io.open(path, "r")
    if existing then
        existing:close()
        local ok, err = pcall(function ()
            dofile(path)
        end)
        if not ok then
            print("hypryou: config error in " .. path .. ": " .. tostring(err))
        end
        return
    end

    local file = io.open(path, "w")
    if file then
        file:close()
        dofile(path)
    end
end

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

dofileOrCreate(os.getenv("HOME") .. "/.cache/hypryou/colors/colors-hyprland.lua")

dofile("/usr/share/hypryou/configs/hyprland/environment.lua")
dofile("/usr/share/hypryou/configs/hyprland/autostart.lua")
dofile("/usr/share/hypryou/configs/hyprland/layout.lua")
dofile("/usr/share/hypryou/configs/hyprland/misc.lua")
dofile("/usr/share/hypryou/configs/hyprland/windowrule.lua")
dofile("/usr/share/hypryou/configs/hyprland/animation.lua")
dofile("/usr/share/hypryou/configs/hyprland/keybindings.lua")

dofileOrCreate(os.getenv("HOME") .. "/.config/hypryou/hyprland.lua")
dofileOrCreate(os.getenv("HOME") .. "/.config/hypryou/hyprland_generated.lua")
