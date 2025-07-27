from utils import colors
from src.modules.settings.base import SwitchRowTemplate
from src.modules.settings.base import SettingsBoolRow, SettingsTextRow
from src.modules.settings.base import Category
from src.modules.settings.base import int_kwargs, float_kwargs
import typing as t
from repository import gtk


class ToggleDarkMode(SwitchRowTemplate):
    __gtype_name__ = "ToggleDarkMode"

    def __init__(self) -> None:
        super().__init__(
            "Dark Mode",
            "Toggles dark theme",
            css_classes=("dark-mode-toggle",)
        )
        self.dark_mode_handler = colors.dark_mode.watch(
            self.switch_set_active
        )
        self.switch_set_active(colors.dark_mode.value)

    def on_switch_changed(self, *args: t.Any) -> None:
        colors.set_dark_mode(self.switch.get_active())

    def destroy(self) -> None:
        colors.dark_mode.unwatch(self.dark_mode_handler)
        super().destroy()


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
            ToggleDarkMode(),
            SettingsTextRow(
                "Color",
                "Use different color for UI instead of wallpapers' one",
                "color",
                "tag",
                max_length=6
            ),

            Category("Effects"),
            SettingsBoolRow(
                "Blur",
                "Adds blur to windows and to UI",
                "blur.enabled"
            ),
            SettingsBoolRow(
                "Blur XRay",
                "Adds xray effect to blur",
                "blur.xray"
            ),
            SettingsTextRow(
                "UI Opacity",
                "Changes opacity of UI (minimum: 85%)",
                "opacity",
                right_icon="percent",
                max_length=3,
                transform_fn=lambda v: str(round(float(v) * 100)),
                transform2_fn=lambda v: min(max(float(v) / 100, 0.85), 1.0),
                test_text=lambda v: v.isdigit()
            ),
            SettingsTextRow(
                "Rounding",
                "Rounded corners' radius (in layout px)",
                "hyprland.decoration.rounding",
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Rounding Power",
                "Adjusts the curve used for rounding corners",
                "hyprland.decoration.rounding_power",
                max_width_chars=3,
                **float_kwargs
            ),

            Category("Layout"),
            SettingsBoolRow(
                "Screen corners",
                "Adds round corners to the top of the screen under the bar",
                "corners"
            ),
            SettingsBoolRow(
                "Floating Sidebar",
                "Adds margins to the sidebar",
                "floating_sidebar",
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
        )
        for child in self.children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
