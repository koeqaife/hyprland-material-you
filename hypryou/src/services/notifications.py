from __future__ import annotations

from enum import Enum
import heapq
import time
from config import CONFIG_DIR
import os
from repository import glib, gio, gdk_pixbuf, gtk, gdk
from utils import Ref
from utils.logger import logger
from src.services.dbus import BUS_TYPE, ServiceABC
import typing as t
from src.variables import Globals
from src.services.events import Event

WATCHER_XML_PATH = os.path.join(
    CONFIG_DIR, "assets", "dbus", "org.freedesktop.Notifications.xml"
)
BUS_WATCHER = "org.freedesktop.Notifications"
PATH_WATCHER = "/org/freedesktop/Notifications"
with open(WATCHER_XML_PATH) as f:
    WATCHER_XML = f.read()


# Server name, vendor, version, protocol version
server_information = glib.Variant(
    "(ssss)",
    ("HyprYou", "koeqaife", "1.0", "1.3")
)
server_capabilities = glib.Variant(
    "(as)",
    ([
        "actions", "body", "body-markup",
        "icon-static", "persistence"
    ],)
)

urgency_timeouts = {
    0: 3000,
    1: 7000,
    2: 0
}
_next_id = 300

notifications = Ref[dict[int, "Notification"]]({}, name="notifications")
popups = Ref[dict[int, "Notification"]]({}, name="notif_popups")


def parse_actions(actions: list[str]) -> list[tuple[str, str]]:
    return list(zip(actions[::2], actions[1::2]))


def generate_new_id() -> int:
    global _next_id
    result = _next_id
    _next_id += 1
    return result


def get_pixbuf_from_data(tuple: ImageData) -> gdk_pixbuf.Pixbuf:
    width, height, rowstride, alpha, bits_per_sample, channels, data = tuple
    return gdk_pixbuf.Pixbuf.new_from_data(
        data,
        gdk_pixbuf.Colorspace.RGB,
        alpha,
        bits_per_sample,
        width,
        height,
        rowstride
    )


class NotificationClosedReason(int, Enum):
    EXPIRED = 1
    DISMISSED_BY_USER = 2
    CLOSED_BY_CALL = 3
    UNDEFINED = 4


class NotificationArgs(t.TypedDict):
    app_name: str
    app_icon: str
    summary: str
    body: str
    actions: list[str]
    hints: Hints


class NotificationUrgency(int, Enum):
    LOW = 0
    NORMAL = 1
    CRITICAL = 2


type ImageData = tuple[int, int, int, bool, int, int, int]
type Category = t.Literal[
    "call",
    "call.ended",
    "call.incoming",
    "call.unanswered",
    "device",
    "device.added",
    "device.error",
    "device.removed",
    "email",
    "email.arrived",
    "email.bounced",
    "im",
    "im.error",
    "im.received",
    "network",
    "network.connected",
    "network.disconnected",
    "network.error",
    "presence",
    "presence.offline",
    "presence.online",
    "transfer",
    "transfer.complete",
    "transfer.error"
]


Hints = t.TypedDict(
    "Hints", {
        "action-icons": bool,
        "category": Category,
        "desktop-entry": str,
        "image-data": ImageData,
        "image_data": ImageData,
        "image-path": str,
        "image_path": str,
        "icon_data": ImageData,
        "resident": bool,
        "sound-file": str,
        "sound-name": str,
        "suppress-sound": bool,
        "transient": bool,
        "x": int,
        "y": int,
        "urgency": NotificationUrgency
    }
)


class Notification:
    def __init__(
        self,
        id: int,
        watcher: NotificationsWatcher,
        **kwargs: t.Unpack[NotificationArgs]
    ) -> None:
        self.id = id
        self.watcher = watcher
        self.set_values(**kwargs)

    def close(self, reason: NotificationClosedReason) -> None:
        logger.debug("Closing notification %s", self.id)
        self.watcher.signal_notification_closed(self.id, reason)
        if self.id in popups.value:
            del popups.value[self.id]
        if self.id in notifications.value:
            del notifications.value[self.id]

    def dismiss(self) -> None:
        if self.id in popups.value:
            del popups.value[self.id]
        if self.hints.get("transient"):
            self.close(
                NotificationClosedReason.DISMISSED_BY_USER
            )
        else:
            logger.debug("Dismissing notification %s", self.id)

    def action(self, action: str) -> None:
        self.watcher.signal_action_invoked(self.id, action)

    def get_icon(self) -> gdk_pixbuf.Pixbuf | str | None:
        if "image-data" in self.hints.keys():
            return get_pixbuf_from_data(self.hints["image-data"])
        elif "image-path" in self.hints.keys():
            path_or_icon = self.hints["image-path"]
            if os.path.isfile(path_or_icon):
                return gdk_pixbuf.Pixbuf.new_from_file(path_or_icon)

            display = gdk.Display.get_default()
            icon_theme = gtk.IconTheme.get_for_display(display)
            if icon_theme.has_icon(path_or_icon):
                return path_or_icon
        elif "icon_data" in self.hints.keys():
            return get_pixbuf_from_data(self.hints["icon_data"])
        else:
            return None

    def set_values(
        self,
        **kwargs: t.Unpack[NotificationArgs]
    ) -> None:
        self.app_name = kwargs["app_name"]
        self.app_icon = kwargs["app_icon"]
        self.summary = kwargs["summary"]
        self.body = kwargs["body"]
        self.actions = parse_actions(kwargs["actions"])
        self.urgency: NotificationUrgency = (
            kwargs["hints"].get("urgency", NotificationUrgency.NORMAL)
        )
        self.hints = kwargs["hints"]
        self.time = time.time()


class NotificationsWatcher:
    def __init__(self) -> None:
        self.conn: gio.DBusConnection
        self.node_info = gio.DBusNodeInfo.new_for_xml(WATCHER_XML)
        self.ifaces = self.node_info.interfaces

        self.expiry_manager = ExpiryManager()
        self._expiry_timer_id: int | None = None

    def register(self) -> int:
        return gio.bus_own_name(
            BUS_TYPE,
            BUS_WATCHER,
            gio.BusNameOwnerFlags.NONE,
            self.on_bus_acquired,
            None,
            lambda *_: logger.warning(
                "Another notifications service is running"
            )
        )

    def on_bus_acquired(
        self,
        conn: gio.DBusConnection,
        name: str,
        user_data: object = None
    ) -> None:
        logger.debug("Notifications bus acquired")
        self.conn = conn
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
            case "GetCapabilities":
                logger.debug("Asked for notification capabilities")
                invocation.return_value(server_capabilities)
            case "GetServerInformation":
                logger.debug("Asked for notification server info")
                invocation.return_value(server_information)
            case "Notify":
                new_id = self.notify(*params.unpack())
                invocation.return_value(glib.Variant("(u)", (new_id, )))
            case "CloseNotification":
                id = t.cast(int, params.unpack()[0])
                if id in notifications.value:
                    notifications.value[id].close(
                        NotificationClosedReason.CLOSED_BY_CALL
                    )
                    invocation.return_value(None)
                else:
                    invocation.return_dbus_error(
                        "org.freedesktop.Notifications.Error.NotFound",
                        f"Notification with ID {id} was not found"
                    )

        return conn.flush()

    def notify(
        self,
        app_name: str,
        replaces_id: int,
        app_icon: str,
        summary: str,
        body: str,
        actions: list[str],
        hints: Hints,
        expire_timeout: int
    ) -> int:
        dismiss_on_timeout = False
        if expire_timeout > 0:
            dismiss_on_timeout = False
        else:
            dismiss_on_timeout = True
            expire_timeout = urgency_timeouts.get(hints.get("urgency", 1), 0)
        kwargs = t.cast(NotificationArgs, {
            "app_name": app_name,
            "app_icon": app_icon,
            "summary": summary,
            "body": body,
            "actions": actions,
            "hints": hints
        })
        if replaces_id and replaces_id in notifications.value:
            logger.debug(
                "Got new notification from '%s'; Replacing %s",
                app_name, replaces_id
            )
            notifications.value[replaces_id].set_values(**kwargs)
            popups.value[replaces_id] = notifications.value[replaces_id]

            if expire_timeout > 0:
                self.expiry_manager.schedule(
                    replaces_id,
                    expire_timeout,
                    dismiss_on_timeout
                )
                self._reschedule_timer()

            event = Event(
                None,
                replaces_id,
                "notification_replaced"
            )
            Globals.events.notify(event)
            return replaces_id

        new_id = generate_new_id()
        logger.debug(
            "Got new notification from '%s'; Id: %s",
            app_name, new_id
        )
        notification = Notification(new_id, self, **kwargs)
        notifications.value[new_id] = notification
        popups.value[new_id] = notification

        if expire_timeout > 0:
            self.expiry_manager.schedule(
                new_id,
                expire_timeout,
                dismiss_on_timeout
            )
            self._reschedule_timer()

        return new_id

    def _reschedule_timer(self) -> None:
        if self._expiry_timer_id is not None:
            glib.source_remove(self._expiry_timer_id)
        if not self.expiry_manager._heap:
            self._expiry_timer_id = None
            return
        next_expiry = self.expiry_manager._heap[0].expiry
        delay_ms = max(int((next_expiry - time.time()) * 1000), 0)
        self._expiry_timer_id = glib.timeout_add(delay_ms, self._on_timeout)

    def _on_timeout(self) -> bool:
        for entry in self.expiry_manager.pop_expired():
            notif = notifications.value.get(entry.notif_id)
            if notif:
                if entry.dismiss:
                    notif.dismiss()
                else:
                    notif.close(NotificationClosedReason.EXPIRED)
        self._reschedule_timer()
        return False

    def signal_action_invoked(
        self,
        id: int,
        action_key: str
    ) -> None:
        self.emit_bus_signal(
            "ActionInvoked",
            glib.Variant("(us)", (id, action_key))
        )

    def signal_notification_closed(
        self,
        id: int,
        reason: NotificationClosedReason
    ) -> None:
        self.emit_bus_signal(
            "NotificationClosed",
            glib.Variant("(uu)", (id, reason))
        )

    def emit_bus_signal(
        self,
        signal_name: str,
        params: glib.Variant
    ) -> None:
        if not self.conn:
            return
        self.conn.emit_signal(
            None,
            PATH_WATCHER,
            BUS_WATCHER,
            signal_name,
            params
        )


class TimeoutEntry(t.NamedTuple):
    expiry: float
    notif_id: int
    dismiss: bool


class ExpiryManager:
    def __init__(self) -> None:
        self._heap: list[TimeoutEntry] = []
        self._entry_finder: dict[int, TimeoutEntry] = {}

    def schedule(self, notif_id: int, timeout_ms: int, dismiss: bool) -> None:
        expiry = time.time() + timeout_ms / 1000.0
        entry = TimeoutEntry(expiry, notif_id, dismiss)
        self._entry_finder[notif_id] = entry
        heapq.heappush(self._heap, entry)

    def cancel(self, notif_id: int) -> None:
        if notif_id in self._entry_finder:
            del self._entry_finder[notif_id]

    def pop_expired(self) -> list[TimeoutEntry]:
        now = time.time()
        expired: list[TimeoutEntry] = []
        while self._heap and self._heap[0].expiry <= now:
            entry = heapq.heappop(self._heap)
            current = self._entry_finder.get(entry.notif_id)
            if current is entry:
                expired.append(entry)
                del self._entry_finder[entry.notif_id]
        return expired


class Service(ServiceABC):
    def start(self) -> None:
        watcher = NotificationsWatcher()
        watcher.register()
