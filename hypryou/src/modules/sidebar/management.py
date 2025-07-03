from repository import gtk, pango, gdk, bluetooth
from utils import Ref, toggle_css_class
import typing as t
from src.services.clock import full_date
from src.services.network import get_network, Primary
import os
from utils import colors
from src.services.idle_inhibitor import inhibited, get_inhibitor
from src.services.notifications import dnd
from src.services.hyprland import night_light
from src.services.state import open_settings, close_window
from src import widget

dnd_icon = Ref("do_not_disturb_off", name="dnd_icon")
dnd_icon.bind(
    dnd,
    lambda bool: "do_not_disturb_on" if bool else "do_not_disturb_off"
)


def open_settings_and_close(page: str) -> None:
    open_settings(page)
    close_window("sidebar")


class ManagementButton(gtk.Box):
    __gtype_name__ = "ManagementButton"

    def __init__(
        self,
        icon: str | Ref[str],
        label: str,
        state: str,
        activated: bool,
        on_click: t.Callable[[], None] | None = None,
        on_right_click: t.Callable[[], None] | None = None
    ) -> None:
        super().__init__(
            css_classes=("management-button",)
        )
        toggle_css_class(self, "activated", activated)
        self.icon = widget.Icon(icon)
        self.label = gtk.Label(
            label=label,
            halign=gtk.Align.START,
            css_classes=("label",)
        )
        self.state = gtk.Label(
            label=state,
            halign=gtk.Align.START,
            css_classes=("state",),
            ellipsize=pango.EllipsizeMode.END
        )
        self.text_box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            hexpand=True
        )

        self.arrow = widget.Icon("chevron_right") if on_right_click else None

        self.text_box.append(self.label)
        self.text_box.append(self.state)
        self.append(self.icon)
        self.append(self.text_box)
        if self.arrow:
            self.append(self.arrow)

        self.click_gesture = gtk.GestureClick.new()
        self.click_gesture.set_button(0)
        self.gesture_conn = (
            self.click_gesture.connect("released", self.on_click_released)
        )
        self.add_controller(self.click_gesture)

        self.on_click = on_click
        self.on_right_click = on_right_click

        self.activated = activated

    def on_click_released(
        self,
        gesture: gtk.GestureClick,
        n_press: int,
        x: int,
        y: int
    ) -> None:
        button_number = gesture.get_current_button()
        if button_number == gdk.BUTTON_PRIMARY:
            if self.on_click:
                self.on_click()
        elif button_number == gdk.BUTTON_SECONDARY:
            if self.on_right_click:
                self.on_right_click()

    def set_activated(self, value: bool) -> None:
        toggle_css_class(self, "activated", value)
        self.activated = value

    def destroy(self) -> None:
        self.icon.destroy()


class InfoBox(gtk.Box):
    __gtype_name__ = "InfoBox"

    def __init__(self) -> None:
        super().__init__(
            css_classes=("info-box",)
        )
        self.date = gtk.Label(
            css_classes=("date-label",),
            halign=gtk.Align.START,
            hexpand=True
        )
        self.username = gtk.Label(
            css_classes=("username-label",),
            halign=gtk.Align.END,
            label=os.getenv("USER", "Unknown user")
        )
        self.date.set_label(full_date.value)
        self.handler_id = full_date.watch(self.on_date_update)

        self.append(self.date)
        self.append(self.username)

    def on_date_update(self, new_value: str) -> None:
        self.date.set_label(new_value)

    def destroy(self) -> None:
        full_date.unwatch(self.handler_id)


class ManagementLine(gtk.Box):
    __gtype_name__ = "ManagementLine"

    def __init__(
        self,
        first_child: ManagementButton,
        second_child: ManagementButton
    ) -> None:
        super().__init__(
            homogeneous=True,
            css_classes=("management-line",)
        )
        self.first_child = first_child
        self.second_child = second_child
        self.append(first_child)
        self.append(second_child)

    def destroy(self) -> None:
        self.first_child.destroy()
        self.second_child.destroy()


class InternetButton(ManagementButton):
    __gtype_name__ = "InternetButton"

    def __init__(self) -> None:
        network = get_network()
        super().__init__(
            network.icon,
            "Internet",
            "UNKNOWN",
            False,
            self.toggle_wifi,
            lambda: open_settings_and_close("network")
        )
        self.on_update()
        network.watch("primary-changed", self.on_update)
        network.watch("state", self.on_update)
        if network.wifi:
            network.wifi.watch("access-point-changed", self.on_update)

    def toggle_wifi(self) -> None:
        network = get_network()
        if network.primary == Primary.WIFI and network.wifi:
            if not network.wifi.enabled:
                self.state.set_label("Connecting")
            network.wifi.enabled = not network.wifi.enabled

    def on_update(self) -> None:
        network = get_network()
        if network.primary == Primary.WIFI and network.wifi:
            wifi = network.wifi
            if wifi.enabled:
                self.set_activated(True)
                active_ap = wifi.active_access_point
                if active_ap:
                    self.state.set_label(active_ap.ssid)
                else:
                    self.state.set_label("Disconnected")
            else:
                self.set_activated(False)
                self.state.set_label("Off")
        elif network.primary == Primary.ETHERNET:
            self.state.set_label("Ethernet")
            self.set_activated(True)
        else:
            self.state.set_label("Unavailable")
            self.set_activated(False)


class BluetoothButton(ManagementButton):
    __gtype_name__ = "BluetoothButton"

    def __init__(self) -> None:
        self.bluetooth = bluetooth.get_default()
        super().__init__(
            "bluetooth_disabled",
            "Bluetooth",
            "UNKNOWN",
            False,
            self.toggle_bluetooth,
            lambda: open_settings_and_close("bluetooth")
        )
        self.on_update()
        self.handler = self.bluetooth.connect("notify", self.on_update)

    def destroy(self) -> None:
        self.bluetooth.disconnect(self.handler)
        super().destroy()

    def toggle_bluetooth(self) -> None:
        self.bluetooth.toggle()

    def on_update(self, *args: t.Any) -> None:
        is_connected = self.bluetooth.get_is_connected()
        is_powered = self.bluetooth.get_is_powered()
        if is_connected:
            self.set_activated(True)
            self.state.set_label("Connected")
            self.icon.set_label("bluetooth_connected")
        elif is_powered:
            self.set_activated(True)
            self.state.set_label("On")
            self.icon.set_label("bluetooth")
        else:
            self.set_activated(False)
            self.state.set_label("Off")
            self.icon.set_label("bluetooth_disabled")


class ToggleButton(ManagementButton):
    __gtype_name__ = "ToggleButton"

    def __init__(
        self,
        icon: str | Ref[str],
        label: str,
        activated: bool | Ref[bool],
        toggle: t.Callable[["ToggleButton", bool], None] | None = None,
        on_right_click: t.Callable[[], None] | None = None
    ) -> None:
        _activated = (
            activated.value if isinstance(activated, Ref)
            else activated
        )
        super().__init__(
            icon,
            label,
            "...",
            _activated,
            self.toggle,
            on_right_click
        )
        self.toggle_action = toggle
        if isinstance(activated, Ref):
            self.activated_ref = activated
            self.on_update()
            activated.watch(self.on_update)

    def toggle(self) -> None:
        if self.toggle_action:
            self.toggle_action(self, not self.activated)

    def on_update(self, *args: bool) -> None:
        if self.activated_ref.value:
            self.state.set_label("On")
            self.set_activated(True)
        else:
            self.state.set_label("Off")
            self.set_activated(False)


def toggle_dark_mode(self: ToggleButton, value: bool) -> None:
    colors.set_dark_mode(value)


def toggle_inhibitor(self: ToggleButton, value: bool) -> None:
    if value:
        get_inhibitor().inhibit()
    else:
        get_inhibitor().un_inhibit()


def toggle_dnd(self: ToggleButton, value: bool) -> None:
    dnd.value = value


def toggle_night_light(self: ToggleButton, value: bool) -> None:
    night_light.value = value


class ManagementFirstPage(gtk.Box):
    __gtype_name__ = "ManagementFirstPage"

    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL
        )

        self.internet = InternetButton()
        self.bluetooth = BluetoothButton()
        self.dark_mode = ToggleButton(
            "contrast",
            "Dark Mode",
            colors.dark_mode,
            toggle_dark_mode
        )
        self.dnd = ToggleButton(
            dnd_icon,
            "Do Not Disturb",
            dnd,
            toggle_dnd
        )
        self.idle_inhibitor = ToggleButton(
            "schedule",
            "Idle Inhibitor",
            inhibited,
            toggle_inhibitor
        )
        self.night_light = ToggleButton(
            "nightlight",
            "Night Light",
            night_light,
            toggle_night_light
        )
        self.lines = (
            ManagementLine(self.internet, self.bluetooth),
            ManagementLine(self.dark_mode, self.dnd),
            ManagementLine(self.idle_inhibitor, self.night_light)
        )
        for line in self.lines:
            self.append(line)

    def destroy(self) -> None:
        for line in self.lines:
            line.destroy()
            self.remove(line)


class ManagementBox(gtk.Box):
    __gtype_name__ = "ManagementBox"

    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL,
            css_classes=("management-box",)
        )
        self.stack = gtk.Stack(
            transition_type=gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            transition_duration=250,
            valign=gtk.Align.START
        )
        # NOTE: In the future I can add more pages
        self.first_page = ManagementFirstPage()
        self.stack.add_named(self.first_page, "1")
        self.stack.set_visible_child_name("1")

        self.info_box = InfoBox()

        self.append(self.info_box)
        self.append(self.stack)

    def destroy(self) -> None:
        self.info_box.destroy()
        self.first_page.destroy()
