from __future__ import annotations

from src.services.dbus import bus
from repository import gio, glib
from utils import Ref
from utils.logger import logger
from utils.service import Service

inhibited = Ref(False, name="inhibited")


class IdleInhibitor:
    def __init__(self) -> None:
        self._proxy = gio.DBusProxy.new_sync(
            bus,
            gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.ScreenSaver",
            "/org/freedesktop/ScreenSaver",
            "org.freedesktop.ScreenSaver",
            None
        )
        self.cookie: int = -1

    def on_inhibit(
        self,
        proxy: gio.DBusProxy,
        result: gio.AsyncResult
    ) -> None:
        props_var: glib.Variant = proxy.call_finish(result)
        self.cookie = int(props_var.unpack()[0])
        logger.debug("On Inhibit; Cookie: %s", self.cookie)
        inhibited.value = True

    def on_un_inhibit(
        self,
        proxy: gio.DBusProxy,
        result: gio.AsyncResult
    ) -> None:
        proxy.call_finish(result)
        logger.debug("On UnInhibit; Cookie: %s", self.cookie)
        self.cookie = -1
        inhibited.value = False

    def inhibit(self) -> None:
        logger.debug("Trying to call Inhibit.")
        self._proxy.call(
            "Inhibit",
            glib.Variant("(ss)", ("HyprYou", "User action")),
            gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_inhibit
        )

    def un_inhibit(self) -> None:
        if self.cookie == -1:
            return
        logger.debug("Trying to call UnInhibit.")
        self._proxy.call(
            "UnInhibit",
            glib.Variant("(u)", (self.cookie,)),
            gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_un_inhibit
        )

    def un_inhibit_sync(self) -> None:
        if self.cookie == -1:
            return
        logger.debug("Trying to call UnInhibit (sync).")
        self._proxy.call_sync(
            "UnInhibit",
            glib.Variant("(u)", (self.cookie,)),
            gio.DBusCallFlags.NONE,
            -1,
            None
        )
        logger.debug("On UnInhibit; Cookie: %s", self.cookie)
        self.cookie = -1
        inhibited.value = False


_instance: IdleInhibitor | None = None


def get_inhibitor() -> IdleInhibitor:
    if not _instance:
        raise RuntimeError(
            "Couldn't get instance of idle inhibitor. " +
            "Most likely it's not initialized."
        )

    return _instance


class IdleInhibitorService(Service):
    def app_init(self) -> None:
        global _instance
        logger.debug("Starting idle inhibitor proxy")
        _instance = IdleInhibitor()

    def on_close(self) -> None:
        if _instance is not None:
            _instance.un_inhibit_sync()
