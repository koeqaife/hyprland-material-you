from __future__ import annotations
from enum import Enum
import os
import threading
import time

from src.services.dbus import cache_proxy_properties, system_bus
from repository import gio, glib
from utils.ref import Ref
from utils.logger import logger
from utils.service import Service, Signals
import typing as t


class BatteryState(int, Enum):
    UNKNOWN = 0
    CHARGING = 1
    DISCHARGING = 2
    EMPTY = 3
    FULL_CHARGED = 4
    PENDING_CHARGE = 5
    PENDING_DISCHARGE = 6


class BatteryLevel(int, Enum):
    UNKNOWN = 0
    NONE = 1
    LOW = 3
    CRITICAL = 4
    NORMAL = 6
    HIGH = 7
    FULL = 8


class LidMonitor:
    """Monitor laptop lid state and trigger appropriate actions"""
    
    def __init__(self) -> None:
        self.lid_path = "/proc/acpi/button/lid/LID/state"
        self.monitoring = False
        self.last_state = None
        self._thread: threading.Thread | None = None
        
        if os.path.exists("/proc/acpi/button/lid"):
            self.start_monitoring()
    
    def start_monitoring(self) -> None:
        """Start monitoring lid state in background thread"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.debug("Started lid monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring lid state"""
        self.monitoring = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.debug("Stopped lid monitoring")
    
    def _get_lid_state(self) -> str | None:
        """Get current lid state from proc filesystem"""
        try:
            if os.path.exists(self.lid_path):
                with open(self.lid_path, 'r') as f:
                    content = f.read().strip()
                    # Format: "state:      open" or "state:      closed"
                    if 'open' in content:
                        return 'open'
                    elif 'closed' in content:
                        return 'closed'
            return None
        except (OSError, IOError) as e:
            logger.warning(f"Failed to read lid state: {e}")
            return None
    
    def _monitor_loop(self) -> None:
        """Monitor loop running in background thread"""
        while self.monitoring:
            try:
                current_state = self._get_lid_state()
                
                if current_state and current_state != self.last_state:
                    if current_state == 'closed' and self.last_state == 'open':
                        # Lid was just closed
                        glib.idle_add(self._trigger_lid_action)
                    
                    self.last_state = current_state
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                logger.error(f"Error in lid monitoring loop: {e}")
                time.sleep(1.0)
    
    def _trigger_lid_action(self) -> None:
        """Trigger lid action in main thread"""
        try:
            from src.modules.power import handle_lid_action
            handle_lid_action()
        except ImportError as e:
            logger.error(f"Failed to import handle_lid_action: {e}")


battery_icons: dict[str, dict[int, str]] = {
    "discharging": {
        0: "battery_0_bar",
        20: "battery_1_bar",
        30: "battery_2_bar",
        40: "battery_3_bar",
        50: "battery_4_bar",
        60: "battery_5_bar",
        80: "battery_6_bar"
    },
    "charging": {
        0: "battery_charging_20",
        20: "battery_charging_20",
        30: "battery_charging_30",
        50: "battery_charging_50",
        60: "battery_charging_60",
        80: "battery_charging_80",
        99: "battery_full"
    }
}


class UPower(Signals):
    def __init__(self) -> None:
        super().__init__()
        self._proxy = gio.DBusProxy.new_sync(
            system_bus,
            gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.UPower",
            "/org/freedesktop/UPower/devices/DisplayDevice",
            "org.freedesktop.UPower.Device",
            None
        )
        self._conn = self._proxy.get_connection()
        self.conns = [
            self._proxy.connect(
                "g-properties-changed", self.properties_changed
            ),
            self._proxy.connect(
                "g-signal", self.on_dbus_signal
            )
        ]
        self.battery_icon = Ref("battery_unknown", name="battery_icon")
        self._cache_properties()

    def prop(self, property_name: str) -> t.Any:
        value = self._proxy.get_cached_property(property_name)
        if value is None:
            return None
        return value.unpack()

    def update_icon(self, *args: t.Any) -> None:
        if not self.is_battery:
            self.battery_icon.value = "battery_unknown"
            return
        thresholds: dict[int, str] | None = None
        if self.state == BatteryState.DISCHARGING:
            thresholds = battery_icons["discharging"]
        elif self.state == BatteryState.CHARGING:
            thresholds = battery_icons["charging"]
        elif self.state == BatteryState.FULL_CHARGED:
            self.battery_icon.value = "battery_full"
            return
        else:
            self.battery_icon.value = "battery_unknown"
            return

        if not thresholds:
            self.battery_icon.value = "battery_unknown"
            return

        icon = "battery_0_bar"
        percent = self.percentage
        for threshold in sorted(thresholds.keys()):
            if percent >= threshold:
                icon = thresholds[threshold]
            else:
                break

        self.battery_icon.value = icon

    @property
    def is_battery(self) -> bool:
        return self.type == 2

    @property
    def type(self) -> int:
        return t.cast(int, self.prop("Type"))

    @property
    def state(self) -> BatteryState:
        return t.cast(BatteryState, self.prop("State"))

    @property
    def percentage(self) -> int:
        return t.cast(int, self.prop("Percentage"))

    @property
    def is_present(self) -> bool:
        return t.cast(bool, self.prop("IsPresent"))

    @property
    def battery_level(self) -> BatteryLevel:
        return t.cast(BatteryLevel, self.prop("BatteryLevel"))

    def on_dbus_signal(
        self,
        proxy: gio.DBusProxy,
        bus_name: str,
        signal_name: str,
        signal_args: glib.Variant
    ) -> None:
        pass

    def properties_changed(
        self,
        proxy: gio.DBusProxy,
        changed_properties_variant: glib.Variant,
        invalid_properties: list[str]
    ) -> None:
        changed_properties = t.cast(
            dict[str, str],
            changed_properties_variant.unpack()
        )
        self._cache_properties(list(changed_properties.keys()))

    def call_method(
        self,
        method_name: str,
        params: glib.Variant,
        callback: t.Callable[..., None] | None = None
    ) -> None:
        self._proxy.call(
            method_name,
            params,
            gio.DBusCallFlags.NONE,
            -1,
            None,
            callback,
            None
        )

    def _cache_properties(self, changed: list[str] | None = None) -> None:
        cache_proxy_properties(
            self._conn,
            self._proxy,
            changed,
            self._cache_properties_finish
        )

    def _cache_properties_finish(self, *args: t.Any) -> None:
        self.update_icon()
        self.notify("changed")


_instance: UPower | None = None


def get_upower() -> UPower:
    if not _instance:
        raise RuntimeError(
            "Couldn't get instance of upower. " +
            "Most likely it's not initialized."
        )

    return _instance


class UPowerService(Service):
    def app_init(self) -> None:
        global _instance
        if __debug__:
            logger.debug("Starting upower proxy")
        _instance = UPower()
        
        # Initialize lid monitor
        self.lid_monitor = LidMonitor()
    
    def app_destroy(self) -> None:
        if hasattr(self, 'lid_monitor'):
            self.lid_monitor.stop_monitoring()
