from repository import gtk
from src.services.notifications import notifications
from src.modules.notifications.item import NotificationItem
from src.modules.notifications.item import NotificationRevealer
import typing as t

T = t.TypeVar("T")


def diff_keys(
    old: dict[T, t.Any],
    new: dict[T, t.Any]
) -> tuple[set[T], set[T]]:
    old_keys = set(old)
    new_keys = set(new)

    return new_keys - old_keys, old_keys - new_keys


class Notifications(gtk.ScrolledWindow):
    def __init__(
        self,
        hide_sensitive_content: bool = False,
        no_notifications_label: bool = True,
        item: type[NotificationItem] = NotificationItem,
        revealer: type[NotificationRevealer] = NotificationRevealer
    ) -> None:
        self.hide_content = hide_sensitive_content
        self.show_no_notifications_label = no_notifications_label
        self._item = item
        self._revealer = revealer
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            valign=gtk.Align.START,
            css_classes=("notifications-categories",)
        )
        super().__init__(
            child=self.box,
            vscrollbar_policy=gtk.PolicyType.AUTOMATIC,
            hscrollbar_policy=gtk.PolicyType.NEVER,
            css_classes=("notifications-scrollable", "notifications-list"),
            hexpand=True,
            vexpand=True
        )

        self.items: dict[int, tuple[gtk.Box, NotificationRevealer]] = {}
        if self.show_no_notifications_label:
            self.no_notifications_label = gtk.Revealer(
                transition_type=gtk.RevealerTransitionType.SLIDE_DOWN,
                transition_duration=250,
                child=gtk.Label(label="No notifications"),
                css_classes=("no-notifications",)
            )
        self.critical = gtk.Box(
            css_classes=("notifications",),
            orientation=gtk.Orientation.VERTICAL,
            valign=gtk.Align.START
        )
        self.messages = gtk.Box(
            css_classes=("notifications",),
            orientation=gtk.Orientation.VERTICAL,
            valign=gtk.Align.START
        )
        self.other = gtk.Box(
            css_classes=("notifications",),
            orientation=gtk.Orientation.VERTICAL,
            valign=gtk.Align.START
        )

        self.children = (
            getattr(self, "no_notifications_label", None),
            self.critical,
            self.messages,
            self.other
        )
        for child in self.children:
            if not isinstance(child, gtk.Widget):
                continue
            self.box.append(child)

        self.freezed = True
        self.handler_id = -1

    def freeze(self) -> None:
        if not self.freezed:
            for item in self.items.values():
                item[1].self_destroy()
                item[0].remove(item[1])
            self.items.clear()
            if self.handler_id != -1:
                notifications.unwatch(self.handler_id)
            self.freezed = True

    def unfreeze(self) -> None:
        if self.freezed:
            self.handler_id = notifications.watch(self.on_change)
            self.freezed = False
            self.on_change()

    def update_no_notifications(self) -> None:
        if not self.show_no_notifications_label:
            return
        if len(self.items) > 0:
            self.no_notifications_label.set_reveal_child(False)
        else:
            self.no_notifications_label.set_reveal_child(True)

    def get_box_for(self, item: NotificationItem) -> gtk.Box:
        category = item.get_detected_category()
        if not category:
            return self.other
        if category == "messages":
            return self.messages
        if category == "critical":
            return self.critical

    def destroy(self) -> None:
        if self.handler_id != -1:
            notifications.unwatch(self.handler_id)
        for item in self.items.values():
            item[1].self_destroy()
            item[0].remove(item[1])
        self.items.clear()

    def on_item_destroy(self, key: int) -> None:
        if key in self.items:
            item = self.items.pop(key)
            item[1].self_destroy()
            item[0].remove(item[1])
        self.update_no_notifications()

    def on_change(self, *args: t.Any) -> None:
        added_keys, removed_keys = diff_keys(
            old=self.items,
            new=notifications.value
        )

        for key in removed_keys:
            if key in self.items:
                self.items[key][1].destroy_with_anim(
                    self.on_item_destroy
                )

        for key in added_keys:
            if key not in self.items and key in notifications.value:
                item = self._item(
                    item=notifications.value[key],
                    hide_sensitive_content=self.hide_content
                )
                box = self.get_box_for(item)
                self.items[key] = (
                    box,
                    self._revealer(
                        item=item
                    )
                )
                box.insert_child_after(self.items[key][1], None)
                self.items[key][1].show()

        self.update_no_notifications()
