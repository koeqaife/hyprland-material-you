from repository import gtk
from src.modules.settings.base import SettingsBoolRow
from src.modules.settings.base import SettingsDropdownRow, DropdownItem


class LockscreenPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsLockscreenPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("lockscreen-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.box_children = (
            SettingsBoolRow(
                "Media player",
                "Show playing media player",
                "lockscreen.media"
            ),
            SettingsBoolRow(
                "Always reveal input",
                "When enabled, you don't have to click on unlock button",
                "lockscreen.always_reveal_input"
            ),
            SettingsBoolRow(
                "Notification counter",
                "Counts how many new notifications you got",
                "lockscreen.notifications_counter"
            ),
            SettingsDropdownRow(
                "Notifications mode",
                "How notifications will be shown",
                "lockscreen.notifications",
                items=[
                    DropdownItem(0, "Show all"),
                    DropdownItem(1, "Hide sensitive content"),
                    DropdownItem(2, "Hide all content"),
                    DropdownItem(3, "Disable"),
                ]
            )
        )
        for child in self.box_children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
