#!/usr/bin/env python3

from repository import gtk, gdk, gio
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
from src.services import dbus
from src.services import hyprland
from src.services import mpris
from src.services import system_tray
from src.services import cli
from src.services import events
from src.services import notifications
from src.services import network

# Modules
from src.modules.bar import Bar, Corner
from src.modules.tray import TrayWindow
from src.modules.notifications.popups import Notifications
from src.modules.sidebar.window import Sidebar

START = time.perf_counter()

dbus_services = (
    dbus.Service, system_tray.Service,
    mpris.Service, notifications.Service
)


class HyprYou(gtk.Application):
    def do_activate(self) -> None:
        self.windows: dict[gdk.Monitor, list[gtk.ApplicationWindow]] = {}
        self.corners: dict[gdk.Monitor, list[Corner]] = {}

        self.hold()
        asyncio.create_task(self.start_app())

    async def start_app(self) -> None:
        await hyprland.init()
        network.get_network()

        try:
            utils.apply_css()
        except Exception:
            utils.colors.restore_palette()

        for service in dbus_services:
            service().start()

        self.tasks = [
            asyncio.create_task(cli.serve()),
            asyncio.create_task(hyprland.connect()),
            asyncio.create_task(clock_task())
        ]

        self.display: gdk.Display = gdk.Display.get_default()
        self.monitors = self.display.get_monitors()
        self.monitors.connect("items-changed", self.update_monitors)

        self.update_monitors()
        self.add_window(TrayWindow(self))
        self.add_window(Sidebar(self))

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
                    Bar(self, monitor),
                    Notifications(self, monitor, i)
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
    if cli.is_socket_exists():
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
