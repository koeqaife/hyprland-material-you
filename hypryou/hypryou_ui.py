#!/usr/bin/env python3

from repository import gtk, gdk, gio, glib
import time
import typing as t
import logging
import os

import utils
from utils.logger import logger
from src.variables import Globals
from config import Settings, CONFIG_DIR

from gi.events import GLibEventLoopPolicy  # type: ignore[import-untyped]
import asyncio

# Services
from utils.service import AsyncService, Service

from src.services.dbus import DBusService
from src.services.hyprland import HyprlandService
from src.services.mpris import MprisService
from src.services.system_tray import TrayService
from src.services.cli import CliService, is_socket_exists
from src.services.notifications import NotificationsService
from src.services.idle_inhibitor import IdleInhibitorService
from src.services.apps import AppsService
from src.services.hyprland_config import HyprlandConfigService
from src.services.state import StateService
from src.services.upower import UPowerService
from src.services.idle import ScreenSaverService
from src.services.login1 import Login1ManagerService
from src.services.backlight import BacklightService
from src.services.audio import AudioService
from src.services.clock import ClockService
from src.services.network import NetworkService
from src.services.bluetooth_agent import BluetoothAgentService

import src.services.cliphist as cliphist

# Modules
from src.modules.bar import Bar, Corner
from src.modules.tray import TrayWindow
from src.modules.notifications.popups import Notifications
from src.modules.sidebar.window import Sidebar
from src.modules.apps_menu import AppsWindow
from src.modules.players import PlayersWindow
from src.modules.cliphist import ClipHistoryWindow
from src.modules.wallpapers import WallpapersWindow
from src.modules.lockscreen import ScreenLock
from src.modules.power import PowerMenuWindow
from src.modules.brightness import BrightnessWindow
from src.modules.popups import PopupsWindow
from src.modules.audio import AudioWindow
from src.modules.audio import MicsWindow
from src.modules.info import InfoWindow
from src.modules.clients import ClientsWindow
from src.modules.settings.window import SettingsWatcher
from src.modules.wifi_secrets import SecretsDialog
from src.modules.bluetooth_pin import PinDialog

START = time.perf_counter()

services: tuple[AsyncService | Service, ...] = (
    StateService(),
    DBusService(),
    NetworkService(),
    HyprlandService(),
    HyprlandConfigService(),
    NotificationsService(),
    TrayService(),
    MprisService(),
    CliService(),
    AppsService(),
    UPowerService(),
    Login1ManagerService(),
    ScreenSaverService(),
    IdleInhibitorService(),
    BacklightService(),
    AudioService(),
    ClockService(),
    BluetoothAgentService()
)

popups_types = (
    TrayWindow,
    Sidebar,
    AppsWindow,
    PlayersWindow,
    ClipHistoryWindow,
    PowerMenuWindow,
    BrightnessWindow,
    AudioWindow,
    MicsWindow,
    InfoWindow,
    ClientsWindow
)

windows_types = (
    Bar,
    Notifications,
    WallpapersWindow,
    PopupsWindow,
)

type RegisterType = t.Callable[["HyprYou"], type[t.Any] | object]
module_register_types: dict[str, RegisterType] = {
    "wifi_secrets": SecretsDialog.register,
    "screen_lock": ScreenLock.register,
    "settings_watcher": SettingsWatcher.register,
    "bluetooth_pin": PinDialog.register
}


class HyprYou(gtk.Application):
    __gtype_name__ = "HyprYou"

    def do_activate(self) -> None:
        self.windows: dict[gdk.Monitor, list[gtk.ApplicationWindow]] = {}
        self.corners: dict[gdk.Monitor, list[Corner]] = {}
        self.registered: dict[str, t.Any] = {}

        self.hold()
        asyncio.create_task(self.start_app())
        Globals.app = self

    async def init_services(self) -> None:
        for service in services:
            try:
                if __debug__:
                    logger.debug(
                        "Starting service %s",
                        type(service).__name__
                    )
                if isinstance(service, AsyncService):
                    await service.app_init()
                elif isinstance(service, Service):
                    service.app_init()
                else:
                    logger.error(
                        "Unknown type of service: %s; Couldn't init.",
                        service
                    )
            except Exception as e:
                logger.critical(
                    "Couldn't initialize service %s.",
                    type(service).__name__, exc_info=e
                )
                exit(1)

    async def start_services(self) -> None:
        for service in services:
            if isinstance(service, AsyncService):
                self.tasks.append(asyncio.create_task(service.start()))
            elif isinstance(service, Service):
                glib.idle_add(service.start)
            else:
                logger.warning(
                    "Unknown type of service: %s; Couldn't start.",
                    service
                )

    async def start_app(self) -> None:
        await self.init_services()

        try:
            colors = utils.colors.sync()
            if colors is not None:
                if colors.wallpaper == Settings().get("wallpaper"):
                    utils.apply_css()
                else:
                    if __debug__:
                        logger.debug(
                            "Settings wallpaper and " +
                            "colors wallpaper are different. " +
                            "Generating new colors."
                        )
                    utils.colors.generate_by_last_wallpaper()
            else:
                raise ValueError
        except Exception:
            utils.colors.generate_by_last_wallpaper()

        self.tasks: list[asyncio.Task[t.Any]] = []
        await self.start_services()

        self.display: gdk.Display = gdk.Display.get_default()
        self.monitors = self.display.get_monitors()
        self.monitors.connect("items-changed", self.update_monitors)

        self.update_monitors()
        for window_type in popups_types:
            try:
                if __debug__:
                    logger.debug(
                        "Creating window %s",
                        window_type.__name__
                    )
                self.add_window(window_type(self))
            except Exception as e:
                logger.error(
                    "Couldn't add window %s.",
                    window_type.__name__, exc_info=e
                )

        for key, register_method in module_register_types.items():
            returned = register_method(self)
            self.registered[key] = returned

        logger.info(
            "Started in " +
            f"{round((time.perf_counter() - START) * 1000)}" +
            "ms"
        )
        self.release()
        await asyncio.gather(*self.tasks)

    def get_monitors(self) -> gio.ListModel:
        monitors = self.display.get_monitors()
        return monitors

    def update_monitors(self, *_: t.Any) -> None:
        monitors = self.get_monitors()

        for monitor in list(self.windows.keys()):
            if monitor not in monitors:
                if __debug__:
                    logger.debug(
                        "Removing windows for monitor: %s",
                        monitor.get_model()
                    )
                for window in self.windows[monitor]:
                    window.destroy()
                self.windows[monitor].clear()
                del self.windows[monitor]

        for monitor in list(self.corners.keys()):
            if monitor not in monitors:
                if __debug__:
                    logger.debug(
                        "Removing corners for monitor: %s",
                        monitor.get_model()
                    )
                for corner in self.corners[monitor]:
                    corner.destroy_window()
                self.corners[monitor].clear()
                del self.corners[monitor]

        for i, monitor in enumerate(list(monitors)):  # type: ignore[assignment]  # noqa
            if monitor not in self.windows:
                if __debug__:
                    logger.debug(
                        "Adding windows for monitor: %s",
                        monitor.get_model()
                    )
                windows: list[gtk.ApplicationWindow] = []
                for window_type in windows_types:
                    try:
                        windows.append(window_type(self, monitor, i))
                    except Exception as e:
                        logger.error(
                            "Couldn't add window %s.",
                            window_type.__name__, exc_info=e
                        )
                corners = [
                    Corner(self, monitor, "left"),
                    Corner(self, monitor, "right")
                ]
                self.windows[monitor] = windows
                self.corners[monitor] = corners
                windows[0].present()


def init() -> None:
    utils.setup_logger(logging.DEBUG if __debug__ else logging.INFO)
    if is_socket_exists():
        logger.critical(
            "Other HyprYou is running on the same hyprland instance!"
        )
        exit(1)

    os.nice(5)
    settings = Settings()
    asyncio.set_event_loop_policy(GLibEventLoopPolicy())
    display = gdk.Display.get_default()
    icon_theme = gtk.IconTheme.get_for_display(display)
    icon_theme.add_search_path(f"{CONFIG_DIR}/assets/icons")

    if settings.get("secure_cliphist"):
        cliphist.secure_clear()

    if __debug__:
        logger.debug("Initialized")


def main() -> None:
    if __debug__:
        logger.debug("Starting app")
    app = HyprYou(application_id="com.koeqaife.hypryou")
    app.run(None)


if __name__ == "__main__":
    try:
        init()
        main()
    except KeyboardInterrupt:
        logger.warning("Bye!")
        exit(0)
    finally:
        if Settings().get("secure_cliphist"):
            cliphist.secure_clear()
        for service in services:
            service.on_close()
