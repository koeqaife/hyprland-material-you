import time
from utils.ref import Ref
import src.widget as widget
from repository import gtk, gdk, glib, layer_shell, pango
from src.services.backlight import (
    get_backlight_manager, BacklightDevice,
    BacklightDeviceView
)
from src.services.audio import volume, volume_icon, speaker_name
from src.services.audio import mic_volume, mic_icon, mic_name
from src.services.audio import recorders
import typing as t
from src.services.state import opened_windows
from src.services.upower import BatteryLevel, get_upower
from config import Settings
from math import ceil

window_counter = Ref[dict[int, int]]({}, name="popup_counter")


class TextPopup(gtk.Revealer):
    __gtype_name__ = "TextPopup"

    def __init__(
        self,
        num: int,
        icon: str | Ref[str],
        text: str,
        critical: bool = False
    ) -> None:
        self.event_counter = 0
        self.num = num
        self.revealed = False
        self.box = gtk.Box(
            css_classes=("popup", "text-popup"),
            hexpand=True
        )
        if critical:
            self.box.add_css_class("critical")
        super().__init__(
            css_classes=("popup-revealer",),
            child=self.box,
            reveal_child=False,
            transition_duration=250,
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN
        )
        self.name = gtk.Label(
            label=text,
            halign=gtk.Align.START,
            css_classes=("name",),
            ellipsize=pango.EllipsizeMode.END
        )
        self.icon = widget.Icon(
            icon,
            valign=gtk.Align.CENTER
        )
        self.box.append(self.icon)
        self.box.append(self.name)

        self.timer_handler = -1

    def reveal(self) -> None:
        if self.timer_handler != -1:
            glib.source_remove(self.timer_handler)
        self.timer_handler = glib.timeout_add(5000, self.un_reveal)

        if not self.revealed:
            self.revealed = True
            window_counter.value[self.num] += 1
            glib.idle_add(self.set_reveal_child, True)

    def un_reveal(self) -> None:
        self.timer_handler = -1
        if self.revealed:
            self.set_reveal_child(False)
            self.revealed = False
            window_counter.value[self.num] -= 1

    def destroy(self) -> None:
        self.icon.destroy()


class Popup(gtk.Revealer):
    __gtype_name__ = "Popup"

    def __init__(
        self,
        icon: str | Ref[str],
        num: int,
        name: str,
        max_value: int = 100
    ) -> None:
        self.num = num
        self.event_counter = 0
        self.max = max_value
        self.revealed = False
        self.vbox = gtk.Box(
            css_classes=("popup",),
            hexpand=True,
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("popup-revealer",),
            child=self.vbox,
            reveal_child=False,
            transition_duration=250,
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN
        )
        self.name = gtk.Label(
            label=name,
            halign=gtk.Align.START,
            css_classes=("name",),
            ellipsize=pango.EllipsizeMode.END
        )
        self.icon = widget.Icon(
            icon,
            valign=gtk.Align.END
        )
        self.scale = gtk.Scale.new_with_range(
            gtk.Orientation.HORIZONTAL,
            0,
            max_value,
            1
        )
        self.scale.set_hexpand(True)
        self.percent = gtk.Label(
            label="0%",
            halign=gtk.Align.END,
            css_classes=("percent",)
        )

        self.name_box = gtk.Box(
            valign=gtk.Align.END
        )
        self.scale_box = gtk.Box()

        self.scale_box.append(self.scale)
        self.scale_box.append(self.percent)

        self.name_box.append(self.icon)
        self.name_box.append(self.name)

        self.vbox.append(self.name_box)
        self.vbox.append(self.scale_box)

        self.scale_handler = self.scale.connect(
            "value-changed", self.scale_changed
        )

        self.timer_handler = -1

    def update_percent(self) -> None:
        new_value = int(self.scale.get_value() / self.max * 100)
        new_label = f"{new_value}%"
        self.percent.set_label(new_label)

    def scale_changed(self, *args: t.Any) -> None:
        self.update_percent()

    def reveal(self) -> None:
        if self.timer_handler != -1:
            glib.source_remove(self.timer_handler)
        self.timer_handler = glib.timeout_add(3000, self.un_reveal)

        if not self.revealed:
            self.revealed = True
            window_counter.value[self.num] += 1
            glib.idle_add(self.set_reveal_child, True)

    def un_reveal(self) -> None:
        self.timer_handler = -1
        if self.revealed:
            self.set_reveal_child(False)
            self.revealed = False
            window_counter.value[self.num] -= 1

    def destroy(self) -> None:
        self.icon.destroy()


class BrightnessPopup(Popup):
    __gtype_name__ = "BrightnessPopup"

    def __init__(self, device: BacklightDevice, num: int) -> None:
        self.device = BacklightDeviceView(device)
        super().__init__(device.icon, num, "Brightness", 512)

        self.handler = self.device.watch(
            "changed-external",
            self.update_scale_value
        )
        self.update_scale_value(device.brightness, False)

    def destroy(self) -> None:
        self.device.unwatch(self.handler)
        self.device.destroy()
        super().destroy()

    def update_scale_value(self, brightness: int, reveal: bool = True) -> None:
        self.event_counter += 1
        if self.event_counter < 3:
            return
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
    __gtype_name__ = "VolumePopup"

    def __init__(
        self,
        num: int,
        icon: str | Ref[str],
        volume: Ref[float],
        name: Ref[str],
        show_if: t.Callable[[], bool]
    ) -> None:
        super().__init__(icon, num, "unknown")

        self.is_ready = [False, False]
        self.show_if = show_if
        self.volume = volume
        self.name_ref = name
        self.update_scale_value(self.volume.value, False)
        self.handler = self.volume.watch(
            self.update_scale_value
        )
        self.name_handler = self.name_ref.watch(
            self.on_name_change
        )

    def destroy(self) -> None:
        self.volume.unwatch(self.handler)
        super().destroy()

    def on_name_change(self, new_value: str) -> None:
        self.is_ready[0] = True
        self.name.set_label(new_value)
        if self.show_if() and all(self.is_ready):
            self.reveal()

    def update_scale_value(
        self,
        new_value: float,
        reveal: bool = True
    ) -> None:
        self.event_counter += 1
        if self.event_counter < 3:
            return

        self.scale.handler_block(self.scale_handler)
        self.scale.set_value(new_value)
        self.scale.handler_unblock(self.scale_handler)
        self.update_percent()

        self.is_ready[1] = True
        if reveal and self.show_if() and all(self.is_ready):
            self.reveal()
        elif self.revealed:
            self.un_reveal()

    def scale_changed(self, *args: t.Any) -> None:
        if not self.revealed:
            return
        self.volume.value = self.scale.get_value()
        self.name_ref.unwatch(self.name_handler)
        if self.show_if():
            self.reveal()
        super().scale_changed(*args)


class PopupsWindow(widget.LayerWindow):
    __gtype_name__ = "PopupsWindow"

    def __init__(
        self,
        app: gtk.Application,
        monitor: gdk.Monitor,
        num: int
    ) -> None:
        self.num = num
        window_counter.value[num] = 0
        self.timeout: int | None = None
        super().__init__(
            app,
            anchors={
                "top": True
            },
            monitor=monitor,
            name="popups",
            css_classes=("popups",),
            layer=layer_shell.Layer.OVERLAY,
            visible=False
        )
        self.child = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )

        self.manager = get_backlight_manager()
        if self.manager.devices:
            self.brightness = BrightnessPopup(self.manager.devices[0], num)
            self.child.append(self.brightness)

        self.volume = VolumePopup(
            num, volume_icon, volume, speaker_name,
            show_if=lambda: (not opened_windows.is_visible("audio"))
        )
        self.child.append(self.volume)

        self.mic_volume = VolumePopup(
            num, mic_icon, mic_volume, mic_name,
            show_if=lambda: (not opened_windows.is_visible("mics"))
        )
        self.child.append(self.mic_volume)

        self.mic_is_using = TextPopup(
            num,
            "mic_double",
            "An application is recording",
        )
        self.child.append(self.mic_is_using)

        self.low_battery = TextPopup(
            num,
            "battery_alert",
            "You have low battery!",
            True
        )
        self.child.append(self.low_battery)

        self.set_child(self.child)

        self.handler = window_counter.watch(
            self._update_visible
        )
        self._update_visible(window_counter.value)

        self.last_recorders_len = 0
        self.gaps_out_handler = Settings().watch(
            "hyprland.gaps_out", self.on_gaps_out,
            True
        )
        self.recorders_handler = recorders.watch(
            self.on_recorders
        )
        self.last_upower_message = 0
        self.upower_handler = get_upower().watch("changed", self.on_upower)
        self.on_upower()

    def on_upower(self, *args: t.Any) -> None:
        upower = get_upower()
        if upower.is_battery and upower.is_present:
            is_critical = (
                upower.battery_level == BatteryLevel.CRITICAL
                or upower.percentage <= 10
            )
            now = time.monotonic()
            if is_critical and self.last_upower_message < now - 300:
                self.last_upower_message = time.monotonic()
                self.low_battery.reveal()

    def on_recorders(self, *args: t.Any) -> None:
        if len(recorders.value) > self.last_recorders_len:
            self.mic_is_using.reveal()
        elif len(recorders.value) == 0:
            self.mic_is_using.un_reveal()
        self.last_recorders_len = len(recorders.value)

    def show(self) -> None:
        self.timeout = None
        super().show()

    def hide(self) -> None:
        self.timeout = None
        counter = window_counter.value[self.num]
        if counter > 0:
            return
        super().hide()

    def _update_visible(self, new: dict[int, int]) -> None:
        new_counter = new[self.num]
        if new_counter > 0:
            self.show()
        else:
            if self.timeout:
                glib.source_remove(self.timeout)
                self.timeout = None
            self.timeout = glib.timeout_add(250, self.hide)

    def destroy(self) -> None:
        if getattr(self, "brightness"):
            self.brightness.destroy()
        self.volume.destroy()
        recorders.unwatch(self.recorders_handler)
        get_upower().unwatch(self.upower_handler)
        del window_counter.value[self.num]
        super().destroy()
