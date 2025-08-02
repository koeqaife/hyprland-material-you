from repository import gtk
from src.modules.settings.base import SettingsDropdownRow, DropdownItem
from src.modules.settings.base import SettingsTextRow
from src.modules.settings.base import Category
from src.modules.settings.base import Hint


class PowerPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsPowerPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("power-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.box_children = (
            Category("Laptop lid"),
            SettingsDropdownRow(
                "Laptop lid action",
                "What to do when lid closed",
                "lid_action",
                items=[
                    DropdownItem("", "Nothing"),
                    DropdownItem("dpms", "Screen off + Lock"),
                    DropdownItem("sleep", "Sleep"),
                    DropdownItem("lock", "Lock screen"),
                ]
            ),

            Category("Charging"),
            SettingsTextRow(
                "Lock",
                "Lock screen after inactivity (sec)",
                "idle.ac.lock",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            SettingsTextRow(
                "Turn off screen",
                "Turn off display after inactivity (sec)",
                "idle.ac.dpms",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            SettingsTextRow(
                "Sleep",
                "Sleep after inactivity (sec)",
                "idle.ac.sleep",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),

            Category("Battery"),
            SettingsTextRow(
                "Lock",
                "Lock screen on battery after inactivity (sec)",
                "idle.battery.lock",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            SettingsTextRow(
                "Turn off screen",
                "Turn off display on battery after inactivity (sec)",
                "idle.battery.dpms",
                test_text=lambda v: v.isdigit(),
                transform2_fn=lambda v: int(v),
                max_length=4
            ),
            SettingsTextRow(
                "Sleep",
                "Sleep on battery after inactivity (sec)",
                "idle.battery.sleep",
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

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
