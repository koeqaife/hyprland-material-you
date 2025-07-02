from enum import Enum, Flag
from repository import nm, glib, gio, gtk
from utils.logger import logger
import typing as t
from utils.service import Signals, Service
from utils import Ref
from config import CONFIG_DIR
import os
from src.services.dbus import system_bus

# I used some logic from Astal by Aylur (LGPLv2.1)
# They have other programming language (Vala), so not all logic here is their

AGENT_XML_PATH = os.path.join(
    CONFIG_DIR, "assets", "dbus",
    "org.freedesktop.NetworkManager.SecretAgent.xml"
)
with open(AGENT_XML_PATH) as f:
    AGENT_XML = f.read()

SECRET_AGENT_FAILED = "org.freedesktop.NetworkManager.SecretAgent.Error.Failed"


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
    UNKNOWN = 0
    UNMANAGED = 10
    UNAVAILABLE = 20
    DISCONNECTED = 30
    PREPARE = 40
    CONFIG = 50
    NEED_AUTH = 60
    IP_CONFIG = 70
    IP_CHECK = 80
    SECONDARIES = 90
    ACTIVATED = 100
    DEACTIVATING = 110
    FAILED = 120


class DeviceStateReason(int, Enum):
    NONE = 0
    UNKNOWN = 1
    NOW_MANAGED = 2
    NOW_UNMANAGED = 3
    CONFIG_FAILED = 4
    IP_CONFIG_UNAVAILABLE = 5
    IP_CONFIG_EXPIRED = 6
    NO_SECRETS = 7
    SUPPLICANT_DISCONNECT = 8
    SUPPLICANT_CONFIG_FAILED = 9
    SUPPLICANT_FAILED = 10
    SUPPLICANT_TIMEOUT = 11
    PPP_START_FAILED = 12
    PPP_DISCONNECT = 13
    PPP_FAILED = 14
    DHCP_START_FAILED = 15
    DHCP_ERROR = 16
    DHCP_FAILED = 17
    SHARED_START_FAILED = 18
    SHARED_FAILED = 19
    AUTOIP_START_FAILED = 20
    AUTOIP_ERROR = 21
    AUTOIP_FAILED = 22
    MODEM_BUSY = 23
    MODEM_NO_DIAL_TONE = 24
    MODEM_NO_CARRIER = 25
    MODEM_DIAL_TIMEOUT = 26
    MODEM_DIAL_FAILED = 27
    MODEM_INIT_FAILED = 28
    GSM_APN_FAILED = 29
    GSM_REGISTRATION_NOT_SEARCHING = 30
    GSM_REGISTRATION_DENIED = 31
    GSM_REGISTRATION_TIMEOUT = 32
    GSM_REGISTRATION_FAILED = 33
    GSM_PIN_CHECK_FAILED = 34
    FIRMWARE_MISSING = 35
    REMOVED = 36
    SLEEPING = 37
    CONNECTION_REMOVED = 38
    USER_REQUESTED = 39
    CARRIER = 40
    CONNECTION_ASSUMED = 41
    SUPPLICANT_AVAILABLE = 42
    MODEM_NOT_FOUND = 43
    BT_FAILED = 44
    GSM_SIM_NOT_INSERTED = 45
    GSM_SIM_PIN_REQUIRED = 46
    GSM_SIM_PUK_REQUIRED = 47
    GSM_SIM_WRONG = 48
    INFINIBAND_MODE = 49
    DEPENDENCY_FAILED = 50
    BR2684_FAILED = 51
    MODEM_MANAGER_UNAVAILABLE = 52
    SSID_NOT_FOUND = 53
    SECONDARY_CONNECTION_FAILED = 54
    DCB_FCOE_FAILED = 55
    TEAMD_CONTROL_FAILED = 56
    MODEM_FAILED = 57
    MODEM_AVAILABLE = 58
    SIM_PIN_INCORRECT = 59
    NEW_ACTIVATION = 60
    PARENT_CHANGED = 61
    PARENT_MANAGED_CHANGED = 62
    OVSDB_FAILED = 63
    IP_ADDRESS_DUPLICATE = 64
    IP_METHOD_UNSUPPORTED = 65
    SRIOV_CONFIGURATION_FAILED = 66
    PEER_NOT_FOUND = 67
    DEVICE_HANDLER_FAILED = 68
    UNMANAGED_BY_DEFAULT = 69
    UNMANAGED_EXTERNAL_DOWN = 70
    UNMANAGED_LINK_NOT_INIT = 71
    UNMANAGED_QUITTING = 72
    UNMANAGED_SLEEPING = 73
    UNMANAGED_USER_CONF = 74
    UNMANAGED_USER_EXPLICIT = 75
    UNMANAGED_USER_SETTINGS = 76
    UNMANAGED_USER_UDEV = 77


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


class ApFlags80211(int, Flag):
    NONE = 0
    PRIVACY = 1
    WPS = 2
    WPS_PBC = 4
    WPS_PIN = 8


class ApSecurityFlags80211(int, Flag):
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


def get_saved_connection_for_ssid(
    client: nm.Client,
    ssid: str
) -> nm.RemoteConnection | None:
    for conn in client.get_connections():
        s_con = conn.get_setting_connection()
        s_wifi = conn.get_setting_wireless()
        if not s_con or not s_wifi:
            continue

        ssid_bytes = s_wifi.get_ssid()
        if not ssid_bytes:
            continue

        conn_ssid = ssid_bytes.get_data().decode()
        if conn_ssid != ssid:
            continue

        s_sec = conn.get_setting_wireless_security()
        if s_sec:
            if s_sec.get_property("psk") or s_sec.get_property("key-mgmt"):
                return conn
        else:
            return conn

    return None


class AccessPoint(Signals):
    def __init__(
        self,
        ap: nm.AccessPoint,
        client: nm.Client,
        device: nm.Device
    ) -> None:
        super().__init__(True)
        self.ap = ap
        self.client = client
        self.device = device
        self.bandwidth: int = ap.get_bandwidth()
        self.bssid: str = ap.get_bssid()
        self.frequency: int = ap.get_frequency()
        self.last_seen: int = ap.get_last_seen()
        self.max_bitrate: int = ap.get_max_bitrate()
        self.strength: int = ap.get_strength()
        self.mode = Mode80211(ap.get_mode())
        self.flags = ApFlags80211(ap.get_flags())
        self.rsn_flags = ApSecurityFlags80211(ap.get_rsn_flags())
        self.wpa_flags = ApSecurityFlags80211(ap.get_wpa_flags())

        _ssid = ap.get_ssid()
        if _ssid is not None:
            self.ssid = nm.utils_ssid_to_utf8(_ssid.get_data())
        else:
            self.ssid = None

        self.strength_handler = ap.connect(
            "notify::strength",
            self.strength_changed
        )
        self.ssid_handler = ap.connect(
            "notify::ssid",
            self.ssid_changed
        )

    @property
    def is_secure(self) -> bool:
        return (
            self.wpa_flags != ApSecurityFlags80211.NONE
            or self.rsn_flags != ApSecurityFlags80211.NONE
        )

    @property
    def is_saved(self) -> bool:
        conn = get_saved_connection_for_ssid(self.client, self.ssid)
        return conn is not None

    def try_to_connect(self) -> None:
        conn = get_saved_connection_for_ssid(self.client, self.ssid)

        if conn is not None:
            self.client.activate_connection_async(
                conn,
                self.device,
                None,
                None,
                None,
                None
            )

    def connect_new(self) -> None:
        if __debug__:
            logger.debug("Trying to connect to %s", self.ssid)

        connection = nm.SimpleConnection()

        s_con = nm.SettingConnection(
            id=self.ssid,
            type="802-11-wireless",
            uuid=nm.utils_uuid_generate()
        )
        connection.add_setting(s_con)

        s_wifi = nm.SettingWireless(
            ssid=glib.Bytes.new(self.ssid.encode()),
            mode="infrastructure"
        )
        connection.add_setting(s_wifi)

        s_ip4 = nm.SettingIP4Config(
            method="auto"
        )
        connection.add_setting(s_ip4)

        self.client.add_and_activate_connection2(
            connection,
            self.device,
            self.ap.get_path(),
            glib.Variant("a{sv}", ()),
            None,
            None,
            None
        )

    def dispose(self) -> None:
        self.ap.disconnect(self.strength_handler)
        self.ap.disconnect(self.ssid_handler)

    def strength_changed(self, *_: t.Any) -> None:
        self.strength = self.ap.get_strength()
        self.notify("changed")

    def ssid_changed(self, *_: t.Any) -> None:
        _ssid = self.ap.get_ssid()
        if _ssid is not None:
            self.ssid = nm.utils_ssid_to_utf8(_ssid.get_data())
        else:
            self.ssid = None
        self.notify("changed")

    def get_icon(self) -> str:
        if self.strength >= 80:
            return "signal_wifi_4_bar"
        if self.strength >= 60:
            return "network_wifi_3_bar"
        if self.strength >= 40:
            return "network_wifi_2_bar"
        if self.strength >= 20:
            return "network_wifi_1_bar"

        return "signal_wifi_0_bar"


class Wifi(Signals):
    def __init__(
        self,
        device: nm.DeviceWifi,
        client: nm.Client
    ) -> None:
        super().__init__(True)
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

        self.state = DeviceState(device.get_state())
        self.icon = "signal_wifi_bad"

        for ap in device.get_access_points():
            bssid = ap.get_bssid()
            self.access_points[bssid] = AccessPoint(
                ap, client, device
            )

        device.connect("access-point-added", self.on_access_point_added)
        device.connect("access-point-removed", self.on_access_point_removed)
        device.connect("notify", self.update_icon)
        device.connect(
            "state-changed",
            self.on_state_changed
        )
        self.client.connect("notify", self.update_icon)

        self.on_active_connection()
        device.connect("notify::active-connection", self.on_active_connection)

        self.on_active_access_point()
        device.connect(
            "notify::active-access-point", self.on_active_access_point
        )

        self.scanning = False
        self._last_scan = device.get_last_scan()

    def on_state_changed(
        self,
        device: nm.DeviceWifi,
        new_state: nm.DeviceState,
        old_state: nm.DeviceState,
        reason: nm.DeviceStateReason
    ) -> None:
        self.notify_sync(
            "state-changed",
            DeviceState(new_state),
            DeviceState(old_state),
            DeviceStateReason(reason)
        )
        self.state = DeviceState(new_state)

    def on_access_point_added(self, _: t.Any, ap: nm.AccessPoint) -> None:
        bssid = ap.get_bssid()
        if bssid not in self.access_points:
            access_point = AccessPoint(
                ap, self.client, self.device
            )
            self.access_points[bssid] = access_point
            self.notify("access-points")
            self.notify("access-point-added", access_point, bssid)

    def on_access_point_removed(self, _: t.Any, ap: nm.AccessPoint) -> None:
        bssid = ap.get_bssid()
        if bssid in self.access_points:
            self.access_points[bssid].dispose()
            del self.access_points[bssid]
            self.notify("access-points")
            self.notify("access-point-removed", bssid)

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
            self.active_access_point.unwatch(self.ap_handler)
            self.ap_handler = 0
            self.active_access_point = None

        if nm_ap is not None:
            ap = AccessPoint(nm_ap, self.client, self.device)
            self.active_access_point = ap
            self.on_access_point_changed()
            self.ap_handler = ap.watch("changed", self.on_access_point_changed)
            self.notify("access-point-changed")
        else:
            self.active_access_point = None
            self.on_access_point_changed()
            self.notify("access-point-changed")
        self.nm_active_access_point = nm_ap

    def get_icon(self) -> str:
        if not self.enabled:
            return "signal_wifi_off"

        if self.internet == Internet.CONNECTED:
            if self.is_hotspot:
                return "wifi_tethering"
            if self.client.get_connectivity() != nm.ConnectivityState.FULL:
                return "signal_wifi_statusbar_not_connected"
            if self.active_access_point is None:
                return "signal_wifi_statusbar_not_connected"

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

    def scan_check(self) -> bool:
        if self.device.get_last_scan() != self._last_scan:
            self.scanning = False
            self.notify("scanning", False)
            return False
        return True

    def scan_finish(
        self,
        device: nm.DeviceWifi,
        result: gio.AsyncResult,
        user_data: None
    ) -> None:
        self._last_scan = self.device.get_last_scan()
        self.scanning = True
        self.device.request_scan_finish(result)
        self.notify("scanning", True)
        glib.timeout_add(1000, self.scan_check)

    def scan(self) -> None:
        if self.scanning:
            return
        self.device.request_scan_async(
            None, self.scan_finish, None
        )

    @property
    def enabled(self) -> bool:
        return bool(self.client.wireless_get_enabled())

    @enabled.setter
    def enabled(self, new_value: bool) -> None:
        self.client.wireless_set_enabled(new_value)

    def deactivate_connection(
        self,
        conn: nm.ActiveConnection | None = None
    ) -> nm.RemoteConnection | None:
        ac_conn = conn or self.device.get_active_connection()
        if not ac_conn:
            return
        if ac_conn.get_state() not in (
            nm.ActiveConnectionState.DEACTIVATED,
            nm.ActiveConnectionState.DEACTIVATING
        ):
            self.client.deactivate_connection(ac_conn, None)
            return ac_conn.get_connection()


class Network(Signals):
    def __init__(
        self,
        client: nm.Client
    ) -> None:
        super().__init__()
        self.client = client
        self.agent = SecretAgent(self.client)
        self.wifi_device: nm.DeviceWifi | None
        self.wired_device: nm.DeviceEthernet | None
        self.wifi: Wifi | None = None

        self.icon = Ref(
            "signal_wifi_statusbar_not_connected",
            name="wifi_icon"
        )

        self.client: nm.Client
        self.primary = Primary.UNKNOWN
        try:
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


class UserCanceled:
    ...


if t.TYPE_CHECKING:
    class SecretsDialog(gtk.ApplicationWindow):
        def __init__(
            self,
            ssid: str,
            callback: t.Callable[[str | UserCanceled | None], None]
        ) -> None:
            ...

        def on_close_request(self, *args: t.Any) -> None:
            ...

        def on_cancel(self, *args: t.Any) -> None:
            ...

        def on_connect(self, *args: t.Any) -> None:
            ...

        def destroy(self) -> None:
            ...

        def on_text(self, *args: t.Any) -> None:
            ...

        def on_entry_enter(self, *args: t.Any) -> None:
            ...

        def return_value(self, value: str | None) -> None:
            ...


class SecretPromptHandler:
    widget: "SecretsDialog | None" = None

    @staticmethod
    def set_widget(widget: t.Any) -> None:
        SecretPromptHandler.widget = t.cast("SecretsDialog", widget)

    def __init__(
        self,
        conn: gio.DBusConnection,
        invocation: gio.DBusMethodInvocation,
        setting_name: str,
        hints: list[str],
        flags: int,
        ssid: str,
        on_finish: t.Callable[[], None]
    ) -> None:
        self.ssid = ssid
        self.conn = conn
        self.invocation = invocation
        self.setting_name = setting_name
        self.hints = hints
        self.flags = flags
        self._on_finish = on_finish
        self.dialog: SecretsDialog | None = None

        if __debug__:
            logger.debug(
                "SecretPromptHandler: setting: %s, hints: %s, flags: %d",
                setting_name, hints, flags
            )

        self.ask()

    def on_finish(self) -> None:
        if self.dialog:
            self.dialog.destroy()
        self._on_finish()

    def cancel(self) -> None:
        self.on_dialog_finish(UserCanceled())

    def on_dialog_finish(self, password: str | UserCanceled | None) -> None:
        if password is None:
            self.invocation.return_value(None)
        elif isinstance(password, UserCanceled):
            self.invocation.return_dbus_error(
                "org.freedesktop.NetworkManager.SecretAgent.Error",
                "User canceled the operation"
            )
        else:
            secrets = {
                self.setting_name: {
                    "psk": glib.Variant("s", password)
                }
            }
            self.invocation.return_value(
                glib.Variant("(a{sa{sv}})", (secrets,))
            )
        self.on_finish()

    def ask(self) -> None:
        if self.widget is None:
            self.on_dialog_finish(None)
            raise RuntimeError(
                "Var widget is not set! Most likely is not initialized. " +
                "Aborting..."
            )
        if not self.dialog:
            self.dialog = self.widget(self.ssid, self.on_dialog_finish)
            self.dialog.present()


class SecretAgent:
    def __init__(
        self,
        client: nm.Client
    ) -> None:
        self.client = client
        self.node_info = gio.DBusNodeInfo.new_for_xml(AGENT_XML)
        self.iface = self.node_info.interfaces[0]
        self.active_prompts: dict[str, SecretPromptHandler] = {}

    def register(self) -> int:
        if __debug__:
            logger.debug("Registering interface '%s'", self.iface.name)

        system_bus.register_object(
            "/org/freedesktop/NetworkManager/SecretAgent",
            self.iface,
            self.handle_bus_call
        )

        if __debug__:
            logger.debug("Registering SecretAgent in NM/AgentManager")
        proxy = gio.DBusProxy.new_sync(
            system_bus,
            gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.NetworkManager",
            "/org/freedesktop/NetworkManager/AgentManager",
            "org.freedesktop.NetworkManager.AgentManager",
            None
        )
        caps = nm.SecretAgentCapabilities.NONE

        proxy.call_sync(
            "RegisterWithCapabilities",
            glib.Variant("(su)", (
                "com.koeqaife.SecretAgent",
                caps,
            )),
            gio.DBusCallFlags.NONE,
            -1,
            None,
        )

    def handle_bus_call(
        self,
        conn: gio.DBusConnection,
        sender: str,
        path: str,
        interface: str,
        target: str,
        params: glib.Variant,
        invocation: gio.DBusMethodInvocation,
        user_data: t.Any = None,
    ) -> None:
        match target:
            case "GetSecrets":
                conn_dict, path, setting_name, hints, flags = params.unpack()
                connection = conn_dict.get("connection", {})
                ssid = str(connection.get("id", "Unknown"))

                prompt_key = f"{path}:{setting_name}"

                if prompt_key in self.active_prompts:
                    logger.warning("Prompt already active for %s", prompt_key)
                    invocation.return_dbus_error(
                        SECRET_AGENT_FAILED,
                        "Prompt already active"
                    )
                    return

                prompt = SecretPromptHandler(
                    conn,
                    invocation,
                    setting_name,
                    hints,
                    flags,
                    ssid,
                    lambda key=prompt_key: (
                        self.active_prompts.pop(key, None)
                    )
                )

                self.active_prompts[prompt_key] = prompt
            case "CancelGetSecrets":
                path, setting_name = params.unpack()
                prompt_key = f"{path}:{setting_name}"

                prompt = self.active_prompts.pop(prompt_key, None)
                if prompt:
                    prompt.cancel()

                invocation.return_value(None)
            case "SaveSecrets":
                invocation.return_value(None)
            case "DeleteSecrets":
                invocation.return_value(None)


_instance: Network | None = None


def get_network() -> Network:
    if not _instance:
        raise RuntimeError(
            "Couldn't get instance of Network. " +
            "Most likely it's not initialized."
        )

    return _instance


class NetworkService(Service):
    def app_init(self) -> None:
        global _instance
        self.client = nm.Client.new()
        _instance = Network(self.client)

    def start(self) -> None:
        _instance.agent.register()
