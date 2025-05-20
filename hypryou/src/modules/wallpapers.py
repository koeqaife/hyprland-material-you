from utils import widget
from utils.logger import logger
from repository import layer_shell, gtk, gdk, gdk_pixbuf
import weakref
from config import Settings
import typing as t


class WallpapersWidget(gtk.Stack):
    def __init__(self) -> None:
        self.settings = Settings()
        super().__init__(
            css_classes=("wallpapers-stack",),
            transition_type=gtk.StackTransitionType.CROSSFADE,
            transition_duration=450
        )
        self.old_picture: gtk.Picture | None = None
        self.counter = -1
        self.handler = self.settings.watch(
            "wallpaper", self.update_image, True
        )

    def update_image(self, *args: t.Any) -> None:
        pixbuf = gdk_pixbuf.Pixbuf.new_from_file(
            self.settings.get("wallpaper")
        )
        self.texture = gdk.Texture.new_for_pixbuf(pixbuf)
        new_picture = gtk.Picture.new_for_paintable(self.texture)

        self.counter += 1
        self.add_named(new_picture, str(self.counter))
        self.set_visible_child_name(str(self.counter))

        if self.old_picture is not None:
            self.remove(self.old_picture)
            self.old_picture = None

    def destroy(self) -> None:
        self.settings.unwatch("wallpaper", self.handler)


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
