from utils.logger import logger
from repository import layer_shell, gtk, gdk, glib
import weakref
from src.services.state import current_wallpaper
import typing as t
from src import widget


class WallpapersWidget(gtk.Stack):
    __gtype_name__ = "WallpapersWidget"

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
        new_picture.set_content_fit(gtk.ContentFit.COVER)

        self.counter += 1
        self.add_named(new_picture, str(self.counter))
        self.set_visible_child_name(str(self.counter))
        glib.timeout_add(451, self.delete_old_picture, new_picture)

    def delete_old_picture(self, new_picture: gtk.Picture) -> None:
        if self.old_picture is not None:
            self.remove(self.old_picture)
            self.old_picture = None

        self.old_picture = new_picture

    def destroy(self) -> None:
        current_wallpaper.unwatch(self.handler)


class WallpapersWindow(widget.LayerWindow):
    __gtype_name__ = "WallpapersWindow"

    def __init__(
        self,
        application: gtk.Application,
        monitor: gdk.Monitor,
        monitor_id: int
    ) -> None:
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
        if __debug__:
            weakref.finalize(
                self,
                lambda: logger.debug("WallpapersWindow finalized")
            )

    def destroy(self) -> None:
        self._child.destroy()
        self.set_child(None)
        super().destroy()
