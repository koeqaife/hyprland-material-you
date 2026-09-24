from repository import gtk, gio
from config import HOME, Settings
from src.modules.settings.base import int_kwargs
from src.modules.settings.base import Row
from src.modules.settings.base import SettingsTextRow
from src.modules.settings.base import SettingsBoolRow
from src.modules.settings.base import SettingsDropdownRow, DropdownItem
from src.modules.settings.base import Category
from src.modules.settings.base import Hint
from src.modules.settings.base import EditableList, EditableListRow
from utils.debounce import sync_debounce
from utils.ref import unpack_reactive
import src.services.hyprland as hyprland
import typing as t
import weakref


class WorkspaceRuleRow(EditableListRow):
    __gtype_name__ = "SettingsWorkspaceRuleRow"

    def __init__(
        self,
        value: dict[str, str],
        monitors: list[str],
        on_remove: t.Callable[[t.Self], None],
        on_changed: t.Callable[[], None]
    ) -> None:
        super().__init__(on_remove, ("workspace-rule-row",))
        self._on_changed = weakref.WeakMethod(on_changed)
        self.monitors = monitors

        self.monitor = gtk.DropDown.new_from_strings(monitors or [""])
        self.monitor.set_valign(gtk.Align.CENTER)
        monitor_name = value.get("monitor") or ""
        if monitor_name in monitors:
            self.monitor.set_selected(monitors.index(monitor_name))

        self.entry_box = gtk.Box(css_classes=("entry-box",))
        self.entry = gtk.Entry(
            css_classes=("entry",),
            halign=gtk.Align.END,
            max_width_chars=10,
            placeholder_text="1-10"
        )
        self.entry.set_text(value.get("workspaces") or "")
        self.entry_box.append(self.entry)

        self.add_field(self.monitor)
        self.add_field(self.entry_box)

        self.debounced_changed = sync_debounce(500)(self.on_changed)
        self.monitor_handler = self.monitor.connect(
            "notify::selected", self.on_changed
        )
        self.entry_handler = self.entry.connect(
            "notify::text", self.debounced_changed
        )

    def on_changed(self, *args: t.Any) -> None:
        method = self._on_changed()
        if callable(method):
            method()  # type: ignore

    def set_problem(self, problem: str | None) -> None:
        if problem:
            self.entry_box.add_css_class("incorrect")
        else:
            self.entry_box.remove_css_class("incorrect")
        self.entry_box.set_tooltip_text(problem)

    def get_value(self) -> dict[str, str]:
        item = self.monitor.get_selected_item()
        monitor = item.get_string() if item is not None else ""
        return {
            "monitor": monitor,
            "workspaces": self.entry.get_text()
        }

    def destroy(self) -> None:
        self.monitor.disconnect(self.monitor_handler)
        self.entry.disconnect(self.entry_handler)
        super().destroy()


class WorkspaceRulesList(EditableList):
    __gtype_name__ = "SettingsWorkspaceRulesList"

    def __init__(self) -> None:
        super().__init__(
            "Workspace rules",
            "Workspaces a monitor keeps, like 1-10 or 1,3,9",
            "workspace_rules",
            "Add rule"
        )

    def monitor_names(self) -> list[str]:
        names = list(hyprland.monitor_ids.value.keys())
        rules = unpack_reactive(Settings().get("workspace_rules"))
        if isinstance(rules, list):
            # A monitor that is unplugged right now still has to show up,
            # otherwise opening the settings would drop its rule.
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                name = rule.get("monitor")
                if name and name not in names:
                    names.append(name)
        return names

    def create_row(self, value: dict[str, str]) -> EditableListRow:
        return WorkspaceRuleRow(
            value, self.monitor_names(), self.on_remove, self.save
        )

    def empty_value(self) -> dict[str, str]:
        names = self.monitor_names()
        return {"monitor": names[0] if names else "", "workspaces": ""}

    def validate(self) -> None:
        # Mirrors generate_workspace_rules(): the rule written first keeps a
        # workspace, so a later one asking for it would be dropped silently.
        owners: dict[int, str] = {}
        for row in self.rows:
            if not isinstance(row, WorkspaceRuleRow):
                continue
            value = row.get_value()
            text = value["workspaces"].strip()
            workspaces = hyprland.parse_workspaces(text)
            if text and not workspaces:
                row.set_problem("Use numbers like 1-10 or 1,3,9")
                continue
            taken = sorted(
                {owners[w] for w in workspaces
                 if w in owners and owners[w] != value["monitor"]}
            )
            for workspace in workspaces:
                owners.setdefault(workspace, value["monitor"])
            if taken:
                row.set_problem(
                    "Already kept by " + ", ".join(taken)
                    + " in a rule above, so this one is ignored"
                )
            else:
                row.set_problem(None)


class HyprlandPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsHyprlandPage"

    def open_hyprland_config(*args: t.Any) -> None:
        gio.AppInfo.launch_default_for_uri(
            f"file://{HOME}/.config/hypryou/hyprland.conf", None
        )

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
            Category("Custom"),
            Row(
                "Hyprland config",
                "Config file is located at ~/.config/hypryou/hyprland.conf",
                self.open_hyprland_config
            ),
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

            Category("Workspaces"),
            WorkspaceRulesList(),
            Hint(
                "A workspace bound to a monitor always opens there, "
                "and the first one becomes that monitor's default"
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
            SettingsBoolRow(
                "Keep Night Light On",
                "Restore night light between sessions",
                "hyprsunset.remember"
            ),
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
