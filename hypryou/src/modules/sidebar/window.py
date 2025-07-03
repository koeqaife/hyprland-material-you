from config import HyprlandVars, Settings
from utils.logger import logger
from utils import toggle_css_class
from repository import gtk, layer_shell
import weakref
from src.modules.sidebar.management import ManagementBox
from src.modules.sidebar.actions import Actions
from src.modules.notifications.list import Notifications
from src import widget


class SidebarBox(gtk.Box):
    __gtype_name__ = "SidebarBox"

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


edges = (
    layer_shell.Edge.TOP,
    layer_shell.Edge.BOTTOM,
    layer_shell.Edge.RIGHT,
)


class Sidebar(widget.LayerWindow):
    __gtype_name__ = "SidebarWindow"

    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            application=app,
            anchors={
                "top": True,
                "right": True,
                "bottom": True
            },
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="sidebar",
            css_classes=("sidebar",),
            setup_popup=True
        )
        self._child: SidebarBox | None = None

        self.settings = Settings()
        self.settings_handler = self.settings.watch(
            "floating_sidebar", self.change_floating
        )

        if __debug__:
            weakref.finalize(self, lambda: logger.debug("Sidebar finalized"))

    def change_floating(self, value: bool) -> None:
        toggle_css_class(self, "floating", value)
        if value:
            gap = HyprlandVars.gap
            for edge in edges:
                layer_shell.set_margin(self, edge, gap)
        else:
            for edge in edges:
                layer_shell.set_margin(self, edge, 0)

    def present(self) -> None:
        if self._child:
            self._child.notifications.unfreeze()
        super().present()

    def on_show(self) -> None:
        if not self._child:
            self._child = SidebarBox()
            self._child.notifications.unfreeze()
            self.set_child(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.notifications.freeze()

    def destroy(self) -> None:
        self.settings.unwatch(self.settings_handler)
        super().destroy()
