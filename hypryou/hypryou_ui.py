#!/usr/bin/env python3

from __start__ import START
import atexit
import threading
from repository import gtk, gdk, gio, glib
import time
import typing as t
import logging
import signal
import traceback
import sys
import types

import utils.colors
from utils.styles import apply_css
from utils.logger import logger, setup_logger
from src.variables import Globals
from config import Settings, ASSETS_DIR, makedirs

from gi.events import GLibEventLoopPolicy  # type: ignore[import-untyped]
import asyncio
from utils.handler import set_fatal_handler, ExitSignals
from utils.handler import exit_error, exit_hung

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
from src.services.state import save_state, restore_state
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
from src.modules.bar import Bar, Corners
from src.modules.tray import TrayWindow
from src.modules.notifications.popups import Notifications
from src.modules.sidebar.window import SidebarWindow
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
from src.modules.emojis import EmojisWindow
from src.modules.keybinds import KeybindsWindow

from src.modules.settings.wallpapers import executor as wallpaper_executor

APP_START = time.perf_counter()
loop: glib.MainLoop

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
    SidebarWindow,
    AppsWindow,
    PlayersWindow,
    ClipHistoryWindow,
    PowerMenuWindow,
    BrightnessWindow,
    AudioWindow,
    MicsWindow,
    InfoWindow,
    ClientsWindow,
    EmojisWindow,
    KeybindsWindow
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
        self.corners: dict[gdk.Monitor, Corners] = {}
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
                exit_error()

    async def async_service_wrapper(self, service: AsyncService) -> None:
        try:
            await service.start()
        except Exception as e:
            logger.critical(
                "Service crashed on task: %s",
                type(service).__name__,
                exc_info=e
            )
            exit_error()

    def sync_service_wrapper(self, service: Service) -> None:
        try:
            service.start()
        except Exception as e:
            logger.critical(
                "Service crashed on task: %s",
                type(service).__name__,
                exc_info=e
            )
            exit_error()

    async def start_services(self) -> None:
        for service in services:
            if isinstance(service, AsyncService):
                self.tasks.append(
                    asyncio.create_task(self.async_service_wrapper(service))
                )
            elif isinstance(service, Service):
                glib.idle_add(self.sync_service_wrapper, service)
            else:
                logger.warning(
                    "Unknown type of service: %s; Couldn't start.",
                    service
                )

    async def start_app(self) -> None:
        await self.init_services()

        cache_ok = utils.colors.generate_by_settings()
        if cache_ok:
            apply_css()

        self.tasks: list[asyncio.Task[t.Any]] = []
        await self.start_services()

        self.display = gdk.Display.get_default()
        icon_theme = gtk.IconTheme.get_for_display(self.display)
        icon_theme.add_search_path(f"{ASSETS_DIR}/icons")

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
            f"{int((APP_START - START) * 1000)}ms + " +
            f"{int((time.perf_counter() - APP_START) * 1000)}ms"
        )
        self.release()
        glib.timeout_add(100, restore_state)
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
                    if __debug__:
                        logger.debug(
                            "Removing window: %s",
                            type(window).__name__
                        )
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
                self.corners[monitor].destroy_windows()
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
                self.windows[monitor] = windows
                self.corners[monitor] = Corners(self, monitor)


def init() -> None:
    setup_logger(logging.DEBUG if __debug__ else logging.INFO)
    if is_socket_exists():
        logger.critical(
            "Other HyprYou is running on the same hyprland instance!"
        )
        exit(1)

    set_fatal_handler(handle_fatal_signal)

    makedirs()
    settings = Settings()
    asyncio.set_event_loop_policy(GLibEventLoopPolicy())

    if settings.get("secure_cliphist"):
        cliphist.secure_clear()

    if __debug__:
        logger.debug("Initialized")


def main() -> None:
    global loop
    if __debug__:
        logger.debug("Starting app")
    loop = glib.MainLoop()
    start_watchdog(7.5)

    app = HyprYou(application_id="com.koeqaife.hypryou")
    app.run(None)


def watchdog(timeout: float) -> None:
    event = threading.Event()

    def ping() -> bool:
        event.set()
        return False

    while True:
        event.clear()
        glib.idle_add(ping, priority=glib.PRIORITY_HIGH)
        if not event.wait(timeout):
            logger.setLevel(logging.DEBUG)
            logger.critical(
                "Watchdog error: Loop did not response in time."
            )

            frames = sys._current_frames()
            for thread_id, frame in frames.items():
                logger.debug(
                    "Thread %s:\n%s",
                    thread_id,
                    "".join(traceback.format_stack(frame))
                )

            exit_hung()
            exit(1)
        time.sleep(timeout)


def start_watchdog(timeout: float = 5.0) -> threading.Thread:
    thread = threading.Thread(
        target=watchdog, args=(timeout,)
    )
    thread.daemon = True
    thread.start()
    return thread


def handle_fatal_signal(signum: int, frame: types.FrameType | None) -> None:
    logger.setLevel(logging.DEBUG)

    sigmap = {
        ExitSignals.SIGERROR: "SIGERROR",
        ExitSignals.SIGRELOAD: "SIGRELOAD",
        ExitSignals.SIGHUNG: "SIGHUNG",
    }
    if signum in sigmap:
        signame = sigmap[signum]
    else:
        signame = signal.Signals(signum).name
    logger.critical(
        f"Received fatal signal {signame} ({signum}), cleaning up..."
    )

    if signum == ExitSignals.SIGERROR or signum == ExitSignals.SIGHUNG:
        save_state()
    if signum != ExitSignals.SIGRELOAD and frame is not None:
        stack_str = ''.join(traceback.format_stack(frame))
        logger.debug("Stack at signal:\n%s", stack_str)

    cleanup()

    signal.signal(signum, signal.SIG_DFL)
    signal.raise_signal(signum)

    # To exit if SIG_DFL didn't kill the process
    time.sleep(0.1)
    exit(1)


def cleanup() -> None:
    for executor in (utils.colors.executor, wallpaper_executor):
        try:
            if executor:
                if hasattr(executor, "_processes") and executor._processes:
                    for p in executor._processes.values():
                        p.kill()

                executor.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            logger.exception("Error while stopping executor", exc_info=e)
    if Settings().get("secure_cliphist"):
        cliphist.secure_clear()
    for service in services:
        try:
            service.on_close()
        except Exception as e:
            logger.exception(
                "Error while stopping service %s",
                type(service).__name__, exc_info=e
            )
    logger.warning("Bye!")


atexit.register(cleanup)


if __name__ == "__main__":
    init()
    main()
