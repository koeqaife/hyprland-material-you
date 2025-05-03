from enum import Enum
from repository import nm
from utils.logger import logger
import typing as t
from utils.service import Signals
from utils import Ref

# I used some logic from Astal by Aylur (LGPLv2.1)
# They have other programming language (Vala), so not all logic here is their


class State(int, Enum):
    UNKNOWN = 0
    ASLEEP = 10
    DISCONNECTED = 20
    DISCONNECTING = 30
    CONNECTING = 40
    CONNECTED_LOCAL = 50
    CONNECTED_SITE = 60
    CONNECTED_GLOBAL = 70


class Connectivity(int, Enum):
    UNKNOWN = 0
    NONE = 1
    PORTAL = 2
    LIMITED = 3
    FULL = 4


class DeviceState(int, Enum):
    UNKNOWN = 0,
    UNMANAGED = 10,
    UNAVAILABLE = 20,
    DISCONNECTED = 30,
    PREPARE = 40,
    CONFIG = 50,
    NEED_AUTH = 60,
    IP_CONFIG = 70,
    IP_CHECK = 80,
    SECONDARIES = 90,
    ACTIVATED = 100,
    DEACTIVATING = 110,
    FAILED = 120


class Primary(int, Enum):
    WIFI = 0
    ETHERNET = 1
    UNKNOWN = 2


class Mode80211(int, Enum):
    UNKNOWN = 0
    ADHOC = 1
    INFRA = 2
    AP = 3
    MESH = 4


class ApFlags80211(int, Enum):
    NONE = 0
    PRIVACY = 1
    WPS = 2
    WPS_PBC = 4
    WPS_PIN = 8


class ApSecurityFlags80211(int, Enum):
    NONE = 0
    PAIR_WEP40 = 1
    PAIR_WEP104 = 2
    PAIR_TKIP = 4
    PAIR_CCMP = 8
    GROUP_WEP40 = 16
    GROUP_WEP104 = 32
    GROUP_TKIP = 64
    GROUP_CCMP = 128
    KEY_MGMT_PSK = 256
    KEY_MGMT_802_1X = 512
    KEY_MGMT_SAE = 1024
    KEY_MGMT_OWE = 2048
    KEY_MGMT_OWE_TM = 4096
    KEY_MGMT_EAP_SUITE_B_192 = 8192


class Internet(int, Enum):
    CONNECTED = 0
    CONNECTING = 1
    DISCONNECTED = 2

    @staticmethod
    def from_device(device: nm.Device) -> "Internet":
        if device is None or device.get_active_connection() is None:
            return Internet.DISCONNECTED

        conn = device.get_active_connection()
        match (conn.get_state()):
            case nm.ActiveConnectionState.ACTIVATED:
                return Internet.CONNECTED
            case nm.ActiveConnectionState.ACTIVATING:
                return Internet.CONNECTING
            case _:
                return Internet.DISCONNECTED


class AccessPoint(Signals):
    def __init__(self, ap: nm.AccessPoint):
        super().__init__()
        self.ap = ap
        self.bandwidth: int = ap.get_bandwidth()
        self.bssid: str = ap.get_bssid()
        self.frequency: int = ap.get_frequency()
        self.last_seen: int = ap.get_last_seen()
        self.max_bitrate: int = ap.get_max_bitrate()
        self.strength: int = ap.get_strength()
        self.mode: Mode80211 = ap.get_mode()
        self.flags: ApFlags80211 = ap.get_flags()
        self.rsn_flags: ApFlags80211 = ap.get_rsn_flags()
        self.wpa_flags: ApFlags80211 = ap.get_wpa_flags()

        _ssid = ap.get_ssid()
        if _ssid is not None:
            self.ssid = nm.utils_ssid_to_utf8(_ssid.get_data())
        else:
            self.ssid = None

        self.handler = ap.connect("notify::strength", self.strength_changed)

    def dispose(self) -> None:
        self.ap.disconnect(self.handler)

    def strength_changed(self, *_: t.Any) -> None:
        self.strength = self.ap.get_strength()
        self.notify("changed")


class Wifi(Signals):
    def __init__(
        self,
        device: nm.DeviceWifi,
        client: nm.Client
    ) -> None:
        super().__init__()
        self.device = device
        self.client = client
        self.active_connection: nm.ActiveConnection | None = None
        self.connection_handler = 0

        self.nm_active_access_point: nm.AccessPoint | None = None
        self.active_access_point: AccessPoint | None = None
        self.ap_handler = 0

        self.access_points: dict[str, AccessPoint] = {}
        self.is_hotspot = False
        self.internet = Internet.DISCONNECTED

        self.state: DeviceState = device.get_state()
        self.icon = "signal_wifi_bad"

        for ap in device.get_access_points():
            self.access_points[ap.get_bssid()] = AccessPoint(ap)

        device.connect("access-point-added", self.on_access_point_added)
        device.connect("access-point-removed", self.on_access_point_removed)
        device.connect("notify", self.update_icon)
        self.client.connect("notify", self.update_icon)

        self.on_active_connection()
        device.connect("notify::active-connection", self.on_active_connection)

        self.on_active_access_point()
        device.connect(
            "notify::active-access-point", self.on_active_access_point
        )

    def on_access_point_added(self, _: t.Any, ap: nm.AccessPoint) -> None:
        self.access_points[ap.get_bssid()] = AccessPoint(ap)
        self.notify("access-points")

    def on_access_point_removed(self, _: t.Any, ap: nm.AccessPoint) -> None:
        bssid = ap.get_bssid()
        if bssid in self.access_points:
            self.access_points[bssid].dispose()
            del self.access_points[bssid]
            self.notify("access-points")

    def on_active_connection(self, *_: t.Any) -> None:
        if self.connection_handler > 0 and self.active_connection:
            self.active_connection.disconnect(self.connection_handler)
            self.connection_handler = 0
            self.active_connection = None

        active_connection = self.device.get_active_connection()
        self.is_hotspot = self.get_is_hotspot()
        if active_connection is not None:
            def update_device(*_: t.Any) -> None:
                self.internet = Internet.from_device(self.device)
            update_device()
            self.connection_handler = active_connection.connect(
                "notify::state", update_device
            )
        self.notify("active-connection-changed")

    def on_access_point_changed(self, *_: t.Any) -> None:
        self.update_icon()

    def on_active_access_point(self, *_: t.Any) -> None:
        nm_ap = self.device.get_active_access_point()
        if nm_ap == self.nm_active_access_point:
            return

        if self.ap_handler > 0 and self.active_access_point:
            self.active_access_point.unwatch("changed", self.ap_handler)
            self.ap_handler = 0
            self.active_access_point = None

        if nm_ap is not None:
            ap = AccessPoint(nm_ap)
            self.active_access_point = ap
            self.on_access_point_changed()
            self.ap_handler = ap.watch("changed", self.on_access_point_changed)
            self.notify("access-point-changed")

    def get_icon(self) -> str:
        if not self.enabled:
            return "signal_wifi_off"

        if self.internet == Internet.CONNECTED:
            if self.is_hotspot:
                return "wifi_tethering"
            if self.client.get_connectivity() != nm.ConnectivityState.FULL:
                return "signal_wifi_statusbar_not_connected"
            if self.active_access_point is None:
                return "signal_wifi_4_bar"

            strength = self.active_access_point.strength
            if strength >= 80:
                return "signal_wifi_4_bar"
            if strength >= 60:
                return "network_wifi_3_bar"
            if strength >= 40:
                return "network_wifi_2_bar"
            if strength >= 20:
                return "network_wifi_1_bar"

            return "signal_wifi_0_bar"

        if self.internet == Internet.CONNECTING:
            return "signal_wifi_0_bar"

        return "signal_wifi_bad"

    def update_icon(self, *_: t.Any) -> None:
        old_icon = self.icon
        self.icon = self.get_icon()
        if self.icon != old_icon:
            self.notify("icon-changed")

    def get_is_hotspot(self) -> bool:
        active_conn = self.device.get_active_connection()
        if active_conn is None:
            return False

        conn = active_conn.get_connection()
        if conn is None:
            return False

        ip4config = conn.get_setting_ip4_config()
        if ip4config is None:
            return False

        return bool(
            ip4config.get_method() == nm.SETTING_IP4_CONFIG_METHOD_SHARED
        )

    def scan(self) -> None:
        self.device.request_scan_async(
            None, None, None
        )

    @property
    def enabled(self) -> bool:
        return bool(self.client.wireless_get_enabled())

    @enabled.setter
    def enabled(self, new_value: bool) -> None:
        self.client.wireless_set_enabled(new_value)


class Network(Signals):
    def __init__(self) -> None:
        super().__init__()
        self.wifi_device: nm.DeviceWifi | None
        self.wired_device: nm.DeviceEthernet | None
        self.wifi: Wifi | None = None

        self.icon = Ref("signal_wifi_statusbar_not_connected")

        self.client: nm.Client
        self.primary = Primary.UNKNOWN
        try:
            self.client = nm.Client.new(None)
            self.wifi_device = self.get_device(nm.DeviceType.WIFI)
            self.wired_device = self.get_device(nm.DeviceType.ETHERNET)

            if self.wifi_device:
                self.wifi = Wifi(self.wifi_device, self.client)
                self.wifi.watch("icon-changed", self.update_icon)

            self.sync()
            self.client.connect("notify::primary-connection", self.sync)
            self.client.connect("notify::activating-connection", self.sync)

            self.client.connect(
                "notify::state",
                lambda *_: self.notify("state")
            )
            self.client.connect(
                "notify::activating-connection",
                lambda *_: self.notify("activating-connection")
            )
        except Exception as e:
            logger.critical(
                "Couldn't initialize Network: %s",
                e, exc_info=e
            )

    def sync(self, *_: t.Any) -> None:
        old_primary = self.primary
        ac = self.client.get_primary_connection()

        if ac is None:
            ac = self.client.get_activating_connection()

        if ac is None:
            pass
        elif ac.get_connection_type() == "802-11-wireless":
            self.primary = Primary.WIFI
        elif ac.get_connection_type() == "802-3-ethernet":
            self.primary = Primary.ETHERNET

        if self.primary != old_primary:
            self.notify("primary-changed")
            self.update_icon()

    def update_icon(self) -> None:
        if self.primary == Primary.WIFI and self.wifi:
            self.icon.value = self.wifi.icon
        elif self.primary == Primary.ETHERNET:
            self.icon.value = "cable"
        else:
            self.icon.value = "signal_wifi_statusbar_not_connected"

    def get_device(self, type: nm.DeviceType) -> nm.Device | None:
        valid: list[nm.Device] = []

        for device in self.client.get_devices():
            if device.get_device_type() == type:
                valid.append(device)

        for device in valid:
            if device.get_active_connection() is not None:
                return device

        if len(valid) > 0:
            return valid[0]

        return None


_instance: Network | None = None


def get_network() -> Network:
    global _instance
    if _instance is None:
        _instance = Network()
    return _instance
