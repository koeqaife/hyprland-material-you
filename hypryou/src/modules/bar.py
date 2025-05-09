import subprocess
from dataclasses import dataclass

import cairo
from utils import widget, Ref, downloader
from utils import toggle_css_class, escape_markup
from utils.logger import logger
from src.variables.clock import date, time
from src.variables import Globals
from repository import gtk, gdk, pango
from src.services import hyprland
from src.services.hyprland import active_workspace, workspace_ids
from src.services.hyprland import active_layout, show_layout
from utils import format
import asyncio
from time import perf_counter
import typing as t
from config import Settings
from src.services.mpris import MprisPlayer, current_player
from src.services.events import Event
import weakref
from src.services.network import get_network


dummy_region = cairo.Region()


class WorkspaceButton(gtk.Button):
    def __init__(self, id: int) -> None:
        super().__init__(
            css_classes=("workspace",),
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER,
            label=str(id)
        )

        self.id = id

        self.connected = self.connect("clicked", self.on_clicked)

    def on_clicked(self, *args: t.Any) -> None:
        asyncio.create_task(hyprland.client.dispatch(f"workspace {self.id}"))

    def destroy(self) -> None:
        self.disconnect(self.connected)


class Workspaces(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("workspaces",),
            valign=gtk.Align.CENTER
        )

        self._old_active = 0

        self.buttons: list[WorkspaceButton] = [
            WorkspaceButton(workspace + 1) for workspace in range(10)
        ]

        for button in self.buttons:
            self.append(button)

        self.update_active(active_workspace.value)
        self.update_empty(workspace_ids.value)

        self.ref_handlers: dict[Ref[t.Any], int] = {
            active_workspace: active_workspace.watch(self.update_active),
            workspace_ids: workspace_ids.watch(self.update_empty)
        }

        self._last_scroll = 0.0
        self._scroll = gtk.EventControllerScroll.new(
            gtk.EventControllerScrollFlags.VERTICAL
        )
        self._scroll_connection = self._scroll.connect(
            "scroll", self.on_scroll
        )
        self.add_controller(self._scroll)

    def destroy(self) -> None:
        for button in self.buttons:
            button.destroy()
            self.remove(button)
        self.buttons.clear()

        self._scroll.disconnect(self._scroll_connection)
        self.remove_controller(self._scroll)
        self._scroll = None  # type: ignore
        for ref, handler_id in self.ref_handlers.items():
            ref.unwatch(handler_id)

    def on_scroll(
        self,
        controller: gtk.EventControllerScroll,
        dx: float,
        dy: float
    ) -> None:
        now = perf_counter()
        if self._last_scroll < now - 0.25:
            self._last_scroll = now
            action = "+1" if dy < 0 else "-1"
            asyncio.create_task(
                hyprland.client.dispatch(f"workspace {action}")
            )

    def update_active(
        self,
        new_value: int
    ) -> None:
        if not new_value:
            return
        if self._old_active == new_value:
            return
        if self._old_active:
            toggle_css_class(self.buttons[self._old_active-1], "active", False)
        if new_value > 10:
            return
        toggle_css_class(self.buttons[new_value-1], "active", True)
        self._old_active = new_value

    def update_empty(
        self,
        not_empty: set[int]
    ) -> None:
        for button in self.buttons:
            toggle_css_class(button, "empty", button.id not in not_empty)


class Clock(gtk.Label):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("clock", "bar-applet"),
            label=time.value,
            tooltip_text=date.value
        )

        self.ref_handlers = {
            time: time.watch(self.update_time),
            date: date.watch(self.update_date)
        }

    def update_time(self, new: str) -> None:
        self.set_label(new)

    def update_date(self, new: str) -> None:
        self.set_tooltip_text(new)

    def destroy(self) -> None:
        for ref, handler_id in self.ref_handlers.items():
            ref.unwatch(handler_id)


@dataclass
class LastChanged:
    artist: str | None = None
    title: str | None = None
    artUrl: str | None = None
    playback_status: str | None = None
    can_go_prev: bool | None = None
    can_go_next: bool | None = None
    can_pause: bool | None = None


class Player(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("mpris-player", "bar-applet"),
            halign=gtk.Align.START,
            valign=gtk.Align.CENTER
        )

        self.player_handlers: dict[MprisPlayer, int] = {}

        image = gtk.Box(
            css_classes=("image",),
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )

        label = gtk.Label(
            ellipsize=pango.EllipsizeMode.END,
            max_width_chars=20,
            halign=gtk.Align.CENTER,
            hexpand=True,
            use_markup=True
        )

        btn_box = gtk.Box(
            css_classes=("buttons",),
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )

        icons = ["skip_previous", "pause", "skip_next"]
        classes = ["previous", "play-pause", "next"]
        handlers = [self.previous, self.play_pause, self.next]

        self.buttons: list[gtk.Button] = []
        self.conns: dict[gtk.Button, int] = {}

        for icon, css_class, handler in zip(icons, classes, handlers):
            btn = gtk.Button(
                child=widget.Icon(icon),
                css_classes=(css_class,)
            )
            btn_box.append(btn)
            self.conns[btn] = btn.connect("clicked", handler)
            self.buttons.append(btn)

        self.children = (
            image,
            label,
            btn_box
        )

        for child in self.children:
            self.append(child)

        self.image_provider = gtk.CssProvider()
        image.get_style_context().add_provider(
            self.image_provider,
            gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.last_changed = LastChanged()
        current_player.watch(self.on_changed)
        self.on_changed()

        self.click_gesture = gtk.GestureClick.new()
        self.click_gesture.set_button(gdk.BUTTON_SECONDARY)
        self.gesture_conn = (
            self.click_gesture.connect("released", self.play_pause)
        )
        self.add_controller(self.click_gesture)

    def next(self, *args: t.Any) -> None:
        current = self.get_player()
        if current:
            current.next()

    def previous(self, *args: t.Any) -> None:
        current = self.get_player()
        if current:
            current.previous()

    def play_pause(self, *args: t.Any) -> None:
        current = self.get_player()
        if current:
            current.play_pause()

    def get_player(self) -> MprisPlayer | None:
        if len(current_player.value) == 2:
            return current_player.value[1]
        else:
            return None

    def update_buttons(self) -> None:
        current = self.get_player()
        if not current:
            self.children[2].set_visible(False)
            self.last_changed.can_go_prev = None
            self.last_changed.can_go_next = None
            self.last_changed.can_pause = None
            self.last_changed.playback_status = None
        else:
            last_changed = self.last_changed

            playback_status = current.playback_status
            can_go_prev = current.can_go_previous
            can_go_next = current.can_go_next
            can_pause = current.can_pause

            if playback_status != last_changed.playback_status:
                icon = self.buttons[1].get_child()
                if isinstance(icon, gtk.Label):
                    icon.set_label(
                        "pause" if playback_status == "Playing"
                        else "play_arrow"
                    )
                    last_changed.playback_status = playback_status

            if can_go_prev != last_changed.can_go_prev:
                self.buttons[0].set_visible(can_go_prev)
                last_changed.can_go_prev = can_go_prev

            if can_go_next != last_changed.can_go_next:
                self.buttons[2].set_visible(can_go_next)
                last_changed.can_go_next = can_go_next

            if can_pause != last_changed.can_pause:
                self.buttons[1].set_visible(can_pause)
                last_changed.can_pause = can_pause

            self.children[2].set_visible(
                can_pause or can_go_next or can_go_prev
            )

    def update_label(self) -> None:
        current = self.get_player()
        if not current:
            text = "Nothing's playing"
            self.last_changed.title = None
            self.last_changed.artist = None
        else:
            metadata = current.metadata

            xesam_artist = metadata.get("xesam:artist")
            artist = xesam_artist[0] if xesam_artist else None
            title = metadata.get("xesam:title")

            if not artist or not title:
                text = "Nothing's playing"
                self.last_changed.title = None
                self.last_changed.artist = None
            else:
                if (
                    artist == self.last_changed.artist
                    and title == self.last_changed.title
                ):
                    return

                self.last_changed.title = title
                self.last_changed.artist = artist

                artist = escape_markup(artist)
                title = escape_markup(title)
                # we show title first cuz length of label is limited
                text = f"{title} <i>- {artist}</i>"
        self.set_tooltip_markup(text)
        self.children[1].set_label(text)

    def on_download(self, filepath: str | None) -> None:
        if not self.children:
            return
        if not filepath:
            self.children[0].set_visible(False)
            return
        css = f"box {{ background-image: url('file://{filepath}'); }}"
        self.image_provider.load_from_data(css)

    def update_image(self) -> None:
        if len(current_player.value) != 2:
            self.children[0].set_visible(False)
            self.last_changed.artUrl = None
        else:
            assert current_player.value
            metadata = current_player.value[1].metadata
            art_url = metadata.get("mpris:artUrl")
            if not art_url or art_url == self.last_changed.artUrl:
                return
            self.children[0].set_visible(True)

            self.last_changed.artUrl = art_url
            downloader.download_image_async(
                art_url, self.on_download, (24, 24), "arts"
            )

    def update_all(self) -> None:
        self.update_image()
        self.update_label()
        self.update_buttons()

    def update_watcher(self) -> None:
        current = self.get_player()
        if not current:
            return

        for player, handler in list(self.player_handlers.items()):
            if player is not current:
                player.unwatch("changed", handler)
                del self.player_handlers[player]

        if current not in self.player_handlers.keys():
            handler_id = current.watch("changed", self.on_changed)
            self.player_handlers[current] = handler_id

    def on_changed(self, *args: t.Any) -> None:
        self.update_watcher()
        self.update_all()

    def destroy(self) -> None:
        for player, handler in self.player_handlers.items():
            player.unwatch("changed", handler)

        for btn in self.buttons:
            btn_child = btn.get_child()
            if isinstance(btn_child, widget.Icon):
                btn_child.destroy()
            btn.set_child(None)
            self.children[2].remove(btn)
        for child in self.children:
            self.remove(child)
        for _widget, conn in self.conns.items():
            _widget.disconnect(conn)

        self.click_gesture.disconnect(self.gesture_conn)
        self.remove_controller(self.click_gesture)

        self.children = None  # type: ignore
        self.buttons = None  # type: ignore
        self.click_gesture = None  # type: ignore
        self.image_provider = None  # type: ignore


class KeyboardLayout(gtk.Label):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("keyboard-layout", "bar-applet")
        )

        self.update_layout(active_layout.value)
        self.set_visible(show_layout.value)

        self.handlers: dict[Ref[t.Any], int] = {
            show_layout: show_layout.watch(self.update_visible),
            active_layout: active_layout.watch(self.update_layout)
        }

    def update_visible(self, new_value: bool) -> None:
        self.set_visible(new_value)

    def update_layout(self, new_layout: str) -> None:
        self.set_label(format.get_layout_tag(new_layout))

    def destroy(self) -> None:
        for ref, handler_id in self.handlers.items():
            ref.unwatch(handler_id)


class Applet(gtk.Button):
    def __init__(
        self,
        name: str,
        icon: str | Ref[str],
        on_click: t.Callable[[], None],
        on_wheel_click: t.Callable[[], None] | None = None
    ) -> None:
        self._icon = widget.Icon(icon)
        super().__init__(
            child=self._icon,
            css_classes=("applet",)
        )

        self.click_gesture = gtk.GestureClick.new()
        self.click_gesture.set_button(0)
        self.gesture_conn = (
            self.click_gesture.connect("released", self.on_click_released)
        )
        self.add_controller(self.click_gesture)

        self.on_click = on_click
        self.on_wheel_click = on_wheel_click

    def on_click_released(
        self,
        gesture: gtk.GestureClick,
        n_press: int,
        x: int,
        y: int
    ) -> None:
        button_number = gesture.get_current_button()
        if button_number == gdk.BUTTON_PRIMARY:
            self.on_click()
        elif button_number == gdk.BUTTON_MIDDLE:
            self.on_wheel_click()

    def destroy(self) -> None:
        self._icon.destroy()
        self.set_child(None)
        self.click_gesture.disconnect(self.gesture_conn)
        self.remove_controller(self.click_gesture)


class Applets(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("applets", "bar-applet")
        )

        self.children = (
            Applet("audio", "volume_up", lambda: None, self.open_pavucontrol),
            Applet("bluetooth", "bluetooth", lambda: None),
            Applet("wifi", get_network().icon, lambda: None),
            Applet("cliphist", "content_paste", lambda: None),
        )
        for child in self.children:
            self.append(child)

    def open_pavucontrol(self) -> None:
        subprocess.Popen(["pavucontrol"])

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
            self.remove(child)


class OpenTray(gtk.Button):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("open-tray", "bar-applet"),
            child=widget.Icon("browse"),
            tooltip_text="System tray"
        )
        self.conn_id = self.connect("clicked", self.on_clicked)

    def on_clicked(self, *args: t.Any) -> None:
        event = Event(None, "tray", "toggle_window")
        Globals.events.notify(event)

    def destroy(self) -> None:
        self.disconnect(self.conn_id)


class OpenSidebar(gtk.Button):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("open-sidebar", "icon-tonal"),
            child=widget.Icon("space_dashboard"),
            tooltip_text="Sidebar",
            halign=gtk.Align.CENTER,
            valign=gtk.Align.CENTER
        )
        self.conn_id = self.connect("clicked", self.on_clicked)

    def on_clicked(self, *args: t.Any) -> None:
        event = Event(None, "sidebar", "toggle_window")
        Globals.events.notify(event)

    def destroy(self) -> None:
        self.disconnect(self.conn_id)


class OpenAppsMenu(gtk.Button):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("open-apps-menu", "icon-tonal"),
            child=widget.Icon("search"),
            tooltip_text="Apps Menu",
            halign=gtk.Align.CENTER,
            valign=gtk.Align.CENTER
        )
        self.conn_id = self.connect("clicked", self.on_clicked)

    def on_clicked(self, *args: t.Any) -> None:
        event = Event(None, "apps_menu", "toggle_window")
        Globals.events.notify(event)

    def destroy(self) -> None:
        self.disconnect(self.conn_id)


class ModulesLeft(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("modules-left",)
        )
        self.children = (
            OpenAppsMenu(),
            Player(),
        )
        for child in self.children:
            self.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
            self.remove(child)


class ModulesCenter(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("modules-center",)
        )
        self.children = (
            Workspaces(),
        )
        for child in self.children:
            self.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
            self.remove(child)


class ModulesRight(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("modules-right",)
        )
        self.children = (
            KeyboardLayout(),
            OpenTray(),
            Applets(),
            Clock(),
            OpenSidebar()
        )
        for child in self.children:
            self.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
            self.remove(child)


class Bar(widget.LayerWindow):
    def __init__(self, application: gtk.Application, monitor: gdk.Monitor):
        super().__init__(
            application,
            height=1,
            anchors={
                "top": True,
                "left": True,
                "right": True
            },
            exclusive=True,
            monitor=monitor,
            css_classes=("bar",)
        )

        self.center_box = gtk.CenterBox(
            start_widget=ModulesLeft(),
            center_widget=ModulesCenter(),
            end_widget=ModulesRight()
        )

        self.set_child(self.center_box)
        self.present()
        weakref.finalize(self, lambda: logger.debug("Bar finalized"))

    def destroy(self) -> None:
        box = self.center_box
        t.cast(t.Any, box.get_start_widget()).destroy()
        t.cast(t.Any, box.get_center_widget()).destroy()
        t.cast(t.Any, box.get_end_widget()).destroy()
        box.set_start_widget(None)
        box.set_center_widget(None)
        box.set_end_widget(None)
        self.set_child(None)
        self.close()
        super().destroy()


class Corner:
    def __init__(
        self,
        application: gtk.Application,
        monitor: gdk.Monitor,
        position: t.Literal["left", "right"]
    ) -> None:
        self.position = position
        self.settings = Settings()
        self.application = application
        self.monitor = monitor

        self.window: widget.LayerWindow | None = None
        self.corner: widget.RoundedCorner | None = None

        self.settings.watch("corners", self.update_visible, True)

    def create_window(self) -> None:
        is_on_left = self.position == "left"

        self.window = widget.LayerWindow(
            application=self.application,
            monitor=self.monitor,
            anchors={
                "top": True,
                "left": is_on_left,
                "right": not is_on_left
            },
            css_classes=("transparent",)
        )

        self.corner = widget.RoundedCorner(
            f"top-{self.position}"
        )
        self.window.set_child(self.corner)

        self.application.add_window(self.window)

        self.window.present()
        surface = self.window.get_surface()
        if surface:
            surface.set_input_region(dummy_region)  # type: ignore[arg-type]

    def destroy_window(self) -> None:
        if self.window:
            self.window.destroy()
            self.window = None
        if self.corner:
            self.corner = None

    def update_visible(self, value: bool) -> None:
        if value:
            self.create_window()
        else:
            self.destroy_window()
