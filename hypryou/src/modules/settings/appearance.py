from src.modules.settings.base import SettingsBoolRow, SettingsTextRow
from src.modules.settings.base import SettingsDropdownRow, DropdownItem
from src.modules.settings.base import Category
from repository import gtk
from utils.colors.schemes import schemes


class AppearancePage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsAppearancePage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("appearance-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.children = (
            Category("Colors"),
            SettingsBoolRow(
                "Dark Mode",
                "Toggles dark theme",
                "appearance.dark_mode"
            ),
            SettingsTextRow(
                "Color",
                "Use different color for UI instead of wallpapers' one",
                "appearance.color",
                "tag",
                max_length=6
            ),
            SettingsDropdownRow(
                "Color scheme",
                "Choose your preferred scheme",
                "appearance.scheme",
                items=[
                    DropdownItem(
                        scheme_name,
                        scheme_name.capitalize().replace("_", " ")
                    )
                    for scheme_name in schemes
                ]
            ),

            Category("Layout"),
            SettingsBoolRow(
                "Screen corners",
                "Adds round corners to the top of the screen under the bar",
                "corners",
                conflicts_with={"floating_bar"}
            ),
            SettingsBoolRow(
                "Floating Sidebar",
                "Adds margins to the sidebar",
                "floating_sidebar",
            ),
            SettingsBoolRow(
                "Floating Bar",
                "Adds margins to the bar (conflicts with corners)",
                "floating_bar",
            ),

            Category("Formatting"),
            SettingsBoolRow(
                "Use 24-hour format",
                "Changes the time format from 13:00 to 1 PM and vice versa",
                "is_24hr_clock",
            ),

            Category("Behavior"),
            SettingsBoolRow(
                "Per-monitor workspaces",
                "Workspaces are split per monitor (e.g. 1-10, 11-20)",
                "separated_workspaces"
            ),
            SettingsBoolRow(
                "Cancel button in power menu",
                "Shows a cancel button in the power menu",
                "power_menu_cancel_button"
            ),
            SettingsBoolRow(
                "Always show battery",
                "Shows battery on bar even when fully charged",
                "always_show_battery"
            ),
            SettingsBoolRow(
                "Auto-close other popups",
                "Opening a popup closes the previous one",
                "one_popup_at_time"
            ),
            SettingsBoolRow(
                "Hide empty workspaces",
                "Don't show workspaces without windows",
                "hide_empty_workspaces"
            ),
            SettingsBoolRow(
                "Old Fullscreen Behavior",
                "If enabled, fullscreen behavior from <2.1.0 will be used",
                "old_fullscreen_behavior"
            ),
            SettingsDropdownRow(
                "Bar media player",
                "How media player on the bar will look like",
                "bar_media_style",
                items=[
                    DropdownItem(
                        0, "Default",
                        "Visible name and cover, not collapsed"
                    ),
                    DropdownItem(
                        1, "Private",
                        "Hidden name and cover, not collapsed"
                    ),
                    DropdownItem(
                        2, "Collapsed",
                        "Just icon on the bar, very small"
                    )
                ]
            ),

            Category("Icons"),
            SettingsTextRow(
                "Light Icons",
                "Gtk icons that will be used on light theme",
                "icons.light"
            ),
            SettingsTextRow(
                "Dark Icons",
                "Gtk icons that will be used on dark theme",
                "icons.dark"
            )
        )
        for child in self.children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
