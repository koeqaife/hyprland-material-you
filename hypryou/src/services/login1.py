from repository import gio, glib
from utils.logger import logger
from utils.service import Service


class Login1Manager:
    def __init__(self) -> None:
        self._proxy = gio.DBusProxy.new_for_bus_sync(
            gio.BusType.SYSTEM,
            gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager",
            None
        )
        self.session = gio.DBusProxy.new_for_bus_sync(
            gio.BusType.SYSTEM,
            gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.login1",
            "/org/freedesktop/login1/session/self",
            "org.freedesktop.login1.Session"
        )

    def set_brightness(
        self,
        subsystem: str,
        device: str,
        brightness: int
    ) -> None:
        self.session.call_sync(
            "SetBrightness",
            glib.Variant(
                "(ssu)",
                (subsystem, device, brightness)
            ),
            gio.DBusCallFlags.NONE,
            -1,
            None
        )

    def call(self, name: str, params: glib.Variant | None = None) -> None:
        self._proxy.call(
            name,
            params,
            gio.DBusCallFlags.NONE,
            -1,
            None
        )

    def suspend(self) -> None:
        self.call(
            "Suspend",
            glib.Variant("(b)", (True,))
        )

    def power_off(self) -> None:
        self.call(
            "PowerOff",
            glib.Variant("(b)", (True,))
        )

    def reboot(self) -> None:
        self.call(
            "Reboot",
            glib.Variant("(b)", (True,))
        )

    def _is_inhibited(self, what: str) -> bool:
        result = self._proxy.call_sync(
            "ListInhibitors",
            None,
            gio.DBusCallFlags.NONE,
            -1,
            None
        )

        inhibitors: tuple[tuple[str, ...]] = result.unpack()[0]
        for inhibitor in inhibitors:
            i_what, who, why, mode, _uid, _pid = inhibitor
            if i_what == what and mode == "block":
                logger.debug(
                    "%s is blocked by: %s — %s",
                    what, who, why
                )
                return True

        return False

    def can_sleep(self) -> bool:
        return not self._is_inhibited("sleep")

    def is_idle_inhibited(self) -> bool:
        return self._is_inhibited("idle")


_instance: Login1Manager | None = None


def get_login_manager() -> Login1Manager:
    if not _instance:
        raise RuntimeError(
            "Couldn't get instance of login1 manager. " +
            "Most likely it's not initialized."
        )

    return _instance


class Login1ManagerService(Service):
    def app_init(self) -> None:
        global _instance
        logger.debug("Starting login1 manager proxy")
        _instance = Login1Manager()
