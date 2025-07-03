from src.services.network import UserCanceled
from src.services.network import SecretPromptHandler
from src.variables import Globals
import typing as t
import weakref
from repository import gtk
import src.widget as widget


def truncate_with_ellipsis(text: str, max_length: int) -> str:
    if max_length < 3:
        raise ValueError
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


class SecretsDialog(gtk.ApplicationWindow):
    @staticmethod
    def register(app: gtk.Application) -> type["SecretsDialog"]:
        SecretPromptHandler.set_widget(SecretsDialog)
        return SecretsDialog

    def __init__(
        self,
        ssid: str,
        callback: t.Callable[[str | UserCanceled | None], None]
    ) -> None:
        self.callback_ref = weakref.WeakMethod(callback)
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            application=Globals.app,
            name="secrets-dialog",
            css_classes=("secrets-dialog",),
            title="Wifi password",
            child=self.box
        )
        self.title = gtk.Label(
            css_classes=("title",),
            label="Enter your Wi-Fi password",
            xalign=0
        )
        ssid = truncate_with_ellipsis(ssid, 16)
        self.description = gtk.Label(
            css_classes=("description",),
            label=f"To connect to “{ssid}”, please enter your password below.",
            xalign=0
        )

        self.entry_box = gtk.Box(
            css_classes=("password-entry",)
        )
        self.entry_icon = widget.Icon("key_vertical")
        self.entry = gtk.Entry(
            css_classes=("entry",),
            placeholder_text="Password",
            hexpand=True,
            visibility=False
        )
        self.entry_box.append(self.entry_icon)
        self.entry_box.append(self.entry)

        self.entry_handlers = (
            self.entry.connect("notify::text", self.on_text),
            self.entry.connect("activate", self.on_entry_enter)
        )

        self.actions_box = gtk.Box(
            css_classes=("actions-box",),
            hexpand=True,
            halign=gtk.Align.END
        )
        self.cancel_button = gtk.Button(
            css_classes=("cancel", "text"),
            label="Cancel"
        )
        self.connect_button = gtk.Button(
            css_classes=("connect", "filled"),
            label="Connect",
            sensitive=False
        )
        self.actions_box.append(self.cancel_button)
        self.actions_box.append(self.connect_button)

        self.button_handlers = {
            self.cancel_button: self.cancel_button.connect(
                "clicked", self.on_cancel
            ),
            self.connect_button: self.connect_button.connect(
                "clicked", self.on_connect
            )
        }

        self.box.append(self.title)
        self.box.append(self.description)
        self.box.append(self.entry_box)
        self.box.append(self.actions_box)

        self.close_handler = self.connect(
            "close-request", self.on_close_request
        )

    def on_close_request(self, *args: t.Any) -> None:
        self.on_cancel()
        self.destroy()

    def on_cancel(self, *args: t.Any) -> None:
        self.return_value(UserCanceled())

    def on_connect(self, *args: t.Any) -> None:
        self.return_value(self.entry.get_text())

    def destroy(self) -> None:
        for handler in self.entry_handlers:
            self.entry.disconnect(handler)
        for button, handler in self.button_handlers.items():
            button.disconnect(handler)
        self.disconnect(self.close_handler)
        super().destroy()

    def on_text(self, *args: t.Any) -> None:
        length = self.entry.get_text_length()
        self.connect_button.set_sensitive(length >= 8)

    def on_entry_enter(self, *args: t.Any) -> None:
        self.connect_button.activate()

    def return_value(self, value: str | None) -> None:
        method = self.callback_ref()
        if method is not None:
            method(value)
