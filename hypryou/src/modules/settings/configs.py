from repository import gtk
from src.modules.settings.base import SettingsBoolRow
from src.modules.settings.base import Category


class ConfigsPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsConfigsPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("configs-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.box_children = (
            Category("Hyprland"),
            SettingsBoolRow(
                "Apps environment",
                "Default apps environment vars (TERMINAL, BROWSER, etc.)",
                "apps.enabled"
            ),
            SettingsBoolRow(
                "Input settings",
                "If disabled, input settings wouldn't apply (advanced)",
                "input.enabled"
            ),
            SettingsBoolRow(
                "Input touchpad settings",
                "If disabled, input touchpad settings wouldn't apply",
                "input.touchpad.enabled"
            ),

            Category("Themes"),
            SettingsBoolRow(
                "GTK4",
                "Theme for GTK4",
                "themes.gtk4"
            ),
            SettingsBoolRow(
                "GTK3",
                "Theme for GTK3",
                "themes.gtk3"
            ),
            SettingsBoolRow(
                "Alacritty",
                "Theme for Alacritty",
                "themes.alacritty"
            ),
            SettingsBoolRow(
                "Kitty",
                "Theme for Kitty",
                "themes.kitty"
            ),
            SettingsBoolRow(
                "Wezterm",
                "Theme for Wezterm",
                "themes.wezterm"
            ),
        )
        for child in self.box_children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
