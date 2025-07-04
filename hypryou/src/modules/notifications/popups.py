from repository import gtk, gdk, layer_shell
from src.services.notifications import popups
from src.modules.notifications.item import NotificationItem
from src.modules.notifications.item import NotificationRevealer
import typing as t
from config import HyprlandVars
from src.services.state import opened_windows, is_locked
from src import widget

T = t.TypeVar("T")


def diff_keys(
    old: dict[T, t.Any],
    new: dict[T, t.Any]
) -> tuple[set[T], set[T]]:
    old_keys = set(old)
    new_keys = set(new)

    return new_keys - old_keys, old_keys - new_keys


class NotificationPopups(gtk.Box):
    __gtype_name__ = "NotificationPopups"

    def __init__(
        self,
        window: gtk.ApplicationWindow
    ) -> None:
        self.window = window
        super().__init__(
            css_classes=("notification-popups",),
            orientation=gtk.Orientation.VERTICAL
        )

        self.items: dict[int, NotificationRevealer] = {}
        self.handler_id = popups.watch(self.on_change)

    def destroy(self) -> None:
        popups.unwatch(self.handler_id)
        for item in self.items.values():
            item.self_destroy()
        self.items.clear()

    def on_item_destroy(self, key: int) -> None:
        if key in self.items:
            item = self.items.pop(key)
            item.self_destroy()
            self.remove(item)
        self.update_window_state()

    def update_window_state(self) -> None:
        if (
            len(self.items) == 0
            or opened_windows.is_visible("sidebar")
            or is_locked.value
        ):
            self.window.hide()
        else:
            self.window.show()

    def on_change(self, *args: t.Any) -> None:
        to_show: list[NotificationRevealer] = []
        added_keys, removed_keys = diff_keys(
            old=self.items,
            new=popups.value
        )

        for key in removed_keys:
            if key in self.items:
                self.items[key].destroy_with_anim(
                    self.on_item_destroy
                )

        if is_locked.value:
            self.window.hide()
            return

        for key in added_keys:
            if key not in self.items and key in popups.value:
                item = NotificationItem(
                    item=popups.value[key],
                    show_dismiss=True
                )
                self.items[key] = NotificationRevealer(
                    item=item
                )
                self.insert_child_after(self.items[key], None)
                to_show.append(self.items[key])

        self.update_window_state()

        for revealer in to_show:
            revealer.show()


class Notifications(widget.LayerWindow):
    __gtype_name__ = "NotificationsWindow"

    def __init__(
        self,
        application: gtk.Application,
        monitor: gdk.Monitor,
        monitor_id: int
    ) -> None:
        super().__init__(
            application=application,
            monitor=monitor,
            width=1,
            height=1,
            anchors={
                "top": True,
                "right": True
            },
            margins={
                "top": HyprlandVars.gap,
                "right": HyprlandVars.gap
            },
            css_classes=("notifications", "transparent"),
            name=f"notifications{monitor_id}",
            layer=layer_shell.Layer.OVERLAY
        )

        self.popups = NotificationPopups(self)
        self.set_child(self.popups)

    def destroy(self) -> None:
        self.popups.destroy()
        self.popups = None  # type: ignore
        self.set_child(None)
        return super().destroy()
