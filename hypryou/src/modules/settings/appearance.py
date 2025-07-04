from utils import colors
from src.modules.settings.base import RowTemplate, SwitchRowTemplate
from src.modules.settings.base import SettingsBoolRow
from src.modules.settings.base import Category
import typing as t
from repository import gtk
import src.widget as widget
from utils import sync_debounce
from config import Settings


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


class OpacityRow(RowTemplate):
    __gtype_name__ = "SettingsOpacityRow"

    def __init__(self) -> None:
        self.settings = Settings()
        super().__init__(
            "UI Opacity",
            "Changes opacity of UI (minimum: 85%)",
            css_classes=("opacity-row",)
        )

        self.entry_box = gtk.Box(
            css_classes=("entry-box",)
        )
        self.entry = gtk.Entry(
            css_classes=("entry",),
            max_length=3,
            max_width_chars=3,
            halign=gtk.Align.END
        )
        self.percent = widget.Icon("percent")
        self.entry_box.append(self.entry)
        self.entry_box.append(self.percent)
        self.append(self.entry_box)

        self.debounced_text_changed = sync_debounce(500)(self.text_changed)
        self.entry_handler = (
            self.entry.connect("notify::text", self.debounced_text_changed)
        )
        self.settings_handler = self.settings.watch(
            "opacity", self.setting_updated
        )

    def setting_updated(self, new_value: float) -> None:
        value = str(round(new_value * 100))
        if self.entry.get_text() != value:
            self.entry.handler_block(self.entry_handler)
            self.entry.set_text(value)
            self.entry.handler_unblock(self.entry_handler)

    def destroy(self) -> None:
        super().destroy()
        self.entry.disconnect(self.entry_handler)

    def text_changed(self, *args: t.Any) -> None:
        text = self.entry.get_text()
        if not text.isdigit():
            value = str(round(self.settings.get("opacity") * 100))
            self.entry.set_text(value)
            return

        value = min(max(float(text) / 100, 0.85), 1.0)
        self.settings.set("opacity", value)


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

            Category("Effects"),
            SettingsBoolRow(
                "Blur",
                "Adds blur to windows and to UI",
                "blur"
            ),
            SettingsBoolRow(
                "Blur XRay",
                "Adds xray effect to blur",
                "blur_xray"
            ),
            OpacityRow(),

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
        )
        for child in self.children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
