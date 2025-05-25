from src.services.state import is_locked, current_wallpaper
from repository import session_lock, gtk, gdk, glib
import typing as t
import weakref
from utils.logger import logger
from utils import widget, toggle_css_class, Ref
from src.variables.clock import time, full_date
from src.services.hyprland import active_layout, show_layout
from src.modules.players import Player
from src.services.mpris import current_player, MprisPlayer
from src.services.upower import get_upower
from src.modules.notifications.list import Notifications
import pwd
import os
from pam import pam
from time import monotonic

username = pwd.getpwuid(os.getuid()).pw_name
close_player = Ref(False, name="lock_close_player")


def check_password(username: str, password: str) -> bool:
    p = pam()
    return p.authenticate(username, password)


class ScreenLockWindow(gtk.ApplicationWindow):
    def __init__(
        self,
        app: gtk.Application
    ) -> None:
        if close_player.value:
            close_player.value = False
        super().__init__(
            application=app,
            css_classes=("lock-screen",),
            name="lock",
            default_height=800,
            default_width=1200
        )

        self.expanded = False
        self.mpris_player: MprisPlayer | None = None
        self.player_widget: ScreenLockPlayer | None = None
        self.mpris_timer: int | None = None
        self.notifications_visible = False
        self.showed_on = monotonic()

        self.dim = gtk.Box(
            css_classes=("lock-screen-dim",),
            hexpand=True,
            vexpand=True
        )
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            css_classes=("lock-screen-box",),
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )

        self.wallpaper = gtk.Picture(
            paintable=current_wallpaper.value,
            css_classes=("lock-wallpaper",),
            content_fit=gtk.ContentFit.COVER
        )
        self.overlay = gtk.Overlay(
            child=self.wallpaper,
            css_classes=("lock-overlay",)
        )
        self.time = gtk.Label(
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER,
            css_classes=("lock-time",)
        )
        self.box.append(self.time)

        self.info_box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            css_classes=("lock-info-box",),
            halign=gtk.Align.START,
            valign=gtk.Align.START
        )

        self.date_box = gtk.Box(
            css_classes=("lock-date-box",)
        )
        self.date_icon = widget.Icon(
            "calendar_today",
            css_classes=("date-icon",)
        )
        self.date = gtk.Label(
            css_classes=("date-label",),
            label=full_date.value
        )
        self.date_box.append(self.date_icon)
        self.date_box.append(self.date)
        self.info_box.append(self.date_box)

        self.layout_box = gtk.Box(
            css_classes=("lock-layout-box",),
            visible=show_layout.value
        )
        self.layout_icon = widget.Icon(
            "keyboard",
            css_classes=("layout-icon",)
        )
        self.layout = gtk.Label(
            css_classes=("layout-label",),
            label=active_layout.value
        )
        self.layout_box.append(self.layout_icon)
        self.layout_box.append(self.layout)
        self.info_box.append(self.layout_box)

        self.battery_box = gtk.Box(
            css_classes=("lock-battery-box",),
            visible=False
        )
        self.battery_icon = widget.Icon(
            get_upower().battery_icon,
            css_classes=("battery-icon",)
        )
        self.battery = gtk.Label(
            css_classes=("battery-label",),
            label="0%"
        )
        self.battery_box.append(self.battery_icon)
        self.battery_box.append(self.battery)
        self.info_box.append(self.battery_box)

        self.unlock_box = gtk.Box(
            css_classes=("lock-unlock-box",),
            orientation=gtk.Orientation.HORIZONTAL,
            valign=gtk.Align.END,
            halign=gtk.Align.CENTER
        )
        self.unlock_btn_box = gtk.Box(
            css_classes=("unlock-button-box",)
        )
        self.unlock_btn_icon = widget.Icon(
            "lock_open"
        )
        self.unlock_btn_label = gtk.Label(
            label="Unlock"
        )
        self.unlock_btn_box.append(self.unlock_btn_icon)
        self.unlock_btn_box.append(self.unlock_btn_label)
        self.unlock_btn = gtk.Button(
            css_classes=("unlock-button", "filled"),
            child=self.unlock_btn_box
        )
        self.unlock_entry = gtk.Entry(
            css_classes=("lock-entry",),
            placeholder_text="Password",
            visibility=False
        )
        self.unlock_entry.set_focusable(True)
        self.btn_revealer = gtk.Revealer(
            child=self.unlock_btn,
            reveal_child=True,
            transition_type=gtk.RevealerTransitionType.SLIDE_LEFT,
            transition_duration=250
        )
        self.entry_revealer = gtk.Revealer(
            child=self.unlock_entry,
            reveal_child=False,
            transition_type=gtk.RevealerTransitionType.SLIDE_RIGHT,
            transition_duration=250
        )
        self.unblock_btn_handler = self.unlock_btn.connect(
            "clicked", self.on_unlock_button_clicked
        )
        self.entry_handlers = (
            self.unlock_entry.connect(
                "activate", self.on_entry_activate
            ),
            self.unlock_entry.connect(
                "notify::text", self.on_text_changed
            ),
        )
        self.entry_focus_controller = gtk.EventControllerFocus()
        self.entry_focus_handler = self.entry_focus_controller.connect(
            "leave", self.entry_focus_leave
        )
        self.unlock_entry.add_controller(self.entry_focus_controller)
        self.entry_key_controller = gtk.EventControllerKey.new()
        self.entry_key_handler = self.entry_key_controller.connect(
            "key-pressed", self.on_key_pressed
        )
        self.unlock_entry.add_controller(self.entry_key_controller)
        self.unlock_box.append(self.btn_revealer)
        self.unlock_box.append(self.entry_revealer)

        self.notifications = ScreenLockNotifications(self)
        self.notifications.unfreeze()
        self.box.append(self.notifications)

        self.overlay.add_overlay(self.dim)
        self.overlay.add_overlay(self.box)
        self.overlay.add_overlay(self.info_box)
        self.overlay.add_overlay(self.unlock_box)
        self.set_child(self.overlay)
        weakref.finalize(
            self, lambda: logger.debug("LockScreenWindow finalized")
        )

        self.ref_handlers: dict[Ref[t.Any], int] = {
            time: time.watch(self.update_time),
            full_date: full_date.watch(self.update_date),
            active_layout: active_layout.watch(self.update_layout),
            show_layout: show_layout.watch(self.update_layout),
            current_player: current_player.watch(self.update_current_player),
            close_player: close_player.watch(self.update_current_player)
        }
        self.battery_handler = get_upower().watch(
            "changed", self.update_battery
        )
        self.update_battery()
        self.update_current_player()
        self.update_expanded()
        self.map_handler = self.connect("map", self._on_map)
        self.change_icon_timeout: int | None = glib.timeout_add(
            5000, self.change_button_icon
        )

    def update_battery(self, *args: t.Any) -> None:
        upower = get_upower()

        is_battery_connected = upower.is_battery and upower.is_present
        if not is_battery_connected:
            self.battery_box.set_visible(False)
            return
        else:
            self.battery_box.set_visible(True)

        self.battery.set_label(f"{round(upower.percentage)}%")

    def change_button_icon(self) -> None:
        self.change_icon_timeout = None
        self.unlock_btn_icon.set_label("lock")

    def close_player(self) -> None:
        if self.mpris_player is None:
            return
        self.mpris_player.pause()
        close_player.value = True

    def _on_map(self, *args: t.Any) -> None:
        self.set_opacity(0.01)
        self._fade_in()

    def _fade_in(self) -> None:
        step: float = 0.05

        def _tick() -> bool:
            current: float = self.get_opacity() or 0.0
            new: float = current + step
            if new < 1.0:
                self.set_opacity(new)
                return True
            self.set_opacity(1.0)
            self.disconnect(self.map_handler)
            return False

        glib.timeout_add(15, _tick)

    def fade_out_and_destroy(
        self,
        on_done: t.Callable[[], None] | None = None
    ) -> None:
        step: float = 0.05

        def _tick() -> bool:
            current: float = self.get_opacity() or 1.0
            new: float = current - step
            if new > 0.01:
                self.set_opacity(new)
                return True
            self.set_opacity(0.01)
            if on_done:
                on_done()
            self.destroy()
            return False

        glib.timeout_add(15, _tick)

    def on_key_pressed(
        self,
        controller: gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: gdk.ModifierType
    ) -> bool:
        if keyval == gdk.KEY_Escape:
            root = self.get_root()
            if isinstance(root, gtk.Root):
                root.set_focus(None)
            return True
        return False

    def on_text_changed(self, *args: t.Any) -> None:
        toggle_css_class(self.unlock_box, "invalid", False)

    def on_entry_activate(self, *args: t.Any) -> None:
        is_correct = check_password(username, self.unlock_entry.get_text())
        if is_correct:
            is_locked.value = False
        else:
            toggle_css_class(self.unlock_box, "invalid", True)

    def entry_focus_leave(self, *args: t.Any) -> None:
        self.btn_revealer.set_reveal_child(True)
        self.entry_revealer.set_reveal_child(False)
        toggle_css_class(self.unlock_box, "activated", False)

    def on_unlock_button_clicked(self, *args: t.Any) -> None:
        if monotonic() - self.showed_on < 5:
            is_locked.value = False
            return
        self.btn_revealer.set_reveal_child(False)
        self.entry_revealer.set_reveal_child(True)
        toggle_css_class(self.unlock_box, "activated", True)

    def update_expanded(self) -> None:
        self.change_expanded(
            self.notifications_visible or
            self.player_widget is not None
        )

    def _notifications_changed(self, is_not_empty: bool) -> None:
        self.notifications_visible = is_not_empty
        self.update_expanded()

    def _mpris_timer(self) -> None:
        if self.player_widget:
            self.player_widget.update_slider_position()
            return True
        self.mpris_timer = None

    def update_current_player(self, *args: t.Any) -> None:
        current = current_player.value[1] if current_player.value else None
        if current == self.mpris_player and not close_player.value:
            return

        if self.player_widget:
            self.player_widget.destroy()
            self.box.remove(self.player_widget)

        if (
            current is None
            or current.playback_status != "Playing"
            or close_player.value
        ):
            self.player_widget = None
            self.mpris_player = None
            if self.mpris_timer:
                glib.source_remove(self.mpris_timer)
                self.mpris_timer = None
            self.update_expanded()
            return

        self.mpris_player = current
        self.player_widget = ScreenLockPlayer(current, self.close_player)
        self.player_widget.set_visible(self.expanded)
        # Used 1s instead of 500ms for optimization
        if not self.mpris_timer:
            self.mpris_timer = glib.timeout_add(1000, self._mpris_timer)

        self.box.insert_child_after(self.player_widget, self.time)
        self.update_expanded()

    def update_layout(self, *args: t.Any) -> None:
        if show_layout.value:
            self.layout.set_label(active_layout.value)
            self.layout_box.set_visible(True)
        else:
            self.layout_box.set_visible(False)

    def change_expanded(self, new_value: bool) -> None:
        self.expanded = new_value
        toggle_css_class(self, "is-expanded", new_value)
        self.update_time()
        if self.expanded:
            self.box.set_valign(gtk.Align.FILL)
            self.box.set_vexpand(True)
        else:
            self.box.set_valign(gtk.Align.CENTER)
            self.box.set_vexpand(False)
        self.notifications.set_visible(self.expanded)
        if self.player_widget:
            self.player_widget.set_visible(self.expanded)

    def update_date(self, new_date: str) -> None:
        self.date.set_label(new_date)

    def update_time(self, *args: t.Any) -> None:
        if self.expanded:
            self.time.set_label(time.value)
        else:
            self.time.set_label("\n".join(time.value.split(":")))

    def destroy(self) -> None:
        self.unlock_btn.disconnect(self.unblock_btn_handler)
        for handler_id in self.entry_handlers:
            self.unlock_entry.disconnect(handler_id)
        self.unlock_entry.remove_controller(self.entry_focus_controller)
        self.entry_focus_controller.disconnect(self.entry_focus_handler)
        self.unlock_entry.remove_controller(self.entry_key_controller)
        self.entry_key_controller.disconnect(self.entry_key_handler)
        for ref, handler_id in self.ref_handlers.items():
            ref.unwatch(handler_id)
        if self.mpris_timer:
            glib.source_remove(self.mpris_timer)
        if self.player_widget:
            self.box.remove(self.player_widget)
            self.player_widget.destroy()
            self.player_widget = None  # type: ignore
        if self.change_icon_timeout:
            glib.source_remove(self.change_icon_timeout)
        self.box.remove(self.notifications)
        self.notifications.destroy()
        self.notifications = None  # type: ignore
        super().destroy()


class ScreenLockPlayer(Player):
    def __init__(
        self,
        item: MprisPlayer,
        on_close: t.Callable[[], None]
    ) -> None:
        super().__init__(item)
        self.text_box.remove(self.player)
        self.player_box = gtk.Box(
            css_classes=("lock-player-box",),
            halign=gtk.Align.END
        )
        self.close_button = gtk.Button(
            css_classes=("lock-player-close", "icon-tonal"),
            child=widget.Icon("close")
        )
        self.player_box.append(self.player)
        self.player_box.append(self.close_button)
        self.text_box.insert_child_after(self.player_box, None)

        self._close_handler = self.close_button.connect(
            "clicked", self._on_close_clicked
        )
        self._on_close = weakref.WeakMethod(on_close)

    def _on_close_clicked(self, *args: t.Any) -> None:
        callback = self._on_close()
        if callback is not None:
            callback()

    def destroy(self) -> None:
        self.close_button.disconnect(self._close_handler)
        super().destroy()


class ScreenLockNotifications(Notifications):
    def __init__(self, window: ScreenLockWindow) -> None:
        self.window = window
        super().__init__(True, False)

    def update_no_notifications(self) -> None:
        self.window._notifications_changed(len(self.items) > 0)


class ScreenLock:
    def __init__(self, app: gtk.Application) -> None:
        self.app = app
        self.lock_instance = session_lock.Instance.new()
        self.lock_instance.connect("locked", self.on_locked)
        self.lock_instance.connect("unlocked", self.on_unlocked)
        self.lock_instance.connect("failed", self.on_failed)

        self.windows: dict[gdk.Monitor, ScreenLockWindow] = {}
        is_locked.watch(self.on_is_locked)

    def on_is_locked(self, new_value: bool) -> None:
        locked = self.lock_instance.is_locked()

        if new_value != locked:
            if new_value:
                self.lock()
            else:
                self.unlock()

    def lock(self) -> None:
        if not self.lock_instance.lock():
            return

        display = t.cast(gdk.Display, gdk.Display.get_default())
        for monitor in display.get_monitors():
            window = ScreenLockWindow(self.app)
            self.windows[monitor] = window
            self.lock_instance.assign_window_to_monitor(window, monitor)
            window.present()

    def unlock(self, *args: t.Any) -> None:
        windows = list(self.windows.values())

        if not windows:
            self.lock_instance.unlock()
            return

        remaining = len(windows)

        def on_window_done() -> None:
            nonlocal remaining
            remaining -= 1
            if remaining == 0:
                self.windows.clear()
                self.lock_instance.unlock()

        for window in windows:
            window.fade_out_and_destroy(on_done=on_window_done)

    def on_locked(self, lock_instance: session_lock.Instance) -> None:
        pass

    def on_unlocked(self, lock_instance: session_lock.Instance) -> None:
        pass

    def on_failed(self, lock_instance: session_lock.Instance) -> None:
        pass
