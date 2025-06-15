from utils.ref import Ref
import src.widget as widget
from repository import gtk, gdk, glib
from config import HyprlandVars
from src.services.backlight import (
    get_backlight_manager, BacklightDevice,
    BacklightDeviceView
)
from src.services.audio import volume, volume_icon
import typing as t
from src.services.state import opened_windows
from math import ceil

window_counter = Ref(0, name="popup_counter")


class Popup(gtk.Revealer):
    def __init__(
        self,
        icon: str | Ref[str],
        max_value: int = 100
    ) -> None:
        self.max = max_value
        self.revealed = False
        self.box = gtk.Box(
            css_classes=("popup",),
            hexpand=True
        )
        super().__init__(
            css_classes=("popup-revealer",),
            child=self.box,
            reveal_child=False,
            transition_duration=250,
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN
        )
        self.icon = widget.Icon(icon)
        self.scale = gtk.Scale.new_with_range(
            gtk.Orientation.HORIZONTAL,
            0,
            max_value,
            1
        )
        self.scale.set_hexpand(True)
        self.label = gtk.Label(
            label="0%",
            halign=gtk.Align.END,
            css_classes=("percent",)
        )

        self.box.append(self.icon)
        self.box.append(self.scale)
        self.box.append(self.label)

        self.scale_handler = self.scale.connect(
            "value-changed", self.scale_changed
        )

        self.timer_handler = -1

    def update_percent(self) -> None:
        new_value = int(self.scale.get_value() / self.max * 100)
        new_label = f"{new_value}%"
        self.label.set_label(new_label)

    def scale_changed(self, *args: t.Any) -> None:
        self.update_percent()

    def reveal(self) -> None:
        if self.timer_handler != -1:
            glib.source_remove(self.timer_handler)
        self.timer_handler = glib.timeout_add(3000, self.un_reveal)

        if not self.revealed:
            self.revealed = True
            window_counter.value += 1
            self.set_reveal_child(True)

    def un_reveal(self) -> None:
        self.timer_handler = -1
        if self.revealed:
            self.revealed = False
            window_counter.value -= 1
            self.set_reveal_child(False)

    def destroy(self) -> None:
        self.icon.destroy()


class BrightnessPopup(Popup):
    def __init__(self, device: BacklightDevice) -> None:
        self.device = BacklightDeviceView(device)
        super().__init__(device.icon, 512)

        self.handler = device.watch(
            "changed-external",
            self.update_scale_value
        )
        self.update_scale_value(device.brightness, False)

    def update_scale_value(self, brightness: int, reveal: bool = True) -> None:
        if reveal and not opened_windows.is_visible("brightness"):
            value = ceil(brightness / self.device.max_brightness * self.max)
            self.scale.handler_block(self.scale_handler)
            self.scale.set_value(value)
            self.scale.handler_unblock(self.scale_handler)
            self.update_percent()
            self.reveal()
        elif self.revealed:
            self.un_reveal()

    def scale_changed(self, *args: t.Any) -> None:
        if not self.revealed:
            return
        scale_value = self.scale.get_value()
        value = ceil(scale_value / self.max * self.device.max_brightness)
        if value == self.device.brightness:
            return
        self.device.set_brightness(value)
        if not opened_windows.is_visible("brightness"):
            self.reveal()
        super().scale_changed(*args)


class VolumePopup(Popup):
    def __init__(self) -> None:
        super().__init__(volume_icon)

        self.handler = volume.watch(
            self.update_scale_value
        )
        self.update_scale_value(volume, False)

    def update_scale_value(
        self,
        new_value: float,
        reveal: bool = True
    ) -> None:
        if reveal and not opened_windows.is_visible("audio"):
            value = new_value
            self.scale.handler_block(self.scale_handler)
            self.scale.set_value(value)
            self.scale.handler_unblock(self.scale_handler)
            self.update_percent()
            self.reveal()
        elif self.revealed:
            self.un_reveal()

    def scale_changed(self, *args: t.Any) -> None:
        if not self.revealed:
            return
        volume.value = self.scale.get_value()
        if not opened_windows.is_visible("audio"):
            self.reveal()
        super().scale_changed(*args)


class PopupsWindow(widget.LayerWindow):
    def __init__(
        self,
        app: gtk.Application,
        monitor: gdk.Monitor
    ) -> None:
        super().__init__(
            app,
            margins={
                "top": HyprlandVars.gap
            },
            anchors={
                "top": True
            },
            monitor=monitor,
            name="popups",
            css_classes=("popups",)
        )
        self.child = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.manager = get_backlight_manager()
        self.child.append(BrightnessPopup(self.manager.devices[0]))
        self.child.append(VolumePopup())
        self.set_child(self.child)

        self.handler = window_counter.watch(
            self._update_visible
        )
        self._update_visible(window_counter.value)

    def _update_visible(self, new_counter: int) -> None:
        if new_counter > 0:
            self.show()
        else:
            self.hide()
