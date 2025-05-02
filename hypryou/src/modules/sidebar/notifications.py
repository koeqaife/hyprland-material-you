from repository import gtk
from src.services.notifications import notifications, NotificationUrgency
from src.modules.notifications.item import NotificationItem
from src.modules.notifications.item import NotificationRevealer
import typing as t
import json
from config import CONFIG_DIR, pjoin

T = t.TypeVar("T")

messengers_file = pjoin(CONFIG_DIR, "assets", "messengers.json")
try:
    with open(messengers_file, "r") as f:
        messengers = list(json.load(f))
except Exception:
    messengers = []

message_prefixes = ("im", "call", "email")


def diff_keys(
    old: dict[T, t.Any],
    new: dict[T, t.Any]
) -> tuple[set[T], set[T]]:
    old_keys = set(old)
    new_keys = set(new)

    return new_keys - old_keys, old_keys - new_keys


class Notifications(gtk.ScrolledWindow):
    def __init__(
        self
    ) -> None:
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            valign=gtk.Align.START,
            css_classes=("notifications-categories",)
        )
        super().__init__(
            child=self.box,
            vscrollbar_policy=gtk.PolicyType.AUTOMATIC,
            hscrollbar_policy=gtk.PolicyType.NEVER,
            css_classes=("notifications-scrollable",),
            hexpand=True,
            vexpand=True
        )

        self.items: dict[int, tuple[gtk.Box, NotificationRevealer]] = {}
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
            self.no_notifications_label,
            self.critical,
            self.messages,
            self.other
        )
        for child in self.children:
            self.box.append(child)

        self.freezed = True

    def freeze(self) -> None:
        if not self.freezed:
            for item in self.items.values():
                item[1].self_destroy()
                item[0].remove(item[1])
            self.items.clear()
            notifications.unwatch(self.on_change)
            self.freezed = True

    def unfreeze(self) -> None:
        if self.freezed:
            notifications.watch(self.on_change)
            self.freezed = False
            self.on_change()

    def update_no_notifications(self) -> None:
        if len(self.items) > 0:
            self.no_notifications_label.set_reveal_child(False)
        else:
            self.no_notifications_label.set_reveal_child(True)

    def get_box_for(self, item: NotificationItem) -> gtk.Box:
        if item.item.urgency == NotificationUrgency.CRITICAL:
            return self.critical

        category = item.item.hints.get("category")
        if category is not None:
            if any(category.startswith(prefix) for prefix in message_prefixes):
                return self.messages

        if any(m in item.item.app_name.lower() for m in messengers):
            return self.messages

        return self.other

    def destroy(self) -> None:
        notifications.unwatch(self.on_change)
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
                item = NotificationItem(
                    item=notifications.value[key]
                )
                box = self.get_box_for(item)
                self.items[key] = (
                    box,
                    NotificationRevealer(
                        item=item
                    )
                )
                box.insert_child_after(self.items[key][1], None)
                self.items[key][1].show()

        self.update_no_notifications()
