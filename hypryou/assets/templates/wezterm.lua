-- <settings:themes.wezterm>
local wezterm = require 'wezterm'
local config = {}

function get_appearance()
  if wezterm.gui then
    return wezterm.gui.get_appearance()
  end
  return 'Dark'
end

function scheme_for_appearance(appearance)
  if appearance:find 'Dark' then
    return 'Catppuccin Macchiato (Gogh)'
  else
    return 'Catppuccin Latte (Gogh)'
  end
end

config.color_scheme = scheme_for_appearance(get_appearance())
config.colors = {
    foreground = "<onBackground>",
    background = "<background>",
    selection_bg = "<secondaryContainer>",
    selection_fg = "<onSecondaryContainer>",
    cursor_bg = "<primary>",
    cursor_fg = "<onPrimary>",
    cursor_border = "<outline>",
    scrollbar_thumb = "<secondaryContainer>",
    split = "<outline>"
}

return config
