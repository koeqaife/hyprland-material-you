from __future__ import annotations

import signal
import os
from repository import gio, glib, gtk, gdk_pixbuf
from config import CONFIG_DIR
from utils.logger import logger
from src.services.dbus import BUS_TYPE, dbus_proxy, cache_proxy_properties
from src.services.dbus import ServiceABC
from src.services.events import NameOwnerChanged
from src.variables import Globals
import typing as t
from utils import Ref
from utils.service import Signals

# it won't reproduce the all possibilities of tray
# I'll just use it as for running background services
# but without any menus
# only actions like activate, secondary activate and quit


WATCHER_XML_PATH = os.path.join(
    CONFIG_DIR, "assets", "dbus", "org.kde.StatusNotifierWatcher.xml"
)
BUS_WATCHER = "org.kde.StatusNotifierWatcher"
PATH_WATCHER = "/StatusNotifierWatcher"
with open(WATCHER_XML_PATH) as f:
    WATCHER_XML = f.read()

ITEM_XML_PATH = os.path.join(
    CONFIG_DIR, "assets", "dbus", "org.kde.StatusNotifierItem.xml"
)
BUS_ITEM = "org.kde.StatusNotifierItem"
PATH_ITEM = "/StatusNotifierItem"
with open(ITEM_XML_PATH) as f:
    ITEM_XML = f.read()


items = Ref[dict[str, "StatusNotifierItem"]]({}, name="tray_items")


type Status = t.Literal["Passive", "Active", "NeedsAttention"]
type Category = t.Literal[
    "ApplicationStatus", "Communications",
    "SystemServices", "Hardware"
]
type Pixmaps = list[tuple[int, int, bytearray]]


def get_process_title(pid: int) -> str | None:
    try:
        with open(f"/proc/{pid}/comm", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def get_pid(bus_name: str) -> int:
    result = dbus_proxy.call_sync(
        "GetConnectionUnixProcessID",
        glib.Variant("(s)", (bus_name,)),
        gio.DBusCallFlags.NONE,
        -1,
        None
    )

    pid: int = result.unpack()[0]
    return pid


class StatusNotifierItem(Signals):
    def __init__(
        self,
        proxy: gio.DBusProxy
    ) -> None:
        super().__init__()
        self._proxy = proxy
        self._conn = proxy.get_connection()
        self._bus_name = self.get_bus_name()
        self._bus_path = proxy.get_object_path()
        self.identifier = self._bus_name + self._bus_path
        self._icon_theme: gtk.IconTheme | None = None
        self._cached_name: str | None = None
        self._pixbufs: dict[tuple[int, int], gdk_pixbuf.Pixbuf] = {}

        self.conns = [
            self._proxy.connect(
                "g-signal", self.on_dbus_signal
            ),
            self._proxy.connect(
                "g-properties-changed", self.properties_changed
            )
        ]

        self._cache_proxy_properties()

    def get_bus_name(self) -> str:
        bus_name = self._proxy.get_name()
        if bus_name is None:
            raise RuntimeError("Proxy bus name is None.")
        else:
            self._bus_name = bus_name
        return bus_name

    def finalize(self) -> None:
        # Removes all links so item will be removed by GC
        # Tested with weakref.finalize
        for conn in self.conns:
            self._proxy.disconnect(conn)
        self._proxy = None  # type: ignore

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
        if (
            "ToolTip" in changed_properties
            or "Title" in changed_properties
        ):
            self._cached_name = None
        if "Icon" in changed_properties:
            self._pixbufs.clear()
        self._cache_proxy_properties(list(changed_properties.keys()))

        self.notify("changed")

    def on_dbus_signal(
        self,
        proxy: gio.DBusProxy,
        bus_name: str,
        signal_name: str,
        signal_args: tuple[str, ...]
    ) -> None:
        if not signal_name.startswith("New"):
            return
        prop = signal_name.lstrip("New")

        if prop == "Icon":
            self._pixbufs.clear()
            self._cache_proxy_properties(
                ["IconName", "IconPixmap"]
            )
        elif prop == "Title" or prop == "ToolTip":
            self._cached_name = None
            self._cache_proxy_properties([prop])
        else:
            self._cache_proxy_properties([prop])
        self.notify(
            "changed",
            {
                "signal": signal_name,
                "prop": prop.lower()
            }
        )

    def prop(self, property_name: str) -> t.Any:
        value = self._proxy.get_cached_property(property_name)
        if value is None:
            return None
        return value.unpack()

    @property
    def id(self) -> int:
        return t.cast(int, self.prop("Id"))

    @property
    def window_id(self) -> int:
        return t.cast(int, self.prop("WindowId"))

    @property
    def tooltip(self) -> str:
        return t.cast(str, self.prop("ToolTip"))

    @property
    def title(self) -> str:
        return t.cast(str, self.prop("Title"))

    def get_name(self) -> str | None:
        if self.status is None:
            return None
        name: str | None = self._cached_name or self.title
        try:
            if not name:
                tooltip = self.tooltip
                name = tooltip[2] if tooltip else None
            if not name:
                pid = get_pid(self.get_bus_name())
                name = get_process_title(pid)
        except Exception as e:
            logger.debug(
                "Couldn't get name for '%s': %s",
                self.identifier, e, exc_info=e
            )
        self._cached_name = name
        return name

    @property
    def status(self) -> Status:
        return t.cast(Status, self.prop("Status"))

    @property
    def category(self) -> Category:
        return t.cast(Category, self.prop("Category"))

    @property
    def icon_theme_path(self) -> str:
        return t.cast(str, self.prop("IconThemePath"))

    @property
    def icon_name(self) -> str:
        return t.cast(str, self.prop("IconName"))

    @property
    def icon_theme(self) -> gtk.IconTheme | None:
        search_path = self.icon_theme_path
        if not search_path:
            return None
        if not self._icon_theme:
            self._icon_theme = gtk.IconTheme()
            self._icon_theme.set_search_path(
                [search_path]
            )
        return self._icon_theme

    def get_pixbuf(
        self,
        width: int,
        height: int,
        resize_method: gdk_pixbuf.InterpType = gdk_pixbuf.InterpType.NEAREST,
    ) -> gdk_pixbuf.Pixbuf | None:
        if (pixbuf := self._pixbufs.get((width, height))):
            return pixbuf

        pixmaps = self.prop("IconPixmap")
        if not pixmaps:
            return None

        nearest_pixmap = min(
            pixmaps,
            key=lambda x: (x[0] - width) ** 2 + (x[1] - height) ** 2,
        )

        data_bytearray = bytearray(nearest_pixmap[2])
        for i in range(0, len(data_bytearray), 4):
            data_bytearray[i:i+4] = (
                data_bytearray[i+1:i+4] + data_bytearray[i:i+1]
            )

        pixbuf = gdk_pixbuf.Pixbuf.new_from_bytes(
            glib.Bytes.new(data_bytearray),
            gdk_pixbuf.Colorspace.RGB,
            True,
            8,
            nearest_pixmap[0],
            nearest_pixmap[1],
            nearest_pixmap[0] * 4,
        )

        if not pixbuf:
            return None

        if width != nearest_pixmap[0] or height != nearest_pixmap[1]:
            pixbuf = pixbuf.scale_simple(
                width,
                height,
                resize_method
            )

        self._pixbufs[(width, height)] = pixbuf
        return pixbuf

    def quit(self) -> None:
        name_owner = self._proxy.get_name_owner()
        if not name_owner:
            logger.error("Name owner of item %s is None", self.identifier)
            return
        pid = get_pid(name_owner)
        os.kill(pid, signal.SIGTERM)

    def activate(self, x: int, y: int) -> None:
        self.call_method("Activate", glib.Variant("(ii)", (x, y)))

    def secondary_activate(self, x: int, y: int) -> None:
        self.call_method("SecondaryActivate", glib.Variant("(ii)", (x, y)))

    def context_menu(self, x: int, y: int) -> None:
        self.call_method("ContextMenu", glib.Variant("(ii)", (x, y)))

    def call_method(
        self,
        method_name: str,
        params: glib.Variant
    ) -> None:
        self._proxy.call(
            method_name,
            params,
            gio.DBusCallFlags.NONE,
            -1,
            None,
            None,
            None
        )

    def _cache_proxy_properties(
        self,
        changed: list[str] | None = None
    ) -> None:
        cache_proxy_properties(self._conn, self._proxy, changed)


class StatusNotifierWatcher:
    def __init__(self) -> None:
        self._conn: gio.DBusConnection | None = None
        self.node_info = gio.DBusNodeInfo.new_for_xml(WATCHER_XML)
        self.ifaces = self.node_info.interfaces
        self.host_registered = True

    def register(self) -> int:
        return gio.bus_own_name(
            BUS_TYPE,
            BUS_WATCHER,
            gio.BusNameOwnerFlags.NONE,
            self.on_bus_acquired,
            None,
            lambda *_: logger.warning(
                "Another system tray is running"
            )
        )

    def on_name_owner_changed(
        self,
        event: NameOwnerChanged
    ) -> None:
        name, old_owner, new_owner = event.data
        if name in items.value and new_owner == "":
            logger.debug("Tray item '%s' disappeared from bus.", name)
            self.remove_item(items.value[name])
        elif old_owner in items.value and new_owner == "":
            logger.debug("Tray item '%s' disappeared from bus.", name)
            self.remove_item(items.value[old_owner])

    def on_bus_acquired(
        self, conn: gio.DBusConnection, name: str, user_data: object = None
    ) -> None:
        logger.debug("System tray bus acquired")
        Globals.events.watch(
            "name_owner_changed",
            self.on_name_owner_changed
        )
        self._conn = conn
        for interface in self.ifaces:
            if interface.name == name:
                logger.debug("Registering interface '%s'", name)
                conn.register_object(
                    PATH_WATCHER,
                    interface,
                    self.handle_bus_call
                )

    def add_item(self, item: StatusNotifierItem) -> None:
        items.value[item._bus_name] = item
        self.notify_registered_item(item.identifier)
        return

    def remove_item(self, item: StatusNotifierItem) -> None:
        try:
            item.finalize()
            items.value.pop(item._bus_name, None)
            self.notify_unregistered_item(item.identifier)
        except Exception as e:
            logger.warning(
                "Can't remove tray item with identifier '%s': %s",
                item.identifier, e
            )
        return

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
                prop_name = params[1] if len(params) >= 1 else None
                match prop_name:
                    case "ProtocolVersion":
                        logger.debug("Asked for ProtocolVersion; Returned 1")
                        invocation.return_value(
                            glib.Variant("(v)", (glib.Variant("i", 1),))
                        )
                    case "IsStatusNotifierHostRegistered":
                        logger.debug("Asked if host registered; Returned True")
                        invocation.return_value(
                            glib.Variant("(v)", (glib.Variant("b", True),))
                        )
                    case "RegisteredStatusNotifierItems":
                        logger.debug("Asked for registered items")
                        invocation.return_value(
                            glib.Variant(
                                "(v)",
                                (glib.Variant("as", items.value.keys()),)
                            ),
                        )
                    case _:
                        invocation.return_value(None)
            case "GetAll":
                logger.debug("Asked for all properties")
                all_properties = {
                    "ProtocolVersion": glib.Variant("i", 1),
                    "IsStatusNotifierHostRegistered": glib.Variant("b", True),
                    "RegisteredStatusNotifierItems": glib.Variant(
                        "as", items.value.keys()
                    ),
                }

                invocation.return_value(
                    glib.Variant("(a{sv})", (all_properties,))
                )
            case "RegisterStatusNotifierItem":
                self.create_item(
                    sender, params[0] if len(params) >= 1 else ""
                )
                invocation.return_value(None)

        return conn.flush()

    def create_item(self, bus_name: str, bus_path: str) -> None:
        if (
            bus_name is None
            or bus_path is None
            or not isinstance(bus_name, str)
            or not isinstance(bus_path, str)
            or items.value.get(bus_name + bus_path) is not None
        ):
            return

        logger.debug("Registering tray item: '%s' (%s)", bus_path, bus_name)
        if not bus_path.startswith("/"):
            bus_path = "/StatusNotifierItem"

        return self.acquire_item_proxy(bus_name, bus_path)

    def acquire_item_proxy(self, bus_name: str, bus_path: str) -> None:
        return gio.DBusProxy.new_for_bus(
            BUS_TYPE,
            gio.DBusProxyFlags.NONE,
            self.ifaces[0],
            bus_name,
            bus_path,
            BUS_ITEM,
            None,
            lambda *args: self.acquire_item_proxy_finish(
                bus_name, bus_path, *args
            ),
            None,
        )

    def acquire_item_proxy_finish(
        self,
        bus_name: str,
        bus_path: str,
        proxy: gio.DBusProxy,
        result: gio.AsyncResult,
        *args: t.Any
    ) -> None:
        proxy = proxy.new_for_bus_finish(result)
        if not proxy:
            return logger.warning(
                "Can't acquire proxy object for tray item with identifier %s",
                bus_name + bus_path
            )

        item = StatusNotifierItem(proxy)

        self.add_item(item)
        return

    def emit_bus_signal(
        self,
        signal_name: str,
        params: glib.Variant
    ) -> None:
        if not self._conn:
            return
        self._conn.emit_signal(
            None,
            PATH_WATCHER,
            BUS_WATCHER,
            signal_name,
            params,
        )

    def notify_registered_item(self, identifier: str) -> None:
        self.emit_bus_signal(
            "StatusNotifierItemRegistered",
            glib.Variant("(s)", (identifier,))
        )
        return

    def notify_unregistered_item(self, identifier: str) -> None:
        self.emit_bus_signal(
            "StatusNotifierItemUnregistered",
            glib.Variant("(s)", (identifier,)),
        )
        return


class Service(ServiceABC):
    def start(self) -> None:
        logger.debug("Starting system_tray dbus")
        watcher = StatusNotifierWatcher()
        watcher.register()

    def on_close(self) -> None:
        pass
