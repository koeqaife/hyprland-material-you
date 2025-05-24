#!/usr/bin/env python3

from repository import gtk, gdk, gio, glib
import time
import typing as t
import logging

import utils
from utils.logger import logger
from src.variables.clock import clock_task
from src.variables import Globals
from config import Settings, DEBUG

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

from src.services import events

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

START = time.perf_counter()

services: tuple[AsyncService | Service, ...] = (
    StateService(),
    DBusService(),
    HyprlandService(),
    HyprlandConfigService(),
    NotificationsService(),
    TrayService(),
    MprisService(),
    CliService(),
    AppsService(),
    IdleInhibitorService(),
)


class HyprYou(gtk.Application):
    def do_activate(self) -> None:
        self.windows: dict[gdk.Monitor, list[gtk.ApplicationWindow]] = {}
        self.corners: dict[gdk.Monitor, list[Corner]] = {}

        self.hold()
        asyncio.create_task(self.start_app())

    async def init_services(self) -> None:
        for service in services:
            if isinstance(service, AsyncService):
                await service.app_init()
            elif isinstance(service, Service):
                service.app_init()
            else:
                logger.critical(
                    "Unknown type of service: %s; Couldn't init.",
                    service
                )

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
            utils.colors.sync()
            utils.apply_css()
        except Exception:
            utils.colors.restore_palette()

        self.tasks = [
            asyncio.create_task(clock_task())
        ]
        await self.start_services()

        self.display: gdk.Display = gdk.Display.get_default()
        self.monitors = self.display.get_monitors()
        self.monitors.connect("items-changed", self.update_monitors)

        self.update_monitors()
        self.add_window(TrayWindow(self))
        self.add_window(Sidebar(self))
        self.add_window(AppsWindow(self))
        self.add_window(PlayersWindow(self))
        self.add_window(ClipHistoryWindow(self))
        self.screen_lock = ScreenLock(self)

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
                logger.debug(
                    "Adding windows for monitor: %s",
                    monitor.get_model()
                )
                windows: list[gtk.ApplicationWindow] = [
                    Bar(self, monitor, i),
                    Notifications(self, monitor, i),
                    WallpapersWindow(self, monitor)
                ]
                corners = [
                    Corner(self, monitor, "left"),
                    Corner(self, monitor, "right")
                ]
                self.windows[monitor] = windows
                self.corners[monitor] = corners
                windows[0].present()


def init() -> None:
    utils.setup_logger(logging.DEBUG if DEBUG else logging.INFO)
    if is_socket_exists():
        logger.critical(
            "Other HyprYou is running on the same hyprland instance!"
        )
        exit(1)

    Globals.events = events.EventsBus()
    Settings()
    asyncio.set_event_loop_policy(GLibEventLoopPolicy())
    logger.debug("Initialized")


def main() -> None:
    logger.debug("Starting app")
    app = HyprYou(application_id="com.koeqaife.hypryou")

    app.run(None)
    Globals.app = app


if __name__ == "__main__":
    try:
        init()
        main()
    except KeyboardInterrupt:
        logger.warning("Bye!")
        exit(0)
    finally:
        for service in services:
            service.on_close()
