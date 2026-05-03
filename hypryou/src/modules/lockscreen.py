from repository import session_lock, gtk, gdk, glib
from utils.logger import logger
from utils.styles import toggle_css_class
from utils.ref import Ref
from src.services.clock import time, full_date
from src.services.hyprland import active_layout, show_layout
from src.services.mpris import current_player, MprisPlayer
from src.services.upower import get_upower
from src.services.state import is_idle_locked
from src.services.state import is_locked, current_wallpaper
from src.services.notifications import notifications
from src.modules.notifications.list import Notifications
from src.modules.players import Player
from src import widget
from config import Settings
import pwd
import os
from time import monotonic
import weakref
import threading
import typing as t

username = pwd.getpwuid(os.getuid()).pw_name
close_player = Ref(False, name="lock_close_player")
blocked_input = Ref(False, name="lock_blocked_input")


def check_password(username: str, password: str) -> bool:
    from pam import pam  # type: ignore [import-untyped]
    p = pam()
    return bool(p.authenticate(username, password))


class ScreenLockWindow(gtk.ApplicationWindow):
    __gtype_name__ = "ScreenLockWindow"

    def __init__(
        self,
        app: gtk.Application
    ) -> None:
        if close_player.value:
            close_player.value = False
        super().__init__(
            application=app,
            css_classes=("lock-screen", "faded-out"),
            name="lock",
            default_height=800,
            default_width=1200
        )

        self.settings = Settings().get_view_for("lockscreen")
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
            css_classes=("lock-wallpaper",),
            content_fit=gtk.ContentFit.COVER
        )
        if isinstance(current_wallpaper.value, gdk.Texture):
            self.wallpaper.set_paintable(current_wallpaper.value)
        else:
            self.wallpaper.set_pixbuf(current_wallpaper.value)
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

        self.notification_count: int = -1
        if self.settings.get("notifications_counter"):
            self.notif_box = gtk.Box(
                css_classes=("lock-notif-box",),
                visible=False
            )
            self.notif_icon = widget.Icon(
                "notifications",
                css_classes=("notif-icon",)
            )
            self.notif_counter = gtk.Label(
                css_classes=("notif-label",),
                label="0 new notifications"
            )
            self.notif_box.append(self.notif_icon)
            self.notif_box.append(self.notif_counter)
            self.info_box.append(self.notif_box)

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

        self.notifications: Notifications | None = None
        if self.settings.get("notifications") != 3:
            hide_content = self.settings.get("notifications") == 1
            hide_all = self.settings.get("notifications") == 2
            self.notifications = Notifications(
                hide_content, False, hide_all=hide_all
            )
            self.notifications.unfreeze()
            self.box.append(self.notifications)

        self.overlay.add_overlay(self.dim)
        self.overlay.add_overlay(self.box)
        self.overlay.add_overlay(self.info_box)
        self.overlay.add_overlay(self.unlock_box)
        self.set_child(self.overlay)
        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("LockScreenWindow finalized")
            )

        self.ref_handlers: dict[Ref[t.Any], int] = {
            time: time.watch(self.update_time),
            full_date: full_date.watch(self.update_date),
            active_layout: active_layout.watch(self.update_layout),
            show_layout: show_layout.watch(self.update_layout),
            current_player: current_player.watch(self.update_current_player),
            close_player: close_player.watch(self.update_current_player),
            notifications: notifications.watch(self._notifications_changed)
        }

        self.battery_handler = get_upower().watch(
            "changed", self.update_battery
        )
        self.update_battery()
        self.update_current_player()
        self.update_expanded()
        self.map_handler = self.connect("map", self._on_map)
        self.change_icon_timeout: int | None = None
        if is_idle_locked.value:
            self.change_icon_timeout = glib.timeout_add(
                5000, self.change_button_icon
            )
        else:
            self.change_button_icon()

        self.unlock_btn.grab_focus()
        self._notifications_changed(notifications.value)

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
        if self.settings.get("always_reveal_input"):
            self.reveal_input(True)

    def close_player(self) -> None:
        if self.mpris_player is None:
            return
        self.mpris_player.pause()
        close_player.value = True

    def _on_map(self, *args: t.Any) -> None:
        glib.idle_add(lambda: self.remove_css_class("faded-out"))

    def fade_out_and_destroy(
        self,
        on_done: t.Callable[[], None] | None = None
    ) -> None:
        self.add_css_class("faded-out")

        def _on_done() -> bool:
            self.destroy()
            if on_done:
                on_done()
            return False

        glib.timeout_add(320, _on_done)

    def on_key_pressed(
        self,
        controller: gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: gdk.ModifierType
    ) -> bool:
        if keyval == gdk.KEY_Escape:
            if self.settings.get("always_reveal_input"):
                self.unlock_entry.set_text("")
            else:
                root = self.get_root()
                if isinstance(root, gtk.Root):
                    root.set_focus(None)
            return True
        return False

    def on_text_changed(self, *args: t.Any) -> None:
        toggle_css_class(self.unlock_box, "invalid", False)
    def _trigger_unlock(self) -> bool:
        is_locked.value = False
        return False
    def on_entry_activate(self, *args: t.Any) -> None:
        if blocked_input.value:
            return
        password = self.unlock_entry.get_text()

        self.unlock_entry.set_editable(False)
        def authenticate_and_continue() -> None:
            blocked_input.value = True
            is_correct = check_password(username, password)
            def on_done() -> None:
                blocked_input.value = False
                self.unlock_entry.set_editable(True)
                if is_correct:
                    glib.idle_add(self._trigger_unlock)
                else:
                    toggle_css_class(self.unlock_box, "invalid", True)
            glib.idle_add(on_done)

        threading.Thread(target=authenticate_and_continue, daemon=True).start()
    def reveal_input(self, reveal: bool) -> None:
        self.btn_revealer.set_reveal_child(not reveal)
        self.entry_revealer.set_reveal_child(reveal)
        toggle_css_class(self.unlock_box, "activated", reveal)

    def entry_focus_leave(self, *args: t.Any) -> None:
        if self.settings.get("always_reveal_input"):
            self.reveal_input(True)
        else:
            self.reveal_input(False)

    def on_unlock_button_clicked(self, *args: t.Any) -> None:
        if monotonic() - self.showed_on < 5 and is_idle_locked.value:
            is_locked.value = False
            return
        self.reveal_input(True)

    def update_expanded(self) -> None:
        self.change_expanded(
            self.notifications_visible or
            self.player_widget is not None
        )

    def _notifications_changed(self, value: dict[t.Any, t.Any]) -> None:
        length = len(value)
        if self.settings.get("notifications_counter"):
            if (
                self.notification_count > length
                or self.notification_count == -1
            ):
                self.notification_count = length
            new = length - self.notification_count
            self.notif_counter.set_label(
                f"{new} new notification{"s" if new != 1 else ""}"
            )
            self.notif_box.set_visible(new != 0)
        self.notifications_visible = length > 0 and self.notifications
        self.update_expanded()

    def _mpris_timer(self) -> bool | None:
        if self.player_widget:
            self.player_widget.update_slider_position()
            return True
        self.mpris_timer = None
        return None

    def update_current_player(self, *args: t.Any) -> None:
        if not self.settings.get("media"):
            return
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
        if self.notifications:
            self.notifications.set_visible(self.expanded)
        if self.player_widget:
            self.player_widget.set_visible(self.expanded)

    def update_date(self, new_date: str) -> None:
        self.date.set_label(new_date)

    def update_time(self, *args: t.Any) -> None:
        if self.expanded:
            self.time.set_label(time.value)
        else:
            hours, minutes = time.value.split()[0].split(":")
            self.time.set_label(f"{int(hours):02d}\n{int(minutes):02d}")

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
            self.player_widget = None
        if self.change_icon_timeout:
            glib.source_remove(self.change_icon_timeout)
        if self.notifications:
            self.box.remove(self.notifications)
            self.notifications.destroy()
            self.notifications = None
        self.disconnect(self.map_handler)
        super().destroy()


class ScreenLockPlayer(Player):
    __gtype_name__ = "ScreenLockPlayer"

    def __init__(
        self,
        item: MprisPlayer,
        on_close: t.Callable[[], None]
    ) -> None:
        super().__init__(item)
        self.text_box.remove(self.title)
        self.title.set_max_width_chars(37)
        self.artists.set_max_width_chars(37)
        self.title_box = gtk.Box(
            css_classes=("lock-title-box",)
        )
        self.close_button = gtk.Button(
            css_classes=("lock-player-close", "icon-tonal"),
            child=widget.Icon("close"),
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )
        self.title_box.append(self.title)
        self.title_box.append(self.close_button)
        self.text_box.insert_child_after(self.title_box, None)

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


class ScreenLock:
    @classmethod
    def register(cls, app: gtk.Application) -> "ScreenLock":
        return cls(app)

    def __init__(self, app: gtk.Application) -> None:
        self.settings = Settings().get_view_for("lockscreen")
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
        lockscreen_app = self.settings.get("application")
        
        # 1. Xử lý Lockscreen ngoại vi (hyprlock, etc.)
        if lockscreen_app != "Default":
            import subprocess
            try:
                # Dùng run để tránh zombie, check=True để bắt lỗi nếu app không tồn tại
                subprocess.run([lockscreen_app], check=True)
                # Sau khi lockscreen ngoại vi kết thúc, ta coi như đã unlock
                is_locked.value = False 
                return
            except subprocess.CalledProcessError as e:
                logger.error(f"External lockscreen exited with error: {e}")
            except Exception as e:
                logger.error(f"Failed to launch {lockscreen_app}: {e}")
                # Nếu lỗi thì rơi xuống (fall back) dùng lockscreen mặc định bên dưới
        
        # 2. Default HyprYou lockscreen behavior
        if not self.lock_instance.lock():
            logger.warning("Failed to acquire session lock.")
            return

        display: gdk.Display = gdk.Display.get_default()
        blocked_input.value = False
        
        # Clear windows cũ nếu còn sót (safety check)
        self.windows.clear()

        for monitor in display.get_monitors():
            window = ScreenLockWindow(self.app)
            self.windows[t.cast(gdk.Monitor, monitor)] = window
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
        blocked_input.value = False

        for window in windows:
            # 1. Ngắt tất cả các Ref watch ngay lập tức để tránh gọi hàm update khi đang xóa
            for ref, handler_id in window.ref_handlers.items():
                ref.unwatch(handler_id)
            window.ref_handlers.clear()
            
            # 2. Dừng các timer
            if window.mpris_timer:
                glib.source_remove(window.mpris_timer)
                window.mpris_timer = None
                
            # 3. Sau đó mới chạy animation
            window.fade_out_and_destroy(on_done=on_window_done)

    def on_locked(self, lock_instance: session_lock.Instance) -> None:
        pass

    def on_unlocked(self, lock_instance: session_lock.Instance) -> None:
        is_idle_locked.value = False

    def on_failed(self, lock_instance: session_lock.Instance) -> None:
        pass
