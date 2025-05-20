from repository import gtk, glib
from utils import widget, Ref
import typing as t
import subprocess
from utils.logger import logger
from src.services.state import close_window


def open_hyprpicker(*_: t.Any) -> None:
    def start() -> None:
        subprocess.Popen(["hyprpicker", "-a"])
    close_window("sidebar")
    glib.timeout_add(250, start)


def open_power_menu(*_: t.Any) -> None:
    logger.warning("Not implemented yet")


def open_settings(*_: t.Any) -> None:
    logger.warning("Not implemented yet")


class ActionButton(gtk.Button):
    def __init__(
        self,
        icon: str | Ref[str],
        on_click: t.Callable[..., None]
    ) -> None:
        super().__init__(
            css_classes=("action-button", "icon-outlined"),
            hexpand=True
        )
        self.icon = widget.Icon(icon)
        self.set_child(self.icon)
        self.conn = self.connect("clicked", on_click)

    def destroy(self) -> None:
        self.disconnect(self.conn)
        self.icon.destroy()


class Actions(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("action-buttons",),
            hexpand=True
        )
        self.color_picker = ActionButton(
            "colorize", open_hyprpicker
        )
        self.power = ActionButton(
            "power_settings_new", open_power_menu
        )
        self.settings = ActionButton(
            "settings", open_settings
        )
        self.children = (
            self.color_picker,
            self.power,
            self.settings
        )
        for child in self.children:
            self.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
            self.remove(child)
