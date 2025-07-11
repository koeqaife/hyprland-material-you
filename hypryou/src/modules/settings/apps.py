from repository import gtk
from src.modules.settings.base import SettingsTextRow
from src.modules.settings.base import Hint


class AppsPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsAppsPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("apps-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.box_children = (
            SettingsTextRow(
                "Browser",
                "Default browser",
                "browser"
            ),
            SettingsTextRow(
                "Editor",
                "Editor to use for opening files",
                "editor"
            ),
            SettingsTextRow(
                "Files",
                "File manager to use for opening files",
                "files"
            ),
            SettingsTextRow(
                "Terminal",
                "Terminal to open when pressing keybind",
                "terminal"
            ),
            Hint(
                "It is recommended to restart the session"
            )
        )
        for child in self.box_children:
            self.box.append(child)

        self.timeout_id = -1
        self.once_scan = False

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
