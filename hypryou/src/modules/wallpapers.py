from utils import widget
from utils.logger import logger
from repository import layer_shell, gtk, gdk
import weakref
from src.services.state import current_wallpaper
import typing as t


class WallpapersWidget(gtk.Stack):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("wallpapers-stack",),
            transition_type=gtk.StackTransitionType.CROSSFADE,
            transition_duration=450
        )
        self.old_picture: gtk.Picture | None = None
        self.counter = -1
        self.handler = current_wallpaper.watch(self.update_image)
        self.update_image()

    def update_image(self, *args: t.Any) -> None:
        texture = current_wallpaper.value
        new_picture = gtk.Picture.new_for_paintable(texture)

        self.counter += 1
        self.add_named(new_picture, str(self.counter))
        self.set_visible_child_name(str(self.counter))

        if self.old_picture is not None:
            self.remove(self.old_picture)
            self.old_picture = None

    def destroy(self) -> None:
        current_wallpaper.unwatch("wallpaper", self.handler)


class WallpapersWindow(widget.LayerWindow):
    def __init__(self, application: gtk.Application, monitor: gdk.Monitor):
        super().__init__(
            application,
            anchors={
                "top": True,
                "left": True,
                "right": True,
                "bottom": True
            },
            exclusive=True,
            monitor=monitor,
            css_classes=("wallpapers",),
            name="wallpapers",
            layer=layer_shell.Layer.BACKGROUND
        )
        layer_shell.set_exclusive_zone(self, -1)

        self._child = WallpapersWidget()
        self.set_child(self._child)
        self.present()
        weakref.finalize(self, lambda: logger.debug("Bar finalized"))

    def destroy(self) -> None:
        self._child.destroy()
        self.set_child(None)
        super().destroy()
