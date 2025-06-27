from repository import gtk, layer_shell
from utils import sync_debounce
from utils.logger import logger
import typing as t
from config import HyprlandVars, Settings
import weakref
from src.services.login1 import get_login_manager
from src.services.state import is_locked, close_window
from src.services import hyprland
from src.services.mpris import players
import asyncio
import src.services.cliphist as cliphist
from src import widget


class ActionButton(gtk.Button):
    __gtype_name__ = "PowerActionButton"

    def __init__(
        self,
        icon: str,
        label: str,
        on_click: t.Callable[[], None]
    ) -> None:
        self.on_click = sync_debounce(750, 1, True)(on_click)
        self.box = gtk.Box(
            css_classes=("power-button-box",)
        )
        super().__init__(
            css_classes=("power-button",),
            child=self.box
        )
        self.icon = widget.Icon(icon)
        self.label = gtk.Label(
            label=label,
            css_classes=("label",)
        )
        self.box.append(self.icon)
        self.box.append(self.label)

        self.handler_id = self.connect("clicked", self.on_click)

    def destroy(self) -> None:
        self.disconnect(self.handler_id)
        del self.on_click


class PowerMenu(gtk.Box):
    __gtype_name__ = "PowerMenu"

    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL
        )
        self.login1 = get_login_manager()
        self.children = (
            ActionButton("lock", "Lock", self.on_lock),
            ActionButton("bedtime", "Sleep", self.on_sleep),
            ActionButton("logout", "Logout", self.on_logout),
            ActionButton("restart_alt", "Restart", self.on_restart),
            ActionButton("mode_off_on", "Shutdown", self.on_shutdown),
        )
        for child in self.children:
            self.append(child)

        self.cancel_button: ActionButton | None = None
        if Settings().get("power_menu_cancel_button"):
            self.cancel_button = ActionButton(
                "close", "Cancel", self.on_cancel
            )
            self.append(self.cancel_button)
        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("PowerMenu finalized")
            )

    def on_lock(self, *args: t.Any) -> None:
        is_locked.value = True

    def on_sleep(self, *args: t.Any) -> None:
        is_locked.value = True
        for player in players.value.values():
            player.pause()
        self.login1.suspend()

    def on_logout(self, *args: t.Any) -> None:
        if Settings().get("secure_cliphist"):
            cliphist.secure_clear()
        asyncio.create_task(
            hyprland.client.raw("dispatch exit")
        )

    def on_restart(self, *args: t.Any) -> None:
        self.login1.reboot()

    def on_shutdown(self, *args: t.Any) -> None:
        self.login1.power_off()

    def on_cancel(self, *args: t.Any) -> None:
        close_window("power_menu")

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
            self.remove(child)
        if self.cancel_button:
            self.cancel_button.destroy()
            self.remove(self.cancel_button)


class PowerMenuWindow(widget.LayerWindow):
    __gtype_name__ = "PowerMenuWindow"

    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            anchors={
                "top": True,
                "right": True
            },
            margins={
                "top": HyprlandVars.gap,
                "right": HyprlandVars.gap
            },
            css_classes=("power-menu",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="power_menu",
            height=1,
            width=1,
            setup_popup=True
        )
        self._child: PowerMenu | None = None

        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("PowerMenuWindow finalized")
            )

    def on_show(self) -> None:
        self._child = PowerMenu()
        self.set_child(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
        self.set_child(None)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
