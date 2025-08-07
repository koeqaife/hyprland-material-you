from repository import gtk
from src.modules.settings.base import int_kwargs
from src.modules.settings.base import SettingsTextRow
from src.modules.settings.base import SettingsBoolRow
from src.modules.settings.base import SettingsDropdownRow, DropdownItem
from src.modules.settings.base import Category
from src.modules.settings.base import Hint


class HyprlandPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsHyprlandPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("hyprland-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.box_children = (
            Category("General"),
            SettingsTextRow(
                "Gaps In",
                "Gaps between windows",
                "hyprland.gaps_in",
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Gaps Out",
                "Gaps between window and monitor edge",
                "hyprland.gaps_out",
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Window border size",
                "Size of the border around windows",
                "hyprland.border_size",
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsDropdownRow(
                "Layout",
                "Which layout to use",
                "hyprland.layout",
                items=[
                    DropdownItem("dwindle", "Dwindle"),
                    DropdownItem("master", "Master"),
                ]
            ),

            Category("Snap"),
            SettingsBoolRow(
                "Enabled",
                "Enable snapping for floating windows",
                "hyprland.snap.enabled",
            ),
            SettingsTextRow(
                "Window Gap",
                "Minimum gap between windows before snapping",
                "hyprland.snap.window_gap",
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Monitor Gap",
                "Minimum gap between window and monitor edges before snapping",
                "hyprland.snap.monitor_gap",
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsBoolRow(
                "Border overlap",
                "One-border gap when snapping windows",
                "hyprland.snap.border_overlap"
            ),
            SettingsBoolRow(
                "Respect gaps",
                "Snapping will respect gaps between windows (Gaps In)",
                "hyprland.snap.respect_gaps"
            ),

            Category("Misc"),
            SettingsDropdownRow(
                "VRR",
                "Adaptive Sync",
                "hyprland.misc.vrr",
                items=[
                    DropdownItem(0, "Off"),
                    DropdownItem(1, "On"),
                    DropdownItem(2, "Fullscreen only"),
                    DropdownItem(3, "Fullscreen Games/Video")
                ],
            ),
            SettingsBoolRow(
                "Middle click paste",
                "Paste from clipboard on middle click",
                "hyprland.misc.middle_click_paste"
            ),

            Category("Cursor"),
            SettingsTextRow(
                "Cursor name",
                "Name of cursor that will be used",
                "cursor.name"
            ),
            SettingsTextRow(
                "Cursor size",
                "Size of cursor in pixels",
                "cursor.size",
                max_width_chars=3,
                **int_kwargs
            ),
            Hint("Changing cursor settings requires session restart"),

            Category("Hyprsunset"),
            SettingsTextRow(
                "Night light temperature",
                "Screen temperature for night light (in K)",
                "hyprsunset.temperature",
                max_width_chars=5,
                **int_kwargs
            )
        )
        for child in self.box_children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.box_children:
            child.destroy()
