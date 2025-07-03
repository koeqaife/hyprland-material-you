import typing as t
from repository import gtk, glib, gio
from utils.logger import logger
import os
from config import CONFIG_DIR
from utils.service import Service

AGENT_XML_PATH = os.path.join(
    CONFIG_DIR, "assets", "dbus",
    "org.bluez.Agent1.xml"
)
with open(AGENT_XML_PATH) as f:
    AGENT_XML = f.read()


class OperationCanceled:
    ...


class OperationRejected:
    ...


type CallbackReturn = OperationCanceled | OperationRejected | None


if t.TYPE_CHECKING:
    class PinDialog(gtk.ApplicationWindow):
        def __init__(
            self,
            pin: str,
            show_buttons: bool,
            callback: t.Callable[[CallbackReturn], None]
        ) -> None:
            ...

        def on_close_request(self, *args: t.Any) -> None:
            ...

        def on_cancel(self, *args: t.Any) -> None:
            ...

        def on_connect(self, *args: t.Any) -> None:
            ...

        def destroy(self) -> None:
            ...

        def on_text(self, *args: t.Any) -> None:
            ...

        def on_entry_enter(self, *args: t.Any) -> None:
            ...

        def return_value(self, value: str | None) -> None:
            ...


class PinDialogHandler:
    widget: "PinDialog | None" = None

    @staticmethod
    def set_widget(widget: t.Any) -> None:
        PinDialogHandler.widget = t.cast("PinDialog", widget)

    def __init__(
        self,
        conn: gio.DBusConnection,
        invocation: gio.DBusMethodInvocation,
        pin: str,
        show_buttons: bool,
        on_finish: t.Callable[[], None]
    ) -> None:
        self.pin = pin
        self.show_buttons = show_buttons
        self.conn = conn
        self.invocation = invocation
        self._on_finish = on_finish
        self.dialog: PinDialog | None = None

        if __debug__:
            logger.debug(
                "PinDialogHandler: pin: %s",
                pin
            )

        self.ask()

    def on_finish(self) -> None:
        if self.dialog:
            self.dialog.destroy()
        self._on_finish()

    def cancel(self) -> None:
        self.on_dialog_finish(OperationCanceled())

    def on_dialog_finish(
        self, value: OperationRejected | OperationCanceled | None
    ) -> None:
        if value is None:
            self.invocation.return_value(None)
        elif isinstance(value, OperationRejected):
            self.invocation.return_dbus_error(
                "org.bluez.Error.Rejected",
                "User/Daemon rejected the operation"
            )
        elif isinstance(value, OperationCanceled):
            self.invocation.return_dbus_error(
                "org.bluez.Error.Canceled",
                "User/Daemon canceled the operation"
            )
        else:
            self.invocation.return_value(None)
        self.on_finish()

    def ask(self) -> None:
        if self.widget is None:
            self.invocation.return_dbus_error(
                "org.bluez.Error.Failed",
                "Not initialized widget"
            )
            raise RuntimeError(
                "Var widget is not set! Most likely is not initialized. " +
                "Aborting..."
            )
        if not self.dialog:
            self.dialog = self.widget(
                self.pin,
                self.show_buttons,
                self.on_dialog_finish
            )
            self.dialog.present()


class BluetoothAgent:
    def __init__(self) -> None:
        self.conn = gio.bus_get_sync(gio.BusType.SYSTEM)
        self.node_info = gio.DBusNodeInfo.new_for_xml(AGENT_XML)
        self.iface = self.node_info.interfaces[0]
        self.active_handlers: dict[str, PinDialogHandler] = {}

    def register(self) -> int:
        if __debug__:
            logger.debug("Registering interface '%s'", self.iface.name)

        self.reg_id = self.conn.register_object(
            "/com/koeqaife/BluetoothAgent",
            self.iface,
            self.handle_bus_call
        )

        if __debug__:
            logger.debug("Registering BluetoothAgent")
        proxy = gio.DBusProxy.new_sync(
            self.conn,
            gio.DBusProxyFlags.NONE,
            None,
            "org.bluez",
            "/org/bluez",
            "org.bluez.AgentManager1",
            None
        )

        proxy.call_sync(
            "RegisterAgent",
            glib.Variant("(os)", (
                "/com/koeqaife/BluetoothAgent",
                "DisplayYesNo",
            )),
            gio.DBusCallFlags.NONE,
            -1,
            None,
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
            case "RequestConfirmation":
                device, passkey = params.unpack()
                key = f"confirmation:{device}"

                if key in self.active_handlers:
                    logger.warning("Handler already active for %s", key)
                    invocation.return_dbus_error(
                        "org.bluez.Error.AlreadyExists",
                        "Handler already active"
                    )
                    return

                handler = PinDialogHandler(
                    conn,
                    invocation,
                    str(passkey),
                    True,
                    lambda key=key: (
                        self.active_handlers.pop(key, None)
                    )
                )

                self.active_handlers[key] = handler
            case "RequestPinCode":
                invocation.return_dbus_error(
                    "org.bluez.Error.NotSupported",
                    "RequestPinCode method is not supported by this agent"
                )
            case "AuthorizeService":
                invocation.return_dbus_error(
                    "org.bluez.Error.NotSupported",
                    "AuthorizeService method is not supported by this agent"
                )
            case "DisplayPinCode":
                device, passkey = params.unpack()
                key = f"display_pin:{device}"

                if key in self.active_handlers:
                    logger.warning("Handler already active for %s", key)
                    invocation.return_dbus_error(
                        "org.bluez.Error.AlreadyExists",
                        "Handler already active"
                    )
                    return

                handler = PinDialogHandler(
                    conn,
                    invocation,
                    str(passkey),
                    False,
                    lambda key=key: (
                        self.active_handlers.pop(key, None)
                    )
                )

                self.active_handlers[key] = handler
            case "Release":
                self.conn.unregister_object(self.reg_id)
                logger.debug("BluetoothAgent released.")
            case "Cancel":
                for handler in set(self.active_handlers.values()):
                    handler.cancel()
                self.active_handlers.clear()


class BluetoothAgentService(Service):
    def start(self) -> None:
        self.agent = BluetoothAgent()
        self.agent.register()
