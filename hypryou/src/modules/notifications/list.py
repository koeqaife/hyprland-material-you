from repository import gtk, glib
from src.services.notifications import notifications, NotificationClosedReason
from src.modules.notifications.item import NotificationItem
from src.modules.notifications.item import NotificationRevealer
import typing as t
from utils import widget, Ref

T = t.TypeVar("T")


is_closing = Ref(False)


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

        self.clear_button_box = gtk.Box(
            css_classes=("close-button-box",)
        )
        self.clear_icon = widget.Icon("clear_all")
        self.clear_label = gtk.Label(label="Clear")
        self.clear_button_box.append(self.clear_icon)
        self.clear_button_box.append(self.clear_label)

        self.clear_button = gtk.Button(
            child=self.clear_button_box,
            halign=gtk.Align.END,
            valign=gtk.Align.END,
            css_classes=("clear-all", "elevated")
        )
        self.clear_button_handler = self.clear_button.connect(
            "clicked", self.close_all
        )

        self.children = (
            getattr(self, "no_notifications_label", None),
            self.critical,
            self.messages,
            self.other,
            self.clear_button
        )
        for child in self.children:
            if not isinstance(child, gtk.Widget):
                continue
            self.box.append(child)

        self.freezed = True
        self.closing_source = -1
        self.handler_id = -1
        self.is_closing_handler = -1
        self.update_clear_button()

    def close_next(self) -> bool | None:
        if self.items:
            try:
                key, next_item = next(self._iterator)
                next_item[1].item.item.close(
                    NotificationClosedReason.DISMISSED_BY_USER
                )
                next_item[1].destroy_with_anim(
                    self.on_item_destroy_anim
                )
                if self.closing_source != -1:
                    return True
            except StopIteration:
                pass
            except AttributeError:
                pass
        self.closing_source = -1
        is_closing.value = False
        self.items.clear()
        self.unfreeze()
        if getattr(self, "_iterator", None):
            del self._iterator

    def close_all(self, *args: t.Any) -> None:
        if is_closing.value:
            return
        if self.handler_id != -1:
            notifications.unwatch(self.handler_id)
            self.handler_id = -1
        if self.is_closing_handler != -1:
            is_closing.unwatch(self.is_closing_handler)
            self.is_closing_handler = -1
        self.freezed = True
        is_closing.value = True
        self._iterator = iter(self.items.items())
        self.closing_source = glib.timeout_add(75, self.close_next)
        self.update_clear_button()

    def freeze(self) -> None:
        if getattr(self, "_iterator", None):
            del self._iterator

        if self.closing_source != -1:
            try:
                glib.source_remove(self.closing_source)
                self.closing_source = -1
                is_closing.value = False
            except glib.Error:
                pass
        if not self.freezed:
            for item in self.items.values():
                item[1].self_destroy()
                if item[1] in item[0]:
                    item[0].remove(item[1])
            self.items.clear()
            if self.handler_id != -1:
                notifications.unwatch(self.handler_id)
                self.handler_id = -1
            if self.is_closing_handler != -1:
                is_closing.unwatch(self.is_closing_handler)
                self.is_closing_handler = -1
            self.freezed = True

    def unfreeze(self) -> None:
        if self.freezed:
            if self.handler_id == -1:
                self.handler_id = notifications.watch(self.on_change)
            if self.is_closing_handler == -1:
                self.is_closing_handler = is_closing.watch(
                    self.update_clear_button
                )
            self.freezed = False
            self.on_change()

    def update_clear_button(self, *args: t.Any) -> None:
        if len(notifications.value) > 0 and not is_closing.value:
            self.clear_button.set_visible(True)
        else:
            self.clear_button.set_visible(False)

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
        self.clear_button.disconnect(self.clear_button_handler)
        if self.closing_source != -1:
            try:
                glib.source_remove(self.closing_source)
            except glib.Error:
                pass
        if self.handler_id != -1:
            notifications.unwatch(self.handler_id)
        for item in self.items.values():
            item[1].self_destroy()
            item[0].remove(item[1])
        self.items.clear()

    def on_item_destroy_anim(self, key: int) -> None:
        if key in self.items:
            item = self.items.get(key)
            if item is None:
                return
            item[1].self_destroy()
            item[0].remove(item[1])

    def on_item_destroy(self, key: int) -> None:
        if key in self.items:
            item = self.items.pop(key)
            item[1].self_destroy()
            item[0].remove(item[1])
        self.update_no_notifications()
        self.update_clear_button()

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
        self.update_clear_button()
