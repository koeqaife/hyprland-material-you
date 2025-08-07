from __start__ import START
import json
import struct
import os
import asyncio
from repository import gtk, layer_shell, gdk, glib, gio, gobject
from utils.styles import toggle_css_class
from utils.logger import logger, setup_logger
from gi.events import GLibEventLoopPolicy  # type: ignore[import-untyped]
import logging
import typing as t
from utils.service import Service, AsyncService
from config import ASSETS_DIR, Settings, get_version, HOME
import time
from enum import IntEnum
import src.widget as widget

# Minimum services
from src.services.dbus import DBusService
from src.services.hyprland import HyprlandService
from src.services.upower import UPowerService, get_upower, lid_is_closed
from src.services.idle import ScreenSaverService
from src.services.clock import ClockService
from src.services.login1 import Login1ManagerService

from src.services.clock import time as time_str, full_date
import src.services.hyprland as hyprland

# It's like hypryou_ui.py but minimum version of it
# I like it

# I don't wanna put anything in other files so everything is here
# It's only one window so I don't think it needs any structure

APP_START = time.perf_counter()
STYLES = os.path.join(ASSETS_DIR, "greeter", "main.css")
SESSION_DIRS = [
    "/usr/share/xsessions",
    "/usr/share/wayland-sessions"
]
LAST_SESSION_PATH = os.path.join(HOME, ".last-session.json")


services: tuple[Service | AsyncService, ...] = (
    DBusService(),
    HyprlandService(),
    Login1ManagerService(),
    UPowerService(),
    ScreenSaverService(),
    ClockService(),
)


class State(IntEnum):
    IDLE = 0
    WAITING_FOR_PASSWORD = 1
    ERROR = 2
    SUCCESS = 3


class SessionDict(t.TypedDict):
    name: str
    exec: str


def get_sessions() -> list[SessionDict]:
    sessions = []
    for path in SESSION_DIRS:
        if not os.path.exists(path):
            continue
        for file in os.listdir(path):
            if not file.endswith(".desktop"):
                continue
            full_path = os.path.join(path, file)
            keyfile = glib.KeyFile()
            keyfile.load_from_file(full_path, glib.KeyFileFlags.NONE)
            name = keyfile.get_string("Desktop Entry", "Name")
            exec_cmd = keyfile.get_string("Desktop Entry", "Exec")
            sessions.append({"name": name, "exec": exec_cmd})
    return t.cast(list[SessionDict], sessions)


def on_lid_closed(is_closed: bool) -> None:
    asyncio.create_task(
        hyprland.client.raw(f"dispatch dpms {"off" if is_closed else "on"}")
    )


class Greetd:
    def __init__(self) -> None:
        socket_path = os.getenv("GREETD_SOCK")
        if socket_path is None:
            raise RuntimeError("Couldn't get socket path")
        self.socket_path = socket_path

    @staticmethod
    def build_message(payload: dict[str, t.Any]) -> bytes:
        json_bytes = json.dumps(payload).encode('utf-8')
        length_prefix = struct.pack('@I', len(json_bytes))
        return length_prefix + json_bytes

    @staticmethod
    async def read_message(reader: asyncio.StreamReader) -> dict[str, t.Any]:
        length_bytes = await reader.readexactly(4)
        length, = struct.unpack('@I', length_bytes)
        payload = await reader.readexactly(length)
        return dict(json.loads(payload.decode('utf-8')))

    async def raw(self, payload: dict[str, t.Any]) -> dict[str, t.Any]:
        try:
            reader, writer = await asyncio.open_unix_connection(
                self.socket_path
            )
            writer.write(self.build_message(payload))
            await writer.drain()

            msg = await self.read_message(reader)
            return msg
        finally:
            writer.close()
            await writer.wait_closed()

    async def create_session(self, username: str) -> dict[str, t.Any]:
        payload = {
            "type": "create_session",
            "username": username
        }
        return await self.raw(payload)

    async def cancel_session(self) -> dict[str, t.Any]:
        payload = {
            "type": "cancel_session"
        }
        return await self.raw(payload)

    async def post_auth_message_response(
        self, response: str | None = None
    ) -> dict[str, t.Any]:
        payload = {
            "type": "post_auth_message_response"
        }
        if response is not None:
            payload["response"] = response
        return await self.raw(payload)

    async def start_session(
        self, cmd: list[str], env: list[str]
    ) -> dict[str, t.Any]:
        payload = {
            "type": "start_session",
            "cmd": cmd,
            "env": env
        }
        return await self.raw(payload)


class SessionItem(gobject.Object):
    def __init__(
        self,
        exec: t.Any,
        label: str
    ) -> None:
        super().__init__()
        self.label = label
        self.exec = exec


class GreeterUI(gtk.ApplicationWindow):
    def __init__(
        self,
        app: "HyprYouGreeter",
        monitor: gdk.Monitor
    ) -> None:
        self.greetd = Greetd()
        self.app = app
        self.overlay = gtk.Overlay(
            hexpand=True,
            vexpand=True
        )
        super().__init__(
            application=app,
            css_classes=("hypryou-greeter",),
            child=self.overlay
        )

        # Stack
        self.stack = gtk.Stack(
            transition_type=gtk.StackTransitionType.CROSSFADE,
            transition_duration=250
        )

        # Username box
        self.username_box = gtk.Box(
            css_classes=("username-box",),
            halign=gtk.Align.CENTER,
            valign=gtk.Align.CENTER,
            orientation=gtk.Orientation.VERTICAL
        )
        self.username = gtk.Label(
            label="Username:",
            css_classes=("username-label",),
            halign=gtk.Align.START
        )
        self.error = gtk.Label(
            label="ERRORR HAHAHAHAH",
            css_classes=("error",),
            halign=gtk.Align.START,
            visible=False
        )
        self.username_entry = gtk.Entry(
            placeholder_text="Type here...",
        )
        self.username_entry.connect("activate", self.on_start_session)
        self.username_entry.connect("notify::text", self.on_username_entry)
        self.continue_button = gtk.Button(
            css_classes=("continue", "in-dialog"),
            label="Continue",
            halign=gtk.Align.END,
            valign=gtk.Align.START
        )
        self.continue_button.connect("clicked", self.on_start_session)
        self.username_box.append(self.username)
        self.username_box.append(self.username_entry)
        self.username_box.append(self.error)
        self.username_box.append(self.continue_button)

        # Auth box
        self.auth_box = gtk.Box(
            css_classes=("auth-box",),
            halign=gtk.Align.CENTER,
            valign=gtk.Align.CENTER,
            orientation=gtk.Orientation.VERTICAL
        )
        self.auth_message = gtk.Label(
            label="Yee",
            css_classes=("auth-message",),
            halign=gtk.Align.START
        )
        self.auth_error = gtk.Label(
            label="",
            css_classes=("auth-error",),
            halign=gtk.Align.START,
            visible=False
        )
        self.auth_entry = gtk.Entry(
            placeholder_text="Type here...",
        )
        self.auth_entry.connect("activate", self.on_auth_continue)
        self.auth_entry.connect("notify::text", self.on_auth_entry)
        self.actions_box = gtk.Box(
            css_classes=("actions-box",),
            halign=gtk.Align.END,
            valign=gtk.Align.START
        )
        self.auth_cancel_button = gtk.Button(
            css_classes=("cancel", "in-dialog"),
            label="Cancel"
        )
        self.auth_cancel_button.connect("clicked", self.on_cancel_session)
        self.auth_continue_button = gtk.Button(
            css_classes=("continue", "in-dialog"),
            label="Continue"
        )
        self.auth_continue_button.connect("clicked", self.on_auth_continue)
        self.auth_box.append(self.auth_message)
        self.auth_box.append(self.auth_entry)
        self.auth_box.append(self.auth_error)
        self.auth_box.append(self.actions_box)
        self.actions_box.append(self.auth_cancel_button)
        self.actions_box.append(self.auth_continue_button)

        # Date box
        self.time = gtk.Label(
            label=time_str.value,
            css_classes=("time",),
            valign=gtk.Align.END
        )
        self.date = gtk.Label(
            label=full_date.value,
            css_classes=("date",),
            valign=gtk.Align.END
        )
        self.date_box = gtk.Box(
            css_classes=("date-box",),
            halign=gtk.Align.CENTER,
            valign=gtk.Align.START,
            orientation=gtk.Orientation.VERTICAL
        )
        self.date_box.append(self.time)
        self.date_box.append(self.date)
        time_str.watch(self.on_time)
        full_date.watch(self.on_date)

        # Info label
        self.info_label = gtk.Label(
            halign=gtk.Align.END,
            valign=gtk.Align.START,
            label=f"HyprYou v{get_version()}",
            css_classes=("info-label",)
        )

        # Battery box
        self.battery_box = gtk.Box(
            css_classes=("battery-box",),
            visible=False,
            halign=gtk.Align.START,
            valign=gtk.Align.START
        )
        self.battery_icon = widget.Icon(
            get_upower().battery_icon,
            css_classes=("battery-icon",)
        )
        self.battery = gtk.Label(
            css_classes=("battery-label",),
            label="0%"
        )
        self.battery_box.append(self.battery_icon)
        self.battery_box.append(self.battery)

        # Sessions
        self.current_session = ""
        self.current_exec = ""
        self.items = gio.ListStore.new(SessionItem)
        for session in get_sessions():
            self.items.append(
                SessionItem(
                    exec=session["exec"],
                    label=session["name"]
                )
            )

        self.factory = gtk.SignalListItemFactory()
        self.factory_handlers = (
            self.factory.connect("setup", self.on_setup),
            self.factory.connect("bind", self.on_bind)
        )

        self.dropdown = gtk.DropDown(
            model=self.items,
            factory=self.factory,
            halign=gtk.Align.START,
            valign=gtk.Align.END,
            css_classes=("sessions",)
        )

        self.dropdown_handler = self.dropdown.connect(
            "notify::selected",
            self.on_item_selected
        )

        self.stack.add_named(self.username_box, "username")
        self.stack.add_named(self.auth_box, "auth")
        self.stack.set_visible_child_name("username")
        self.username_entry.grab_focus_without_selecting()

        self.overlay.add_overlay(self.stack)
        self.overlay.add_overlay(self.date_box)
        self.overlay.add_overlay(self.info_label)
        self.overlay.add_overlay(self.battery_box)
        self.overlay.add_overlay(self.dropdown)

        get_upower().watch(
            "changed", self.update_battery
        )
        self.update_battery()
        self.on_username_entry()

        layer_shell.init_for_window(self)
        layer_shell.set_anchor(self, layer_shell.Edge.TOP, True)
        layer_shell.set_anchor(self, layer_shell.Edge.BOTTOM, True)
        layer_shell.set_anchor(self, layer_shell.Edge.LEFT, True)
        layer_shell.set_anchor(self, layer_shell.Edge.RIGHT, True)
        layer_shell.set_keyboard_mode(self, layer_shell.KeyboardMode.ON_DEMAND)
        layer_shell.set_monitor(self, monitor)

        try:
            with open(LAST_SESSION_PATH, "r") as f:
                data: dict[str, str] = json.load(f)
            if "session" in data.keys():
                model = self.dropdown.get_model()
                if model is None:
                    return
                for i in range(model.get_n_items()):
                    item = t.cast(SessionItem, model.get_item(i))
                    if item.label == data["session"]:
                        self.dropdown.set_selected(i)
                        break
            if "username" in data.keys():
                self.username_entry.set_text(data["username"])
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    def set_error(self, error: str | None) -> None:
        # I don't really understand how greetd works
        # And I'm a little bit lazy
        # So I'mma set error message in both pages
        is_error = error is not None
        toggle_css_class(self.username_entry, "incorrect", is_error)
        toggle_css_class(self.auth_entry, "incorrect", is_error)
        self.error.set_visible(is_error)
        self.auth_error.set_visible(is_error)
        if error is not None:
            self.error.set_label(error)
            self.auth_error.set_label(error)

    async def _handler(self, response: dict[str, t.Any]) -> None:
        if response["type"] == "success":
            return await self.on_success()
        elif response["type"] == "error":
            self.set_error(response["description"])
        if response["type"] == "auth_message":
            return await self.on_auth_message(response)

    async def on_success(self) -> None:
        import shlex

        async def task() -> None:
            cmd = shlex.split(self.current_exec)
            response = await self.greetd.start_session(cmd, [])
            if response["type"] == "success":
                try:
                    with open(LAST_SESSION_PATH, "w") as f:
                        payload = {
                            "username": self.username_entry.get_text(),
                            "session": self.current_session
                        }
                        json.dump(payload, f)
                except Exception as e:
                    logger.exception(
                        "Error while saving json file", exc_info=e
                    )
                exit(1)
            else:
                await self._handler(response)

        asyncio.create_task(task())

    async def on_auth_message(self, r: dict[str, t.Any]) -> None:
        self.stack.set_sensitive(False)
        try:
            match r["auth_message_type"]:
                case "visible":
                    self.auth_entry.set_visibility(True)
                case "secret":
                    self.auth_entry.set_visibility(False)
                case _:
                    return await self._handler(
                        await self.greetd.post_auth_message_response()
                    )
            self.auth_message.set_label(r["auth_message"])
            self.stack.set_visible_child_name("auth")
            self.auth_entry.grab_focus_without_selecting()
            self.auth_entry.set_text("")
        finally:
            self.stack.set_sensitive(True)

    def on_username_entry(self, *args: t.Any) -> None:
        self.set_error(None)
        self.continue_button.set_sensitive(
            len(self.username_entry.get_text().strip()) > 0
        )

    def on_auth_entry(self, *args: t.Any) -> None:
        self.set_error(None)
        self.continue_button.set_sensitive(
            len(self.username_entry.get_text().strip()) > 0
        )

    def on_start_session(self, *args: t.Any) -> None:
        async def task() -> None:
            self.stack.set_sensitive(False)
            try:
                return await self._handler(
                    await self.greetd.create_session(
                        self.username_entry.get_text()
                    )
                )
            finally:
                self.stack.set_sensitive(True)
        asyncio.create_task(task())

    def on_cancel_session(self, *args: t.Any) -> None:
        async def task() -> None:
            self.stack.set_sensitive(False)
            await self.greetd.cancel_session()
            self.set_error(None)
            self.stack.set_visible_child_name("username")
            self.username_entry.grab_focus_without_selecting()
            self.stack.set_sensitive(True)
        asyncio.create_task(task())

    def on_auth_continue(self, *args: t.Any) -> None:
        async def task() -> None:
            self.stack.set_sensitive(False)
            try:
                return await self._handler(
                    await self.greetd.post_auth_message_response(
                        self.auth_entry.get_text()
                    )
                )
            finally:
                self.stack.set_sensitive(True)
        asyncio.create_task(task())

    def on_time(self, value: str) -> None:
        self.time.set_label(value)

    def on_date(self, value: str) -> None:
        self.date.set_label(value)

    def update_battery(self, *args: t.Any) -> None:
        upower = get_upower()

        is_battery_connected = upower.is_battery and upower.is_present
        if not is_battery_connected:
            self.battery_box.set_visible(False)
            return
        else:
            self.battery_box.set_visible(True)

        self.battery.set_label(f"{round(upower.percentage)}%")

    def on_setup(
        self,
        factory: gtk.SignalListItemFactory,
        list_item: gtk.ListItem
    ) -> None:
        label = gtk.Label(xalign=0)
        list_item.set_child(label)

    def on_bind(
        self,
        factory: gtk.SignalListItemFactory,
        list_item: gtk.ListItem
    ) -> None:
        item = t.cast(SessionItem, list_item.get_item())
        label = t.cast(gtk.Label, list_item.get_child())
        label.set_text(item.label)

    def on_item_selected(self, *args: t.Any) -> None:
        item = t.cast(SessionItem, self.dropdown.get_selected_item())
        self.current_exec = item.exec
        self.current_session = item.label


class HyprYouGreeter(gtk.Application):
    __gtype_name__ = "HyprYouGreeter"

    def do_activate(self) -> None:
        provider = gtk.CssProvider()
        gtk.StyleContext.add_provider_for_display(
            gdk.Display.get_default(),
            provider,
            gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        provider.load_from_path(STYLES)
        self.hold()
        asyncio.create_task(self.start_app())

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

    async def async_service_wrapper(self, service: AsyncService) -> None:
        try:
            await service.start()
        except Exception as e:
            logger.critical(
                "Service crashed on task: %s",
                type(service).__name__,
                exc_info=e
            )
            exit(1)

    def sync_service_wrapper(self, service: Service) -> None:
        try:
            service.start()
        except Exception as e:
            logger.critical(
                "Service crashed on task: %s",
                type(service).__name__,
                exc_info=e
            )
            exit(1)

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

    def get_monitors(self) -> gio.ListModel:
        display = gdk.Display.get_default()
        monitors = display.get_monitors()
        return monitors

    async def start_app(self) -> None:
        await self.init_services()

        self.tasks: list[asyncio.Task[t.Any]] = []
        await self.start_services()

        monitors = self.get_monitors()
        for i, monitor in enumerate(list(monitors)):
            greeter = GreeterUI(self, t.cast(gdk.Monitor, monitor))
            greeter.present()

        lid_is_closed.watch(on_lid_closed)

        logger.info(
            "Started in " +
            f"{int((APP_START - START) * 1000)}ms + " +
            f"{int((time.perf_counter() - APP_START) * 1000)}ms"
        )
        self.release()
        await asyncio.gather(*self.tasks)


def init() -> None:
    setup_logger(logging.DEBUG if __debug__ else logging.INFO)

    asyncio.set_event_loop_policy(GLibEventLoopPolicy())
    settings = Settings()
    settings.mutable = False
    if __debug__:
        logger.debug("Initialized")


def main() -> None:
    if __debug__:
        logger.debug("Starting app")
    app = HyprYouGreeter(
        application_id="com.koeqaife.hypryou.greeter"
    )
    app.run(None)


if __name__ == "__main__":
    init()
    main()
