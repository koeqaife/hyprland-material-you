from src.services.bluetooth_agent import OperationCanceled
from src.services.bluetooth_agent import OperationRejected
from src.services.bluetooth_agent import CallbackReturn
from src.services.bluetooth_agent import PinDialogHandler
from src.variables import Globals
import typing as t
import weakref
from repository import gtk


class PinDialog(gtk.ApplicationWindow):
    @staticmethod
    def register(app: gtk.Application) -> type["PinDialog"]:
        PinDialogHandler.set_widget(PinDialog)
        return PinDialog

    def __init__(
        self,
        pin: str,
        show_buttons: bool,
        callback: t.Callable[[CallbackReturn], None]
    ) -> None:
        self.callback_ref = weakref.WeakMethod(callback)
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            application=Globals.app,
            name="pin-dialog",
            css_classes=("pin-dialog",),
            title="Pairing Confirmation",
            child=self.box
        )
        self.title = gtk.Label(
            css_classes=("title",),
            xalign=0
        )
        self.description = gtk.Label(
            css_classes=("description",),
            use_markup=True,
            xalign=0
        )
        if show_buttons:
            self.title.set_text("Pairing Confirmation")
            self.description.set_text(
                f"Verify that the code on your device matches: <b>{pin}</b>" +
                "\nDoes this code match?"
            )
        else:
            self.title.set_text("Enter PIN Code")
            self.description.set_text(
                "Please enter this PIN code on the other device:" +
                f"\n<b>{pin}</b>"
            )

        self.box.append(self.title)
        self.box.append(self.description)

        if show_buttons:
            self.actions_box = gtk.Box(
                css_classes=("actions-box",),
                hexpand=True,
                halign=gtk.Align.END
            )
            self.no_button = gtk.Button(
                css_classes=("cancel", "text"),
                label="No"
            )
            self.yes_button = gtk.Button(
                css_classes=("connect", "filled"),
                label="Yes"
            )
            self.actions_box.append(self.no_button)
            self.actions_box.append(self.yes_button)

            self.button_handlers = {
                self.no_button: self.no_button.connect(
                    "clicked", self.on_reject
                ),
                self.yes_button: self.yes_button.connect(
                    "clicked", self.on_connect
                )
            }
            self.box.append(self.actions_box)

        self.close_handler = self.connect(
            "close-request", self.on_close_request
        )

    def on_close_request(self, *args: t.Any) -> None:
        self.on_cancel()
        self.destroy()

    def on_reject(self, *args: t.Any) -> None:
        self.return_value(OperationRejected())

    def on_cancel(self, *args: t.Any) -> None:
        self.return_value(OperationCanceled())

    def on_connect(self, *args: t.Any) -> None:
        self.return_value(None)

    def destroy(self) -> None:
        if hasattr(self, "button_handlers"):
            for button, handler in self.button_handlers.items():
                button.disconnect(handler)
        self.disconnect(self.close_handler)
        super().destroy()

    def return_value(self, value: str | None) -> None:
        method = self.callback_ref()
        if method is not None:
            method(value)
