from repository import gtk, glib, pango, gdk, gio
from src.services.notifications import Notification, NotificationClosedReason
from src.services.notifications import Category, NotificationUrgency
from utils import widget
import typing as t
from utils import get_formatted_time, toggle_css_class
from config import Settings
import datetime
import json
from config import CONFIG_DIR
from os.path import join as pjoin

safe_categories: tuple[Category, ...] = (
    "device",
    "network",
    "transfer",
    "call"
)

messengers_file = pjoin(CONFIG_DIR, "assets", "messengers.json")
try:
    with open(messengers_file, "r") as f:
        messengers = list(json.load(f))
except Exception:
    messengers = []

message_prefixes = ("im", "call", "email")


def get_is_sensitive(item: "NotificationItem") -> bool:
    if item.item.urgency == NotificationUrgency.CRITICAL:
        return False

    category = item.item.hints.get("category")
    if (
        (category
         and not any(
             category.startswith(prefix) for prefix in safe_categories)
         )
        or item.get_detected_category() == "messages"
    ):
        return True

    return False


class NotificationItem(gtk.Box):
    def __init__(
        self,
        item: Notification,
        show_dismiss: bool = False,
        hide_sensitive_content: bool = False
    ) -> None:
        self.is_destroyed = False
        self.hide_content = hide_sensitive_content
        if item.hints.get("transient") and show_dismiss:
            show_dismiss = False
        self.item = item
        super().__init__(
            css_classes=("notification",),
            orientation=gtk.Orientation.VERTICAL,
            halign=gtk.Align.END,
            valign=gtk.Align.START
        )

        self._cached_detected: t.Literal["critical", "messages"] | None = None
        self.conns: dict[gtk.Widget, int] = {}

        # Notification header
        self.header_box = gtk.Box(
            css_classes=("header",)
        )
        self.info_box = gtk.Box(
            css_classes=("info",),
            halign=gtk.Align.START,
            hexpand=True
        )
        self.app_icon = gtk.Image(
            css_classes=("app-icon",),
            halign=gtk.Align.START,
            height_request=24,
            width_request=24,
            icon_name="application-x-executable-symbolic"
        )
        self.app_title = gtk.Label(
            css_classes=("app-title",),
            halign=gtk.Align.START,
            ellipsize=pango.EllipsizeMode.END,
            max_width_chars=20
        )
        self.separator = gtk.Label(
            css_classes=("separator",),
            label="•",
            halign=gtk.Align.START
        )
        self.time = gtk.Label(
            css_classes=("time",),
            halign=gtk.Align.START
        )
        self.close = gtk.Button(
            child=widget.Icon("close"),
            halign=gtk.Align.END,
            css_classes=("close", "icon-default"),
            tooltip_text="Close"
        )
        self.dismiss = gtk.Button(
            child=widget.Icon("chevron_right"),
            halign=gtk.Align.END,
            css_classes=("dismiss", "icon-default"),
            tooltip_text="Hide"
        ) if show_dismiss else None

        self.conns[self.close] = self.close.connect(
            "clicked", self.on_close
        )

        if self.dismiss:
            self.conns[self.dismiss] = self.dismiss.connect(
                "clicked", self.on_dismiss
            )

        self.info_box.append(self.app_icon)
        self.info_box.append(self.app_title)
        self.info_box.append(self.separator)
        self.info_box.append(self.time)
        self.header_box.append(self.info_box)
        if self.dismiss:
            self.header_box.append(self.dismiss)
        self.header_box.append(self.close)

        # Notification body
        self.body_box = gtk.Box(
            css_classes=("body",)
        )
        self.image = gtk.Image(
            css_classes=("body-image",),
            valign=gtk.Align.START,
        )
        self.text_box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.title = gtk.Label(
            css_classes=("title",),
            halign=gtk.Align.START,
            wrap=True,
            wrap_mode=pango.WrapMode.WORD_CHAR,
        )
        self.body_text = gtk.Label(
            css_classes=("body-text",),
            use_markup=True,
            halign=gtk.Align.START,
            wrap=True,
            wrap_mode=pango.WrapMode.WORD_CHAR,
        )
        self.text_box.append(self.title)
        self.text_box.append(self.body_text)
        self.body_box.append(self.image)
        self.body_box.append(self.text_box)

        # Notification actions
        self.actions_box = gtk.Box(
            css_classes=("actions",),
            spacing=8,
            halign=gtk.Align.END
        )
        self.action_buttons: list[gtk.Button] = []

        self.children = (
            self.header_box,
            self.body_box,
            self.actions_box
        )
        for child in self.children:
            if child:
                self.append(child)

        self.handler_id = item.watch("changed", self.update_values)
        self.update_values()

    def get_detected_category(
        self
    ) -> t.Literal["critical", "messages"] | None:
        if self._cached_detected is not None:
            return self._cached_detected

        if self.item.urgency == NotificationUrgency.CRITICAL:
            self._cached_detected = "critical"
            return "critical"

        category = self.item.hints.get("category")
        if category is not None:
            if any(category.startswith(prefix) for prefix in message_prefixes):
                self._cached_detected = "messages"
                return "messages"

        if any(m in self.item.app_name.lower() for m in messengers):
            self._cached_detected = "messages"
            return "messages"

        return None

    def on_action(self, action: str) -> None:
        self.item.action(action)
        if not self.item.hints.get("resident"):
            self.item.close(NotificationClosedReason.DISMISSED_BY_USER)

    def on_close(self, *args: t.Any) -> None:
        self.item.close(NotificationClosedReason.DISMISSED_BY_USER)

    def on_dismiss(self, *args: t.Any) -> None:
        if self.dismiss:
            self.item.dismiss()

    def update_values(self, *args: t.Any) -> None:
        hide_content = (
            self.hide_content and get_is_sensitive(self)
        )

        settings = Settings()
        self.app_title.set_label(self.item.app_name)

        _datetime = datetime.datetime.now()
        self.time.set_label(
            get_formatted_time(
                _datetime,
                settings.get("time_format") == "12"
            )
        )
        toggle_css_class(self, "critical", self.item.urgency == 2)

        app_icon = self.item.get_app_icon()
        display = gdk.Display.get_default()
        icon_theme = gtk.IconTheme.get_for_display(display)
        if app_icon:
            if isinstance(app_icon, str) and icon_theme.has_icon(app_icon):
                texture = icon_theme.lookup_icon(
                    app_icon, None, 24, 1,
                    gtk.TextDirection.LTR,
                    gtk.IconLookupFlags.FORCE_SYMBOLIC
                )
                if texture:
                    self.app_icon.set_from_paintable(texture)
            elif isinstance(app_icon, gio.Icon):
                texture = icon_theme.lookup_by_gicon(
                    app_icon, 24, 1,
                    gtk.TextDirection.LTR,
                    gtk.IconLookupFlags.FORCE_SYMBOLIC
                )
                if texture:
                    self.app_icon.set_from_paintable(texture)

        self.body_box.set_visible(not hide_content)
        self.actions_box.set_visible(not hide_content)
        if hide_content:
            return

        actions = self.item.actions
        for button in self.action_buttons:
            self.actions_box.remove(button)
        self.action_buttons.clear()

        if actions:
            for action in actions:
                button = gtk.Button(
                    label=action[1],
                    css_classes=("action", "outlined"),
                    halign=gtk.Align.END
                )
                self.conns[button] = button.connect(
                    "clicked",
                    lambda *args, action=action[0]: self.on_action(action)
                )
                self.actions_box.append(button)
                self.action_buttons.append(button)

        icon = self.item.get_icon()
        if isinstance(icon, str):
            texture = icon_theme.lookup_icon(
                icon, None, 64, 1,
                gtk.TextDirection.LTR,
                gtk.IconLookupFlags.FORCE_SYMBOLIC
            )
            self.image.set_from_paintable(texture)
        elif icon:
            self.image.set_from_pixbuf(icon)
            self.image.set_visible(True)
        else:
            self.image.set_visible(False)
            self.image.set_size_request(0, 0)

        self.title.set_label(self.item.summary)
        self.body_text.set_label(self.item.body)
        self.body_text.set_visible(self.item.body != "")
        self.title.set_visible(self.item.summary != "")

    def destroy(self) -> None:
        if self.is_destroyed:
            return
        self.is_destroyed = True
        self.item.unwatch(self.handler_id)
        for _widget, conn in self.conns.items():
            _widget.disconnect(conn)
        for child in self.children:
            self.remove(child)


class NotificationRevealer(gtk.Box):
    def __init__(
        self,
        item: NotificationItem,
        transition_duration: int = 250
    ) -> None:
        self.is_destroyed = False
        self.duration = transition_duration
        self.item = item
        self.first_revealer = gtk.Revealer(
            css_classes=("notification-revealer",),
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN,
            transition_duration=transition_duration,
            reveal_child=True,
            hexpand=True,
            vexpand=True
        )
        self.second_revealer = gtk.Revealer(
            css_classes=("notification-revealer",),
            transition_type=gtk.RevealerTransitionType.SLIDE_LEFT,
            transition_duration=transition_duration,
            reveal_child=False,
            hexpand=True,
            vexpand=True
        )

        self.first_revealer.set_child(self.second_revealer)
        self.second_revealer.set_child(item)

        self.destroy_lock = False

        super().__init__(
            css_classes=("notification-revealer-box",),
            valign=gtk.Align.START
        )
        self.append(self.first_revealer)

    def show(self) -> None:
        self.second_revealer.set_reveal_child(True)
        self.first_revealer.set_reveal_child(True)

    def destroy_with_anim_finish(
        self,
        on_finish: t.Callable[[int], None]
    ) -> None:
        self.first_revealer.set_reveal_child(False)
        glib.timeout_add(
            self.duration + 5,
            lambda: on_finish(self.item.item.id)
        )

    def destroy_with_anim(
        self,
        on_finish: t.Callable[[int], None]
    ) -> None:
        if self.destroy_lock:
            return
        self.destroy_lock = True

        self.second_revealer.set_reveal_child(False)
        glib.timeout_add(
            self.duration + 5,
            lambda: self.destroy_with_anim_finish(on_finish)
        )

    def self_destroy(self) -> None:
        self.item.destroy()
        if self.is_destroyed:
            return
        self.is_destroyed = True
        self.first_revealer.set_child(None)
        self.second_revealer.set_child(None)
        self.remove(self.first_revealer)
