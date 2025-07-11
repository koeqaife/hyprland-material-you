from repository import gtk
from src.modules.settings.base import SettingsTextRow
from src.modules.settings.base import Category
from src.modules.settings.base import Hint


class SleepPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsSleepPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("sleep-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.box_children = (
            Category("Charging"),
            SettingsTextRow(
                "Lock",
                "Lock screen after inactivity (sec)",
                "ac_lock",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            SettingsTextRow(
                "Turn off screen",
                "Turn off display after inactivity (sec)",
                "ac_dpms",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            SettingsTextRow(
                "Sleep",
                "Sleep after inactivity (sec)",
                "ac_sleep",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),

            Category("Battery"),
            SettingsTextRow(
                "Lock",
                "Lock screen on battery after inactivity (sec)",
                "battery_lock",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            SettingsTextRow(
                "Turn off screen",
                "Turn off display on battery after inactivity (sec)",
                "battery_dpms",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            SettingsTextRow(
                "Sleep",
                "Sleep on battery after inactivity (sec)",
                "battery_sleep",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            Hint(
                "Timers are cumulative.\n" +
                "Example: Sleep = Lock + Screen off + Sleep"
            )
        )
        for child in self.box_children:
            self.box.append(child)

        self.timeout_id = -1
        self.once_scan = False

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
