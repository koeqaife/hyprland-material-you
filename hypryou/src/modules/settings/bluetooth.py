import threading
from repository import gtk, bluetooth, gdk, gio, glib
from src.modules.settings.base import RowTemplate
from src.services.apps import launch_detached
import typing as t
from utils import toggle_css_class
import src.widget as widget
from collections import defaultdict


class BluetoothToggle(RowTemplate):
    __gtype_name__ = "BluetoothToggle"

    def __init__(self) -> None:
        self.bluetooth = bluetooth.get_default()
        super().__init__(
            "Bluetooth",
            "Toggle Bluetooth and find nearby devices",
            css_classes=("bluetooth-toggle-row",)
        )
        self.switch = widget.Switch(
            valign=gtk.Align.CENTER,
            tooltip_text="Toggle",
        )
        self.discover_icon = widget.Icon("search")
        self.discover = gtk.Button(
            css_classes=("icon-tonal", "discover-button"),
            child=self.discover_icon,
            tooltip_text="Scan devices",
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )
        self.append(self.switch)
        self.append(self.discover)

        self.switch_handler = self.switch.connect(
            "notify::active", self.on_switch_changed
        )
        self.powered_handler = self.bluetooth.connect(
            "notify::is-powered", self.on_update
        )
        self.discover_handler = self.discover.connect(
            "clicked", self.on_discover
        )
        self.adapter = self.bluetooth.get_adapter()
        if self.adapter:
            self.discovering_handler = self.adapter.connect(
                "notify::discovering", self.on_discovering
            )
        else:
            self.discover_handler = None
        self.on_update()

    def on_discovering(self, *args: t.Any) -> None:
        if self.adapter.get_discovering():
            self.discover.set_tooltip_text("Stop scanning")
            self.discover_icon.set_label("cancel")
        else:
            self.discover.set_tooltip_text("Scan")
            self.discover_icon.set_label("search")

    def on_discover(self, *args: t.Any) -> None:
        adapter = self.bluetooth.get_adapter()
        if adapter:
            if not adapter.get_discovering():
                adapter.start_discovery()
            else:
                adapter.stop_discovery()

    def on_click(self) -> None:
        self.switch.activate()

    def on_secondary_click(self):
        launch_detached("blueman-manager")

    def on_update(self, *args: t.Any) -> None:
        self.set_sensitive(True)
        enabled = self.bluetooth.get_is_powered()
        self.switch.handler_block(self.switch_handler)
        self.switch.set_active(enabled)
        self.switch.handler_unblock(self.switch_handler)

    def on_switch_changed(self, *args: t.Any) -> None:
        adapter = self.bluetooth.get_adapter()
        if adapter:
            adapter.set_powered(self.switch.get_active())

    def destroy(self) -> None:
        super().destroy()
        self.switch.disconnect(self.switch_handler)
        self.bluetooth.disconnect(self.powered_handler)
        self.discover.disconnect(self.discover_handler)
        if self.discovering_handler and self.adapter:
            self.adapter.disconnect(self.discovering_handler)
        if self.adapter and self.adapter.get_discovering():
            self.adapter.stop_discovery()


icons_map = defaultdict(
    lambda: "bluetooth",
    {
        "audio-headphones": "headphones",
        "audio-headset": "headset_mic",
        "camera-web": "camera",
        "computer": "computer",
        "input-gaming": "gamepad",
        "input-mouse": "mouse",
        "input-keyboard": "keyboard",
        "microphone": "mic",
        "phone": "smartphone",
        "printer": "print",
        "printer-network": "print",
        "scanner": "scan",
        "video-display": "monitor",
        "bluetooth": "bluetooth",
        "audio-card": "media_output",
        "audio-speakers": "speaker"
    }
)


class BluetoothDevice(RowTemplate):
    __gtype_name__ = "SettingsBluetoothDevice"

    def __init__(self, device: bluetooth.Device) -> None:
        self.device = device
        super().__init__(
            device.get_name() or "Unknown",
            device.get_address(),
            css_classes=("bluetooth-device",)
        )
        self.address = device.get_address()
        self.icon = widget.Icon(
            icons_map[device.get_icon()],
            valign=gtk.Align.CENTER
        )
        self.prepend(self.icon)

        self.handlers = (
            self.device.connect("notify::connecting", self.on_connecting),
            self.device.connect("notify::connected", self.on_connected),
        )
        self.update_description()

        self.menu = gio.Menu()
        self.popover = gtk.PopoverMenu()
        self.popover.set_parent(self)
        self.popover.set_has_arrow(False)
        self.update_menu()

    def update_menu(self, *args: t.Any) -> None:
        self.menu.remove_all()
        connected = self.device.get_connected() or self.device.get_connecting()
        self.menu.append(
            "Connect" if not connected else "Disconnect",
            "connect"
        )
        self.menu.append(
            "Copy address",
            "copy_address"
        )
        self.popover.set_menu_model(self.menu)

    def copy(self, *args: t.Any) -> None:
        display = gdk.Display.get_default()
        clipboard = display.get_clipboard()
        clipboard.set_content(
            gdk.ContentProvider.new_for_bytes(
                "text/plain;charset=utf-8",
                glib.Bytes.new(self.address.encode())
            )
        )

    def on_click_released(
        self,
        gesture: gtk.GestureClick,
        n_press: int,
        x: int,
        y: int
    ) -> None:
        button_number = gesture.get_current_button()
        if button_number == gdk.BUTTON_PRIMARY:
            self.on_click()
        elif button_number == gdk.BUTTON_SECONDARY:
            self.on_secondary_click(x, y)

    def connect_action(self, *args: t.Any) -> None:
        self.on_click()

    def on_click(self) -> None:
        if self.device.get_connected() or self.device.get_connecting():
            self.device.disconnect_device()
            self.set_description("Disconnecting...")
        else:
            if self.device.get_paired():
                self.device.connect_device()
            else:
                _bluetooth = bluetooth.get_default()
                adapter = _bluetooth.get_adapter()
                adapter.set_pairable(True)

                def pair_async():
                    try:
                        self.device.pair()
                        self.device.connect_device()
                    except glib.Error:
                        pass

                threading.Thread(target=pair_async, daemon=True).start()

    def on_secondary_click(self, x: int, y: int) -> None:
        rect = gdk.Rectangle()
        rect.x = x
        rect.y = y
        self.popover.set_pointing_to(rect)
        self.popover.popup()

    def update_description(self) -> None:
        if self.device.get_connecting():
            self.set_description("Connecting...")
            toggle_css_class(self, "active", True)
        elif self.device.get_connected():
            self.set_description("Connected")
            toggle_css_class(self, "active", True)
        else:
            self.set_description(self.address)
            toggle_css_class(self, "active", False)

    def on_connecting(self, *args: t.Any) -> None:
        self.update_description()
        self.update_menu()

    def on_connected(self, *args: t.Any) -> None:
        self.update_description()
        self.update_menu()

    def destroy(self) -> None:
        for handler in self.handlers:
            self.device.disconnect(handler)
        super().destroy()


BluetoothDevice.install_action("connect", None, BluetoothDevice.connect_action)
BluetoothDevice.install_action("copy_address", None, BluetoothDevice.copy)


class BluetoothList(gtk.Box):
    __gtype_name__ = "SettingsBluetoothList"

    def __init__(self) -> None:
        self.bluetooth = bluetooth.get_default()
        self.adapter = self.bluetooth.get_adapter()
        super().__init__(
            css_classes=("bluetooth-list",),
            vexpand=True,
            orientation=gtk.Orientation.VERTICAL
        )
        if not self.adapter:
            self.append(
                gtk.Label(
                    label="Bluetooth not available",
                    css_classes=("not-available",)
                )
            )
            return
        self.items: dict[str, BluetoothDevice] = {}

        for device in self.bluetooth.get_devices():
            row = BluetoothDevice(device)
            self.items[device.get_address()] = row
            self.append(row)

        self.devices_handler = self.bluetooth.connect(
            "notify",
            self.on_devices
        )

    def on_devices(self, *args: t.Any) -> None:
        device_map = {
            device.get_address(): device
            for device in self.bluetooth.get_devices()
        }
        current_addresses = set(device_map.keys())
        previous_addresses = set(self.items.keys())

        added = current_addresses - previous_addresses
        removed = previous_addresses - current_addresses

        for addr in added:
            device = device_map[addr]
            if device:
                row = BluetoothDevice(device)
                self.items[addr] = row
                self.append(row)

        for addr in removed:
            row = self.items.pop(addr, None)
            if row:
                row.destroy()
                self.remove(row)

    def destroy(self, *args: t.Any) -> None:
        self.bluetooth.disconnect(self.devices_handler)
        for device in self.items.values():
            device.destroy()


class BluetoothPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsBluetoothPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("bluetooth-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.list = BluetoothList()
        self.toggle = BluetoothToggle()
        self.box.append(self.toggle)
        self.box.append(self.list)

        self.timeout_id = -1
        self.once_scan = False

    def destroy(self) -> None:
        self.toggle.destroy()
        self.list.destroy()
