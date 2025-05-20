from utils import widget
from utils.logger import logger
from repository import gtk, layer_shell
import weakref
from src.modules.sidebar.management import ManagementBox
from src.modules.sidebar.actions import Actions
from src.modules.sidebar.notifications import Notifications
from src.services.state import opened_windows
import typing as t


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
        self.name = "sidebar"
        self._child: SidebarBox | None = None

        self.handler = opened_windows.watch(self.update_visible)
        self.update_visible()

        weakref.finalize(self, lambda: logger.debug("Sidebar finalized"))

    def update_visible(self, *args: t.Any) -> None:
        is_opened = self.name in opened_windows.value
        is_visible = self.get_visible()

        if is_opened and not is_visible:
            self.present()
        elif not is_opened and is_visible:
            self.hide()

    def on_show(self) -> None:
        if not self._child:
            self._child = SidebarBox()
            self.set_child(self._child)
            self._child.notifications.unfreeze()

    def on_hide(self) -> None:
        if self._child:
            self._child.notifications.freeze()

    def destroy(self) -> None:
        opened_windows.unwatch(self.handler)
        super().destroy()
