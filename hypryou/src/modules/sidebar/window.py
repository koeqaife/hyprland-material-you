from utils import widget
from utils.logger import logger
from repository import gtk, layer_shell
from src.variables import Globals
from src.services.events import Event
import weakref
from src.modules.sidebar.management import ManagementBox


class SidebarBox(gtk.Box):
    def __init__(self) -> None:
        super().__init__()
        self.management = ManagementBox()
        self.append(self.management)

    def destroy(self) -> None:
        self.management.destroy()
        self.remove(self.management)


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

    def destroy(self) -> None:
        Globals.events.unwatch("toggle_window", self._toggle, "sidebar")
        super().destroy()
