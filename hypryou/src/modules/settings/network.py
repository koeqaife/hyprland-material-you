from repository import gtk, glib
from src.modules.settings.base import RowTemplate
from src.services.network import get_network, AccessPoint
from src.services.network import DeviceState, DeviceStateReason
from src.services.apps import launch_detached
import typing as t
from utils import toggle_css_class
import src.widget as widget


class WifiToggle(RowTemplate):
    __gtype_name__ = "SettingsWifiToggle"

    def __init__(self) -> None:
        self.network = get_network()
        super().__init__(
            "Wi-Fi",
            "Find and connect to Wi-Fi networks",
            css_classes=("wifi-toggle-row",)
        )
        self.switch = gtk.Switch(
            valign=gtk.Align.CENTER,
            tooltip_text="Toggle",
        )
        self.scan = gtk.Button(
            css_classes=("icon-tonal", "scan-button"),
            child=widget.Icon("refresh"),
            tooltip_text="Scan",
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )
        self.append(self.switch)
        self.append(self.scan)

        self.switch_handler = self.switch.connect(
            "notify::active", self.on_switch_changed
        )
        self.network_handler = self.network.watch("state", self.on_update)
        self.scan_handler = self.scan.connect(
            "clicked", self.on_scan
        )
        if self.network.wifi:
            self.wifi_scan_handler = self.network.wifi.watch(
                "scanning", self.on_scanning
            )
        else:
            self.wifi_scan_handler = None
        self.on_update()

    def on_scanning(self, state: bool) -> None:
        self.scan.set_sensitive(not state)
        if state:
            self.scan.set_tooltip_text("Scanning...")
        else:
            self.scan.set_tooltip_text("Scan")

    def on_scan(self, *args: t.Any) -> None:
        self.network.wifi.scan()

    def on_click(self) -> None:
        self.switch.activate()

    def on_secondary_click(self):
        launch_detached("nm-connection-editor")

    def on_update(self) -> None:
        if self.network.wifi:
            self.set_sensitive(True)
            enabled = self.network.wifi.enabled
            self.switch.handler_block(self.switch_handler)
            self.switch.set_active(enabled)
            self.switch.handler_unblock(self.switch_handler)
        else:
            self.set_sensitive(False)

    def on_switch_changed(self, *args: t.Any) -> None:
        wifi = self.network.wifi
        if wifi:
            wifi.enabled = self.switch.get_active()

    def destroy(self) -> None:
        super().destroy()
        self.switch.disconnect(self.switch_handler)
        self.network.unwatch(self.network_handler)
        self.scan.disconnect(self.scan_handler)
        if self.wifi_scan_handler:
            self.network.wifi.unwatch(self.wifi_scan_handler)


class AccessPointRow(RowTemplate):
    __gtype_name__ = "SettingsAccessPoint"

    def __init__(self, ap: AccessPoint) -> None:
        self.ap = ap
        self.aps: dict[str, AccessPoint] = {}
        super().__init__(
            ap.ssid or "",
            "Saved" if ap.is_saved else None,
            ("wifi-access-point",)
        )
        self.icon = widget.Icon(
            "",
            css_classes=("wifi-strength",)
        )
        self.prepend(self.icon)
        if ap.is_secure:
            self.secure_icon = widget.Icon(
                "lock",
                css_classes=("is-secure",)
            )
            self.append(self.secure_icon)

        self.ap_handlers: dict[AccessPoint, int] = {}
        self._last_active = False
        self.on_changed()
        self.add_ap(ap)

    def update_primary_ap(self) -> None:
        if len(self.aps) == 0:
            return
        best_ap = max(list(self.aps.values()), key=lambda ap: ap.strength)
        self.ap = best_ap

    def add_ap(self, ap: AccessPoint) -> int:
        self.ap_handlers[ap] = ap.watch("changed", self.on_changed)
        self.aps[ap.bssid] = ap
        return len(self.aps)

    def rem_ap(self, bssid: str) -> int:
        ap = self.aps.pop(bssid, None)
        if ap in self.ap_handlers.keys():
            handler = self.ap_handlers.pop(ap, None)
            if handler is not None:
                ap.unwatch(handler)
        self.update_primary_ap()
        return len(self.aps)

    def on_click(self) -> None:
        if self.ap.is_saved:
            self.ap.try_to_connect()
        else:
            self.ap.connect_new()

    def on_changed(self) -> None:
        self.update_icon()
        self.label.set_label(self.ap.ssid or "")
        self.set_visible(bool(self.ap.ssid))
        self.update_primary_ap()

    def set_is_active(self, value: bool) -> None:
        toggle_css_class(self, "active", value)
        if self._last_active != value:
            self._last_active = value
            if not value:
                self.set_description("Saved" if self.ap.is_saved else None)

    def update_icon(self, *args: t.Any) -> None:
        self.icon.set_label(self.ap.get_icon())

    def destroy(self) -> None:
        for ap, handler in self.ap_handlers.items():
            ap.unwatch(handler)
        super().destroy()


state_map = {
    DeviceState.UNKNOWN: "Unknown state",
    DeviceState.UNMANAGED: "Not Managed",
    DeviceState.UNAVAILABLE: "Unavailable",
    DeviceState.DISCONNECTED: "Disconnected",
    DeviceState.PREPARE: "Preparing...",
    DeviceState.CONFIG: "Configuring...",
    DeviceState.NEED_AUTH: "Authentication...",
    DeviceState.IP_CONFIG: "Getting IP...",
    DeviceState.IP_CHECK: "Checking IP...",
    DeviceState.SECONDARIES: "Finalizing...",
    DeviceState.ACTIVATED: "Connected",
    DeviceState.DEACTIVATING: "Disconnecting...",
    DeviceState.FAILED: "Connection Failed",
}


class WifiList(gtk.Box):
    __gtype_name__ = "SettingsWifiList"

    def __init__(self) -> None:
        self.network = get_network()
        self.wifi = self.network.wifi
        self.bssid_ssid_map: dict[str, str] = {}
        super().__init__(
            css_classes=("wifi-list",),
            vexpand=True,
            orientation=gtk.Orientation.VERTICAL
        )
        if not self.wifi:
            self.append(
                gtk.Label(
                    label="Wifi not available",
                    css_classes=("not-available",)
                )
            )
            return
        self.items: dict[str, AccessPointRow] = {}
        for ap in self.network.wifi.access_points.values():
            self.bssid_ssid_map[ap.bssid] = ap.ssid
            if ap.ssid in self.items.keys():
                self.items[ap.ssid].add_ap(ap)
                continue
            row = AccessPointRow(ap)
            self.items[ap.ssid] = row

        sorted_rows = sorted(
            self.items.values(),
            key=lambda row: row.ap.strength,
            reverse=True
        )
        for row in sorted_rows:
            self.append(row)

        self.wifi_handlers = (
            self.wifi.watch("access-point-added", self.on_ap_added),
            self.wifi.watch("access-point-removed", self.on_ap_rem),
            self.wifi.watch("access-point-changed", self.on_active),
            self.wifi.watch("state-changed", self.on_state_changed),
        )
        self._last_active_ap: tuple[str, AccessPointRow] | None = None
        self.on_active()

    def set_active_description(self, state: DeviceState) -> None:
        if self._last_active_ap is None:
            return
        self._last_active_ap[1].set_description(
            state_map.get(state, "Unknown state")
        )

    def on_state_changed(
        self,
        new_state: DeviceState,
        old_state: DeviceState,
        reason: DeviceStateReason
    ) -> None:
        self.set_active_description(new_state)

    def on_active(self, *args: t.Any) -> None:
        active_ap = self.network.wifi.active_access_point
        ssid = active_ap.ssid if active_ap else None
        if not ssid:
            return

        if self._last_active_ap and ssid != self._last_active_ap[0]:
            self._last_active_ap[1].set_is_active(False)
            self._last_active_ap = None

        if not self._last_active_ap and active_ap:
            if ssid not in self.items.keys():
                row = AccessPointRow(active_ap)
                self.items[ssid] = row
                self.insert_child_after(row, None)
            else:
                row = self.items[ssid]
                self.reorder_child_after(row, None)
            row.set_is_active(True)
            self._last_active_ap = (ssid, row)
            self.set_active_description(
                self.wifi.state
            )

    def on_ap_added(self, ap: AccessPoint, bssid: str) -> None:
        if ap.ssid is None:
            return
        self.bssid_ssid_map[bssid] = ap.ssid
        if ap.ssid in self.items.keys():
            self.items[ap.ssid].add_ap(ap)
            return
        row = AccessPointRow(ap)
        self.items[ap.ssid] = row
        self.append(row)

    def on_ap_rem(self, bssid: str) -> None:
        ssid = self.bssid_ssid_map.pop(bssid, None)
        if ssid is None:
            return
        if ssid not in self.items.keys():
            return
        row = self.items[ssid]
        left = row.rem_ap(bssid)
        if left <= 0:
            if self._last_active_ap and row is self._last_active_ap[1]:
                self._last_active_ap = None
            row.destroy()
            self.remove(row)
            del self.items[ssid]

    def destroy(self) -> None:
        if not hasattr(self, "wifi_handlers"):
            return
        for handler in self.wifi_handlers:
            self.wifi.unwatch(handler)


class NetworkPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsNetworkPage"

    def __init__(self) -> None:
        self.network = get_network()
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("network-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.list = WifiList()
        self.toggle = WifiToggle()
        self.box.append(self.toggle)
        self.box.append(self.list)

        self.timeout_id = -1
        self.once_scan = False

    def scan_wifi(self) -> bool:
        if not self.network.wifi:
            self.timeout_id = -1
            return False
        self.network.wifi.scan()
        return True

    def on_show(self) -> None:
        if not self.once_scan:
            self.scan_wifi()
            self.once_scan = True
        self.timeout_id = glib.timeout_add(60000, self.scan_wifi)

    def on_hide(self) -> None:
        if self.timeout_id != -1:
            glib.source_remove(self.timeout_id)
            self.timeout_id = -1

    def destroy(self) -> None:
        self.toggle.destroy()
        self.list.destroy()
