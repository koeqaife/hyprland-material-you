from repository import gtk
from src.modules.settings.base import SettingsTextRow
from src.modules.settings.base import SettingsBoolRow
from src.modules.settings.base import Category
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
            Category("Cliphist"),
            SettingsBoolRow(
                "Secure Cliphist (Clipboard History)",
                "Delete cliphist.db when session starts/ends",
                "secure_cliphist"
            ),

            Category("Default Apps"),
            SettingsTextRow(
                "Browser",
                "Default browser",
                "apps.browser"
            ),
            SettingsTextRow(
                "Editor",
                "Editor to use for opening files",
                "apps.editor"
            ),
            SettingsTextRow(
                "Files",
                "File manager to use for opening files",
                "apps.files"
            ),
            SettingsTextRow(
                "Terminal",
                "Terminal to open when pressing keybind",
                "apps.terminal"
            ),
            Hint(
                "It is recommended to restart the session"
            )
        )
        for child in self.box_children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
