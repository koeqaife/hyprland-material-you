import types
from utils.ref import Ref
from utils.styles import toggle_css_class
from repository import gtk, glib
from config import Settings
import typing as t
from src.services.hyprland import MonitorDict
import src.services.hyprland as hyprland
import asyncio
import src.widget as widget
import weakref
from src.variables import Globals

from src.modules.settings.base import RowTemplate
from src.modules.settings.base import DropdownRow, DropdownItem
from src.modules.settings.base import TextRow
from src.modules.settings.base import SwitchRow

# I finally made it! I hate it so much
# Input settings were much more boring that this tho
# it turned out to spaghetti code tho, but who cares?
# Me in the future: O_O; WHAT THE HELLY I'VE DONE??!?!?!?


def check_position(value: str) -> bool:
    try:
        x, y = value.split("x")
        _ = int(x), int(y)
        return True
    except ValueError:
        return False


class YesNoDialog(gtk.ApplicationWindow):
    __gtype_name__ = "SettingsMonitorsYesNo"

    def __init__(
        self,
        callback: t.Callable[[bool], None]
    ) -> None:
        self.callback_ref = weakref.WeakMethod(callback)
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            application=Globals.app,
            name="monitors-dialog",
            css_classes=("settings-monitors-dialog", "misc--dialog"),
            title="Monitor Settings Confirmation",
            child=self.box
        )
        self.title = gtk.Label(
            css_classes=("title",),
            xalign=0
        )
        self.description = gtk.Label(
            css_classes=("description",),
            use_markup=True,
            xalign=0
        )

        self.title.set_text("Save Settings?")
        self._description = (
            "Settings will be automatically canceled in <b>{}</b>"
        )
        self.left = 10
        self.description.set_markup(self._description.format("10"))

        self.box.append(self.title)
        self.box.append(self.description)

        self.actions_box = gtk.Box(
            css_classes=("actions-box",),
            hexpand=True,
            halign=gtk.Align.END
        )
        self.no_button = gtk.Button(
            css_classes=("no", "text"),
            label="No"
        )
        self.yes_button = gtk.Button(
            css_classes=("yes", "filled"),
            label="Yes"
        )
        self.actions_box.append(self.no_button)
        self.actions_box.append(self.yes_button)

        self.button_handlers = {
            self.no_button: self.no_button.connect(
                "clicked", self.on_cancel
            ),
            self.yes_button: self.yes_button.connect(
                "clicked", self.on_yes
            )
        }
        self.box.append(self.actions_box)

        self.close_handler = self.connect(
            "close-request", self.on_close_request
        )

        self.source = glib.timeout_add(1000, self.on_timeout)

    def on_timeout(self) -> bool:
        self.left -= 1
        if self.left <= 0:
            self.on_cancel()
            self.source = -1
            return False
        self.description.set_markup(self._description.format(str(self.left)))
        return True

    def on_close_request(self, *args: t.Any) -> None:
        self.on_cancel()

    def on_cancel(self, *args: t.Any) -> None:
        self.return_value(False)

    def on_yes(self, *args: t.Any) -> None:
        self.return_value(True)

    def destroy(self) -> None:
        if hasattr(self, "button_handlers"):
            for button, handler in self.button_handlers.items():
                button.disconnect(handler)
        if self.source > 0:
            glib.source_remove(self.source)
        self.disconnect(self.close_handler)
        super().destroy()

    def return_value(self, value: bool) -> None:
        method = self.callback_ref()
        if method is not None:
            method(value)


class MonitorsPage(gtk.Box):
    __gtype_name__ = "SettingsMonitorsPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        self.scrollable = gtk.ScrolledWindow(
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER,
            vexpand=True
        )
        super().__init__(
            css_classes=("monitors-page", "settings-page",),
            orientation=gtk.Orientation.VERTICAL
        )

        self._finished = False
        self._ref = t.cast(
            Ref[list[dict[str, str]]],
            Settings().get_ref("monitors")
        )
        self._dialog: YesNoDialog | None = None
        self.original_settings: dict[str, dict[str, str]] = {}
        self.settings: dict[str, dict[str, str]] = {}

        self.current_monitor = ""
        self.monitors: dict[str, MonitorDict] = {}

        self.monitor_items: dict[str, DropdownItem] = {}
        self.monitor_selector = DropdownRow(
            "Monitor",
            "Select monitor to configure",
            items=[], on_selected=self.on_select_monitor
        )
        self.refresh_button = gtk.Button(
            child=widget.Icon("refresh"),
            css_classes=("icon-tonal", "refresh-button"),
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )
        self.monitor_selector.append(self.refresh_button)

        self.monitor_enabled = SwitchRow(
            "Enabled",
            "Enabled or disable monitor",
            on_changed=self.on_monitor_enabled
        )

        self.modes_items: list[DropdownItem] = []
        self._cached_custom = DropdownItem("custom", "Custom")
        self.mode_selector = DropdownRow(
            "Select mode",
            "Screen resolution and hertz",
            items=[self._cached_custom],
            on_selected=self.on_select_mode
        )

        self.custom_mode = TextRow(
            "Custom mode",
            "Set custom monitor mode",
            on_text_changed=self.make_text_handler("mode")
        )

        self.position = TextRow(
            "Position",
            "Position of the monitor in pixels",
            on_text_changed=self.on_position,
            max_width_chars=10
        )

        self.scale = TextRow(
            "Scale",
            "Monitor scale",
            on_text_changed=self.on_scale,
            max_length=4,
            max_width_chars=3,
            right_icon="percent"
        )

        self.color_management = DropdownRow(
            "Color management preset",
            "How colors will look like on your monitor",
            items=[
                DropdownItem(
                    "auto", "Auto",
                    "sRGB for 8bpc, wide for 10bpc if supported (recommended)"
                ),
                DropdownItem(
                    "srgb", "sRGB",
                    "sRGB primaries (default)"
                ),
                DropdownItem(
                    "wide", "Wide",
                    "wide color gamut, BT2020 primaries"
                ),
                DropdownItem(
                    "edid", "Edid",
                    "Primaries from edid (known to be inaccurate)"
                ),
                DropdownItem(
                    "hdr", "HDR",
                    "Wide color gamut and HDR PQ transfer function"
                ),
                DropdownItem(
                    "hdredid", "HDR-Edid",
                    "Same as hdr with edid primaries"
                )
            ],
            on_selected=self.make_dropdown_handler("cm")
        )

        self.transform = DropdownRow(
            "Transform",
            "Rotate or flip your screen however you need",
            items=[
                DropdownItem("0", "None"),
                DropdownItem("1", "90°"),
                DropdownItem("2", "180°"),
                DropdownItem("3", "270°"),
                DropdownItem("4", "Flipped"),
                DropdownItem("5", "Flipped + 90°"),
                DropdownItem("6", "Flipped + 180°"),
                DropdownItem("7", "Flipped + 270°")
            ],
            on_selected=self.make_dropdown_handler("transform")
        )

        self.vrr = DropdownRow(
            "VRR",
            "Adaptive Sync",
            items=[
                DropdownItem("", "Default"),
                DropdownItem("0", "Off"),
                DropdownItem("1", "On"),
                DropdownItem("2", "Fullscreen only"),
                DropdownItem("3", "Fullscreen Games/Video")
            ],
            on_selected=self.make_dropdown_handler("vrr")
        )

        self.mirror = TextRow(
            "Mirror",
            "Copy screen from another monitor",
            on_text_changed=self.make_text_handler("mirror")
        )

        self.bitdepth = TextRow(
            "Bitdepth",
            "Number of bits used per color channel (e.g. 8, 10)",
            on_text_changed=self.on_bitdepth,
            max_length=4,
            max_width_chars=3
        )

        self.children = (
            self.monitor_selector,
            gtk.Separator(),
            self.monitor_enabled,
            self.mode_selector,
            self.custom_mode,
            self.position,
            self.scale,
            self.color_management,
            self.transform,
            self.mirror,
            self.vrr,
            self.bitdepth
        )

        self.actions_box = gtk.Box(
            css_classes=("actions-box",),
            halign=gtk.Align.END
        )
        self.save_button = gtk.Button(
            css_classes=("filled",),
            label="Save",
            sensitive=False
        )
        self.cancel_button = gtk.Button(
            css_classes=("text",),
            label="Cancel"
        )
        self.actions_box.append(self.cancel_button)
        self.actions_box.append(self.save_button)

        self.button_handlers = {
            self.cancel_button: self.cancel_button.connect(
                "clicked", self.cancel
            ),
            self.save_button: self.save_button.connect(
                "clicked", self.save
            ),
            self.refresh_button: self.refresh_button.connect(
                "clicked", self.sync
            )
        }

        for child in self.children:
            self.box.append(child)

        self.append(self.scrollable)
        self.append(self.actions_box)

        self.sync()

    def sync(self, *args: t.Any) -> None:
        asyncio.create_task(self.sync_async())

    async def sync_async(self) -> None:
        monitors = await hyprland.get_monitors()
        for monitor in monitors:
            if monitor["name"] not in self.monitor_items.keys():
                self.monitor_items[monitor["name"]] = DropdownItem(
                    monitor["name"], monitor["name"],
                    monitor["description"]
                )
                self.monitor_selector.set_items(
                    list(self.monitor_items.values())
                )
        self.monitors = {
            monitor["name"]: monitor
            for monitor in monitors
        }
        self.settings = {
            monitor_setting["output"]: monitor_setting
            for monitor_setting in self._ref.unpack()
            if monitor_setting.get("output")
        }
        self.original_settings = {
            key: dict(value)
            for key, value in self.settings.items()
        }
        self.save_button.set_sensitive(False)

        cur_monitor = self.monitors.get(self.current_monitor)
        if cur_monitor is None:
            return
        self.update_all(cur_monitor)

    def cancel(self, *args: t.Any) -> None:
        self.settings = {
            key: dict(value)
            for key, value in self.original_settings.items()
        }
        self.save_button.set_sensitive(False)
        monitor = self.monitors.get(self.current_monitor)
        if monitor is None:
            return

        self.update_all(monitor)

    def save(self, *args: t.Any) -> None:
        if not self._dialog:
            self._ref.value = list(self.settings.values())
            self._dialog = YesNoDialog(self.on_dialog)
            self._dialog.present()
            self.set_sensitive(False)

    def sync_finished(self) -> None:
        self._finished = True

    def update_setting(self, key: str, value: t.Any) -> None:
        if not self._finished:
            return
        if self.current_monitor in self.settings:
            current = self.settings[self.current_monitor]
        else:
            current = {
                "output": self.current_monitor
            }
            self.settings[self.current_monitor] = current
        current[key] = value
        self.save_button.set_sensitive(True)

    def get_setting(
        self,
        key: str,
        monitor: MonitorDict | None = None
    ) -> str | None:
        if monitor is None:
            name = self.current_monitor
        else:
            name = monitor["name"]
        value = self.settings.get(name, {}).get(key)
        return value

    # on_... events

    def on_dialog(self, save: bool) -> None:
        if self._dialog is None:
            return
        self._dialog.destroy()
        self._dialog = None
        self.set_sensitive(True)
        if save:
            self.sync()
        else:
            self._ref.value = list(self.original_settings.values())

    def on_monitor_enabled(self, row: SwitchRow, value: bool) -> None:
        self.update_setting("disabled", "1" if not value else "0")

    def on_position(self, row: TextRow, text: str) -> None:
        if check_position(text):
            toggle_css_class(row.entry_box, "incorrect", False)
            self.update_setting("position", text)
        else:
            toggle_css_class(row.entry_box, "incorrect", True)

    def on_select_mode(self, row: DropdownRow, item: DropdownItem) -> None:
        if item is None:
            return
        self.custom_mode.set_visible(item.value == "custom")
        if item.value != "custom":
            self.update_setting("mode", item.value)

    def on_select_monitor(self, row: DropdownRow, item: DropdownItem) -> None:
        if item is None:
            return

        monitor_name = item.value
        if monitor_name == self.current_monitor:
            return
        self.current_monitor = monitor_name

        monitor = self.monitors.get(monitor_name)
        if monitor is None:
            return

        self.update_all(monitor)

    def on_scale(self, row: TextRow, value: str) -> None:
        if not value.isdigit():
            toggle_css_class(row.entry_box, "incorrect", True)
            return
        toggle_css_class(row.entry_box, "incorrect", False)

        self.update_setting("scale", float(value) / 100)

    def on_bitdepth(self, row: TextRow, value: str) -> None:
        if not value.isdigit():
            toggle_css_class(row.entry_box, "incorrect", True)
            return
        toggle_css_class(row.entry_box, "incorrect", False)

        self.update_setting("bitdepth", value)

    # Handler generators

    def make_text_handler(self, key: str) -> t.Callable[[TextRow, str], None]:
        def handler(this: MonitorsPage, row: TextRow, text: str) -> None:
            this.update_setting(key, text)
        func = types.MethodType(handler, self)
        setattr(self, f"on_{key}_handler", func)
        return func

    def make_dropdown_handler(
        self, key: str
    ) -> t.Callable[[DropdownRow, DropdownItem], None]:
        def handler(
            this: MonitorsPage, row: DropdownRow, item: DropdownItem
        ) -> None:
            this.update_setting(key, item.value)
        func = types.MethodType(handler, self)
        setattr(self, f"on_{key}_handler", func)
        return func

    # Update widgets

    def update_all(self, monitor: MonitorDict) -> None:
        self._finished = False
        self.update_modes(monitor)
        self.update_position(monitor)
        self.update_enabled(monitor)
        self.update_scale(monitor)
        self.update_color_management(monitor)
        self.update_mirror(monitor)
        self.update_vrr(monitor)
        self.update_transform(monitor)
        self.update_bitdepth(monitor)
        glib.idle_add(self.sync_finished)

    def update_bitdepth(self, monitor: MonitorDict) -> None:
        bitdepth = self.get_setting("bitdepth", monitor) or ""
        self.bitdepth.entry_update_text(bitdepth)

    def update_vrr(self, monitor: MonitorDict) -> None:
        vrr = self.get_setting("vrr", monitor) or ""
        self.vrr.set_current(vrr)

    def update_mirror(self, monitor: MonitorDict) -> None:
        mirror = self.get_setting("mirror", monitor) or ""
        self.mirror.entry_update_text(mirror)
        self.mirror.entry.set_max_width_chars(
            min(max(map(len, self.monitors.keys())), 15)
        )

    def update_transform(self, monitor: MonitorDict) -> None:
        transform = self.get_setting("transform", monitor) or "0"
        self.transform.set_current(transform)

    def update_color_management(self, monitor: MonitorDict) -> None:
        cm = self.get_setting("cm", monitor) or "srgb"
        self.color_management.set_current(cm)

    def update_enabled(self, monitor: MonitorDict) -> None:
        disabled = self.get_setting("disabled", monitor) or "0"
        self.monitor_enabled.switch_set_active(disabled == "0")

    def update_scale(self, monitor: MonitorDict) -> None:
        scale = self.get_setting("scale", monitor) or "1"
        self.scale.entry_update_text(str(int(float(scale) * 100)))

    def update_position(self, monitor: MonitorDict) -> None:
        pos = self.get_setting("position", monitor) or "auto"
        self.position.entry_update_text(pos)

    def update_modes(self, monitor: MonitorDict) -> None:
        if not monitor:
            return

        self.modes_items.clear()
        for _mode in monitor["availableModes"]:
            self.modes_items.append(DropdownItem(
                _mode, _mode
            ))
        self.modes_items.append(self._cached_custom)
        self.mode_selector.set_items(self.modes_items)

        if mode := self.get_setting("mode", monitor):
            if mode in monitor["availableModes"]:
                self.mode_selector.set_current(mode)
            else:
                self.mode_selector.set_current("custom")
                self.custom_mode.entry_update_text(mode)

    def destroy(self) -> None:
        for child in self.children:
            if isinstance(child, RowTemplate):
                child.destroy()

        for button, handler_id in self.button_handlers.items():
            button.disconnect(handler_id)

        if self._dialog:
            self._dialog.destroy()
            self._dialog = None
