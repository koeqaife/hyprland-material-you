import asyncio
import os
from config import CONFIG_DIR
from utils.service import Service
from repository import gio, glib
from utils.logger import logger
import typing as t
from pywayland.client.display import Display
from pywayland.protocol.wayland.wl_seat import WlSeat
from pywayland.protocol.wayland.wl_registry import WlRegistryProxy
from pywayland.protocol.ext_idle_notify_v1.ext_idle_notification_v1 import (
    ExtIdleNotificationV1Proxy as Notification
)
from pywayland.protocol.ext_idle_notify_v1.ext_idle_notifier_v1 import (
    ExtIdleNotifierV1, ExtIdleNotifierV1Proxy as Notifier
)
from src.services import hyprland
from src.services.upower import get_upower, BatteryState
from src.services.state import is_locked
from src.services.login1 import get_login_manager
from src.services.mpris import players
from config import Settings


WATCHER_XML_PATH = os.path.join(
    CONFIG_DIR, "assets", "dbus", "org.freedesktop.ScreenSaver.xml"
)
BUS_WATCHER = "org.freedesktop.ScreenSaver"
PATH_WATCHER = "/org/freedesktop/ScreenSaver"
with open(WATCHER_XML_PATH) as f:
    WATCHER_XML = f.read()

SETTINGS_KEYS = (
    "ac_lock", "ac_dpms", "ac_sleep",
    "battery_lock", "battery_dpms", "battery_sleep"
)


class ScreenSaver:
    def __init__(self) -> None:
        upower = get_upower()
        self._conn: gio.DBusConnection | None = None
        self.node_info = gio.DBusNodeInfo.new_for_xml(WATCHER_XML)
        self.ifaces = self.node_info.interfaces
        self.items: dict[int, tuple[str, str]] = {}
        self.next_id = 100
        self.last_battery_state = upower.state

        self.display = Display()
        self.display.connect()
        self.fd = self.display.get_fd()
        self.registry: WlRegistryProxy = self.display.get_registry()
        self.idle_notifier: Notifier | None = None
        self.seat: WlSeat | None = None
        self.notifications: list[Notification] = []
        self.notifier_set = False

        self.registry.dispatcher["global"] = self.global_handler
        self.display.dispatch()
        self.display.roundtrip()
        self.display.roundtrip()
        glib.io_add_watch(  # type: ignore
            self.fd, glib.IO_IN, self.on_event
        )

        get_upower().watch(
            "changed", self.update_on_battery
        )
        Settings()._signals.watch("changed", self.on_settings_changed)

    def on_settings_changed(self, key: str, value: str) -> None:
        if key in SETTINGS_KEYS:
            self.update_notifications()

    def on_event(self, *args: t.Any) -> bool:
        self.display.dispatch()
        self.display.roundtrip()
        return True

    def register(self) -> int:
        return gio.bus_own_name(
            gio.BusType.SESSION,
            BUS_WATCHER,
            gio.BusNameOwnerFlags.NONE,
            self.on_bus_acquired,
            None,
            lambda *_: logger.warning(
                "Another screen saver is running"
            )
        )

    def create_idle_notification(
        self,
        timeout: int,
        on_idle: t.Callable[[Notification], None],
        on_resume: t.Callable[[Notification], None] | None = None
    ) -> None:
        if timeout == 0:
            return
        if self.idle_notifier is None:
            logger.critical("IdleNotifier proxy is None")
            return
        timeout *= 1000
        notification: Notification = self.idle_notifier.get_idle_notification(
            timeout=timeout, seat=self.seat
        )
        self.notifications.append(notification)
        notification.dispatcher["idled"] = on_idle
        if on_resume is not None:
            notification.dispatcher["resumed"] = on_resume

    @property
    def is_inhibited(self) -> bool:
        login1 = get_login_manager()
        return login1.is_idle_inhibited() or bool(self.items)

    def dpms_off(self, *args: t.Any) -> None:
        if self.is_inhibited:
            return
        asyncio.create_task(hyprland.client.raw("dispatch dpms off"))

    def dpms_on(self, *args: t.Any) -> None:
        asyncio.create_task(hyprland.client.raw("dispatch dpms on"))

    def on_lock(self, *args: t.Any) -> None:
        if self.is_inhibited:
            return
        is_locked.value = True

    def on_sleep(self, *args: t.Any) -> None:
        login1 = get_login_manager()
        if login1.can_sleep() and not self.is_inhibited:
            for player in players.value.values():
                player.pause()
            login1.suspend()

    def update_on_battery(self, *args: t.Any) -> None:
        upower = get_upower()
        if self.last_battery_state != upower.state:
            self.update_notifications()
            self.last_battery_state = upower.state

    def update_notifications(self) -> None:
        if self.notifications:
            for notification in self.notifications:
                notification.destroy()
            self.notifications.clear()

        settings = Settings()
        upower = get_upower()

        if not upower.is_battery or upower.state != BatteryState.DISCHARGING:
            lock_timeout = settings.get("ac_lock")
            dpms_timeout = settings.get("ac_dpms")
            sleep_timeout = settings.get("ac_sleep")
        else:
            lock_timeout = settings.get("battery_lock")
            dpms_timeout = settings.get("battery_dpms")
            sleep_timeout = settings.get("battery_sleep")

        if lock_timeout > 0:
            self.create_idle_notification(
                lock_timeout,
                self.on_lock,
                self.dpms_on
            )
        if dpms_timeout > 0:
            self.create_idle_notification(
                lock_timeout + dpms_timeout,
                self.dpms_off,
                self.dpms_on
            )
        if sleep_timeout > 0:
            self.create_idle_notification(
                lock_timeout + dpms_timeout + sleep_timeout,
                self.on_sleep,
                self.dpms_on
            )

    def global_handler(
        self,
        registry: WlRegistryProxy,
        name: int,
        interface: str,
        version: int
    ) -> None:
        if interface == "wl_seat":
            self.seat = registry.bind(name, WlSeat, version)
        elif interface == "ext_idle_notifier_v1":
            self.idle_notifier = registry.bind(
                name, ExtIdleNotifierV1, version
            )

        if self.seat and self.idle_notifier and not self.notifier_set:
            self.update_notifications()
            self.notifier_set = True

    def on_bus_acquired(
        self, conn: gio.DBusConnection, name: str, user_data: object = None
    ) -> None:
        logger.debug("Screen saver bus acquired")
        self._conn = conn
        for interface in self.ifaces:
            if interface.name == name:
                logger.debug("Registering interface '%s'", name)
                conn.register_object(
                    PATH_WATCHER,
                    interface,
                    self.handle_bus_call
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
            case "Get":
                invocation.return_value(None)
            case "GetAll":
                invocation.return_value(glib.Variant("a{sv}", ()))
            case "Inhibit":
                cookie = self.inhibit(*params.unpack())
                invocation.return_value(glib.Variant("(u)", (cookie,)))
            case "UnInhibit":
                cookie = t.cast(int, params.unpack()[0])
                self.un_inhibit(cookie)
                invocation.return_value(None)

        return conn.flush()

    def un_inhibit(self, cookie: int) -> None:
        if cookie not in self.items.keys():
            return
        logger.debug(
            "ScreenSaver UnInhibit: App: '%s' Cookie: '%s'",
            self.items[cookie][0], cookie
        )
        del self.items[cookie]

    def inhibit(self, app_name: str, reason: str) -> int:
        cookie = self.next_id
        self.next_id += 1
        self.items[cookie] = (app_name, reason)
        logger.debug(
            "ScreenSaver Inhibit: App: '%s' Reason: '%s' Cookie: %s",
            app_name, reason, cookie
        )
        return cookie


class ScreenSaverService(Service):
    def __init__(self):
        self.watcher: ScreenSaver

    def app_init(self):
        self.watcher = ScreenSaver()

    def start(self) -> None:
        logger.debug("Starting screen saver dbus")
        self.watcher.register()

    def on_close(self):
        for notification in self.watcher.notifications:
            notification.destroy()
