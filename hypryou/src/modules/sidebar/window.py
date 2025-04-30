from utils import widget
from utils.logger import logger
from repository import gtk, layer_shell
from src.variables import Globals
from src.services.events import Event
import weakref
from src.modules.sidebar.management import ManagementBox
from src.modules.sidebar.actions import Actions
from src.modules.sidebar.notifications import Notifications


class SidebarBox(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL
        )
        self.management = ManagementBox()
        self.actions = Actions()
        self.notifications = Notifications()
        self.children = (
            self.management,
            self.actions,
            self.notifications
        )
        for child in self.children:
            self.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
            self.remove(child)


class Sidebar(widget.LayerWindow):
    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            application=app,
            anchors={
                "top": True,
                "right": True,
                "bottom": True
            },
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            hide_on_esc=True,
            name="sidebar",
            css_classes=("sidebar",)
        )
        self._child: SidebarBox | None = None
        Globals.events.watch("toggle_window", self._toggle, "sidebar")
        weakref.finalize(self, lambda: logger.debug("Sidebar finalized"))

    def _toggle(self, _: Event) -> None:
        if self.is_visible():
            self.hide()
        else:
            self.present()

    def on_show(self) -> None:
        if not self._child:
            self._child = SidebarBox()
            self.set_child(self._child)
        Globals.sidebar_opened = True

    def on_hide(self) -> None:
        Globals.sidebar_opened = False

    def destroy(self) -> None:
        Globals.events.unwatch("toggle_window", self._toggle, "sidebar")
        super().destroy()
