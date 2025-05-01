from repository import gtk, pango, gdk
from utils import widget, Ref, toggle_css_class
import typing as t
from src.variables.clock import full_date
from src.services.network import get_network, Primary
import os


# TODO: Make buttons work


class ManagementButton(gtk.Box):
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

    def destroy(self) -> None:
        self.icon.destroy()


class InfoBox(gtk.Box):
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
            label=os.getenv("USER")
        )
        self.date.set_label(full_date.value)
        full_date.watch(self.on_date_update)

        self.append(self.date)
        self.append(self.username)

    def on_date_update(self, new_value: str) -> None:
        self.date.set_label(new_value)

    def destroy(self) -> None:
        full_date.unwatch(self.on_date_update)


class ManagementLine(gtk.Box):
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
    def __init__(self) -> None:
        network = get_network()
        super().__init__(
            network.icon,
            "Internet",
            "UNKNOWN",
            False,
            self.toggle_wifi,
            on_right_click=lambda: None
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


class ManagementFirstPage(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL
        )

        self.internet = InternetButton()
        self.bluetooth = ManagementButton(
            "bluetooth",
            "Bluetooth",
            "Off",
            False,
            on_right_click=lambda: None
        )
        self.dark_mode = ManagementButton(
            "contrast",
            "Dark Mode",
            "On",
            True
        )
        self.dnd = ManagementButton(
            "do_not_disturb_off",
            "Do Not Disturb",
            "Off",
            False
        )
        self.idle_inhibitor = ManagementButton(
            "schedule",
            "Idle Inhibitor",
            "Off",
            False
        )
        self.night_light = ManagementButton(
            "nightlight",
            "Night Light",
            "Off",
            False
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
