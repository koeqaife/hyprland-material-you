from __future__ import annotations

import signal
import os
from repository import gio, glib, gtk, gdk_pixbuf
from config import ASSETS_DIR
from utils.logger import logger
from src.services.dbus import dbus_proxy, cache_proxy_properties
from src.services.dbus import name_owner_changed
import typing as t
from utils.ref import Ref
from utils.service import Signals, Service
from utils_cy.helpers import argb_to_rgba


WATCHER_XML_PATH = os.path.join(
    ASSETS_DIR, "dbus", "org.kde.StatusNotifierWatcher.xml"
)
BUS_WATCHER = "org.kde.StatusNotifierWatcher"
PATH_WATCHER = "/StatusNotifierWatcher"

ITEM_XML_PATH = os.path.join(
    ASSETS_DIR, "dbus", "org.kde.StatusNotifierItem.xml"
)
BUS_ITEM = "org.kde.StatusNotifierItem"
PATH_ITEM = "/StatusNotifierItem"


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
        if self._proxy is None:
            return
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
        if self._proxy is None:
            self.finalize()
            return
        value = self._proxy.get_cached_property(property_name)
        if value is None:
            return None
        return value.unpack()

    @property
    def menu(self) -> str:
        return t.cast(str, self.prop("Menu"))

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
            if __debug__:
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

        if not self._proxy:
            return None
        variant = self._proxy.get_cached_property("IconPixmap")
        if variant is None or variant.n_children() == 0:
            return None

        nearest = None
        nearest_score = float("inf")

        for i in range(variant.n_children()):
            item = variant.get_child_value(i)
            w = item.get_child_value(0).get_int32()
            h = item.get_child_value(1).get_int32()
            score = (w - width) ** 2 + (h - height) ** 2
            if score < nearest_score:
                nearest = item
                nearest_score = score

        if nearest is None:
            return None

        w = nearest.get_child_value(0).get_int32()
        h = nearest.get_child_value(1).get_int32()
        data_variant = nearest.get_child_value(2)
        try:
            glib_bytes = data_variant.get_data_as_bytes()
            data_bytes = bytearray(glib_bytes.get_data() or b"")
        except MemoryError:
            return None

        data_bytes = argb_to_rgba(data_bytes)

        pixbuf = gdk_pixbuf.Pixbuf.new_from_bytes(
            glib.Bytes.new(data_bytes),
            gdk_pixbuf.Colorspace.RGB,
            True,
            8,
            w,
            h,
            w * 4,
        )

        if not pixbuf:
            return None

        if width != w or height != h:
            pixbuf = pixbuf.scale_simple(width, height, resize_method)

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
        self.host_registered = True

    def register(self) -> int:
        return gio.bus_own_name(
            gio.BusType.SESSION,
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
        name: str,
        old_owner: str,
        new_owner: str
    ) -> None:
        if name in items.value and new_owner == "":
            if __debug__:
                logger.debug("Tray item '%s' disappeared from bus.", name)
            self.remove_item(items.value[name])
        elif old_owner in items.value and new_owner == "":
            if __debug__:
                logger.debug("Tray item '%s' disappeared from bus.", name)
            self.remove_item(items.value[old_owner])

    def on_bus_acquired(
        self, conn: gio.DBusConnection, name: str, user_data: object = None
    ) -> None:
        if __debug__:
            logger.debug("System tray bus acquired")

        name_owner_changed.watch("notify", self.on_name_owner_changed)
        self._conn = conn

        with open(WATCHER_XML_PATH) as f:
            watcher_xml = f.read()
        node_info = gio.DBusNodeInfo.new_for_xml(watcher_xml)
        self.ifaces = node_info.interfaces

        for interface in self.ifaces:
            if interface.name == name:
                if __debug__:
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
                        if __debug__:
                            logger.debug(
                                "Asked for ProtocolVersion; Returned 1"
                            )
                        invocation.return_value(
                            glib.Variant("(v)", (glib.Variant("i", 1),))
                        )
                    case "IsStatusNotifierHostRegistered":
                        if __debug__:
                            logger.debug(
                                "Asked if host registered; Returned True"
                            )
                        invocation.return_value(
                            glib.Variant("(v)", (glib.Variant("b", True),))
                        )
                    case "RegisteredStatusNotifierItems":
                        if __debug__:
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
                if __debug__:
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

        if __debug__:
            logger.debug(
                "Registering tray item: '%s' (%s)",
                bus_path, bus_name
            )
        if not bus_path.startswith("/"):
            bus_path = "/StatusNotifierItem"

        return self.acquire_item_proxy(bus_name, bus_path)

    def acquire_item_proxy(self, bus_name: str, bus_path: str) -> None:
        return gio.DBusProxy.new_for_bus(
            gio.BusType.SESSION,
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


class TrayService(Service):
    def start(self) -> None:
        if __debug__:
            logger.debug("Starting system_tray dbus")
        watcher = StatusNotifierWatcher()
        watcher.register()

    def on_close(self) -> None:
        pass
