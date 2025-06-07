from utils import widget, toggle_css_class
from utils.logger import logger
from repository import gtk, layer_shell
from src.services.backlight import BacklightDevice, get_backlight_manager
from config import HyprlandVars
import weakref
import typing as t

SCALE_MAX = 512


class DeviceItem(gtk.Box):
    def __init__(self, item: BacklightDevice, number: int) -> None:
        super().__init__(
            valign=gtk.Align.START,
            hexpand=True,
            css_classes=("brightness-item",),
            orientation=gtk.Orientation.VERTICAL
        )
        self._item = item
        self.info_box = gtk.Box(
            css_classes=("info-box",),
            hexpand=True
        )
        self.icon = widget.Icon(item.icon)
        self.label = gtk.Label(
            label=f"Device {number}",
            css_classes=("label",),
            tooltip_text=item.device,
            hexpand=True,
            halign=gtk.Align.START
        )
        self.percent = gtk.Label(
            label="50%",
            css_classes=("percent",),
            halign=gtk.Align.END
        )
        self.info_box.append(self.icon)
        self.info_box.append(self.label)
        self.info_box.append(self.percent)

        self.scale = gtk.Scale.new_with_range(
            gtk.Orientation.HORIZONTAL,
            0, SCALE_MAX, 1
        )
        self.scale.set_hexpand(True)

        self.append(self.info_box)
        self.append(self.scale)

        self.handler = item.watch("changed-external", self.update_scale_value)
        self.update_scale_value(item.brightness)

        self.scale_handler = self.scale.connect(
            "value-changed", self.scale_changed
        )

    def update_percent(self) -> None:
        scale_value = self.scale.get_value()
        value = scale_value / SCALE_MAX * 100
        self.percent.set_label(f"{round(value)}%")

    def scale_changed(self, *args: t.Any) -> None:
        scale_value = self.scale.get_value()
        value = scale_value / SCALE_MAX * self._item.max_brightness
        self._item.set_brightness(int(value))
        self.update_percent()

    def update_scale_value(self, brightness: int) -> None:
        value = brightness / self._item.max_brightness * SCALE_MAX
        self.scale.set_value(value)
        self.update_percent()

    def destroy(self) -> None:
        self._item.unwatch("changed-external", self.handler)


class DevicesBox(gtk.ScrolledWindow):
    def __init__(self) -> None:
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.list = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            spacing=8
        )

        self.box.append(self.list)

        self.items: dict[int, DeviceItem] = {}
        super().__init__(
            child=self.box,
            css_classes=("brightness-devices-scroll",),
            vscrollbar_policy=gtk.PolicyType.NEVER,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        weakref.finalize(
            self,
            lambda: logger.debug("brightness.DevicesBox finalized")
        )

        devices = get_backlight_manager().devices
        for i, device in enumerate(devices, 1):
            item = DeviceItem(device, i)
            self.items[i] = item
            self.list.append(item)

        if len(self.items) > 5:
            self.set_policy(
                vscrollbar_policy=gtk.PolicyType.ALWAYS,
                hscrollbar_policy=gtk.PolicyType.NEVER
            )
            toggle_css_class(self, "with-min-height")

    def destroy(self) -> None:
        for key, item in self.items.items():
            item.destroy()
            self.list.remove(item)
        self.items.clear()
        self.set_child(None)


class BrightnessWindow(widget.LayerWindow):
    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            anchors={
                "top": True,
                "right": True
            },
            margins={
                "top": HyprlandVars.gap,
                "right": HyprlandVars.gap
            },
            css_classes=("brightness",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            hide_on_esc=True,
            name="brightness",
            height=1,
            width=400,
            setup_popup=True
        )
        self._child: DevicesBox | None = None

        weakref.finalize(
            self, lambda: logger.debug("BrightnessWindow finalized")
        )

    def on_show(self) -> None:
        self._child = DevicesBox()
        self.set_child(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
        self.set_child(None)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
