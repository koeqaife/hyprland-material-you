from repository import gtk
from config import info

from src.modules.settings.base import SettingsBoolRow
from src.modules.settings.base import Row
from src.modules.settings.base import Category


def open_link(url: str) -> None:
    import webbrowser
    webbrowser.open(url)


class WikiButton(gtk.Button):
    def __init__(self, url: str) -> None:
        super().__init__(
            css_classes=("outlined", "wiki-button"),
            label="Wiki",
            valign=gtk.Align.CENTER
        )
        self.connect("clicked", lambda *_: open_link(url))


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
        self.children_with_wiki = (
            (
                SettingsBoolRow(
                    "Telegram",
                    "Generate theme for Telegram",
                    "themes.telegram"
                ),
                f"{info["github"]}/wiki/More-themes#telegram-theme"
            ),
            (
                Row(
                    "Discord",
                    "Theme for Discord",
                ),
                f"{info["github"]}/wiki/More-themes#discord-theme"
            ),
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
            self.children_with_wiki[1][0],
            self.children_with_wiki[0][0]
        )

        for child, url in self.children_with_wiki:
            child.insert_child_after(WikiButton(url), child.info_box)

        for _child in self.box_children:
            self.box.append(_child)

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
