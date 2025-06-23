from dataclasses import dataclass
from utils import downloader, toggle_css_class, Ref, sync_debounce
from utils import format_seconds
from utils.service import Signals
from utils.logger import logger
from repository import gtk, layer_shell, pango, glib, gobject
from src.services.mpris import players, MprisPlayer, current_player
from config import HyprlandVars
import weakref
import typing as t
from src import widget

type HandlersDict = dict[
    tuple[Signals, str] | Ref[t.Any] | gobject.Object, int
]


@dataclass
class LastChanged:
    artists: list[str] | None = None
    title: str | None = None
    art_url: str | None = None
    playback_status: str | None = None
    can_go_prev: bool | None = None
    can_go_next: bool | None = None
    can_pause: bool | None = None


class Player(gtk.Box):
    __gtype_name__ = "Player"

    def __init__(self, item: MprisPlayer) -> None:
        super().__init__(
            valign=gtk.Align.START,
            hexpand=True,
            css_classes=("mpris-player",),
            orientation=gtk.Orientation.VERTICAL
        )
        self._item = item
        self.info_box = gtk.Box(
            css_classes=("info-box",),
            hexpand=True
        )

        self.image = gtk.Box(
            css_classes=("image",),
            valign=gtk.Align.START
        )
        self.text_box = gtk.Box(
            css_classes=("text-box",),
            orientation=gtk.Orientation.VERTICAL,
            hexpand=True,
            valign=gtk.Align.START
        )

        self.info_box.append(self.image)
        self.info_box.append(self.text_box)

        self.player = gtk.Label(
            css_classes=("player",),
            halign=gtk.Align.END,
            label=item.get_bus_name().split(".")[3].capitalize(),
            tooltip_text=item.get_bus_name()
        )
        self.title = gtk.Label(
            css_classes=("title",),
            ellipsize=pango.EllipsizeMode.END,
            halign=gtk.Align.START,
            valign=gtk.Align.CENTER
        )
        self.artists = gtk.Label(
            css_classes=("artists",),
            ellipsize=pango.EllipsizeMode.END,
            halign=gtk.Align.START,
            valign=gtk.Align.CENTER
        )
        self.text_box.append(self.player)
        self.text_box.append(self.title)
        self.text_box.append(self.artists)

        self.slider = gtk.Scale.new_with_range(
            orientation=gtk.Orientation.HORIZONTAL,
            min=0,
            max=1,
            step=1
        )

        self.current_position = gtk.Label(
            css_classes=("position-label",),
            label="0:00",
            halign=gtk.Align.START,
            hexpand=True
        )
        self.actions = gtk.Box(
            css_classes=("actions",),
            halign=gtk.Align.CENTER
        )
        self.max_position = gtk.Label(
            css_classes=("position-label",),
            label="0:00",
            halign=gtk.Align.END,
            hexpand=True
        )
        self.center_box = gtk.CenterBox(
            css_classes=("extra-box",),
            hexpand=True,
            start_widget=self.current_position,
            center_widget=self.actions,
            end_widget=self.max_position
        )

        icons = ["skip_previous", "pause", "skip_next"]
        classes = ["previous", "play-pause", "next"]
        handlers = [self.previous, self.play_pause, self.next]

        self.buttons: list[gtk.Button] = []

        self.append(self.info_box)
        self.append(self.slider)
        self.append(self.center_box)

        self.last_changed = LastChanged()

        self.image_provider = gtk.CssProvider()
        self.image.get_style_context().add_provider(
            self.image_provider,
            gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._locked_timer = False

        self.handlers: HandlersDict = {
            (item, "changed"): item.watch(
                "changed", self.on_change, priority=1
            ),
            (item, "seeked"): item.watch(
                "seeked", self.update_slider_position, priority=1
            ),
            current_player: current_player.watch(self.on_cur_player_changed),
            self.slider: self.slider.connect("change-value", self.on_seek),
        }

        for icon, css_class, handler in zip(icons, classes, handlers):
            btn = gtk.Button(
                child=widget.Icon(icon),
                css_classes=(css_class,)
            )
            self.actions.append(btn)
            self.handlers[btn] = btn.connect("clicked", handler)
            self.buttons.append(btn)

        self.on_cur_player_changed(current_player.value)
        self.on_change()

    def next(self, *args: t.Any) -> None:
        self._item.next()

    def previous(self, *args: t.Any) -> None:
        self._item.previous()

    def play_pause(self, *args: t.Any) -> None:
        self._item.play_pause()

    def lock_timer(self, *args: t.Any) -> None:
        self._locked_timer = True

    @sync_debounce(500)
    def unlock_timer(self, *args: t.Any) -> None:
        self._locked_timer = False

    def on_seek(self, *args: t.Any) -> None:
        self.lock_timer()
        self.seek()

    @sync_debounce(250)
    def seek(self, *args: t.Any) -> None:
        self._item.set_position(
            self._item.metadata["mpris:trackid"],
            int(self.slider.get_value() * 1_000_000)
        )
        self.unlock_timer()

    def on_cur_player_changed(
        self, new: tuple[bool, MprisPlayer] | tuple[()]
    ) -> None:
        toggle_css_class(
            self, "is-current", new[1] is self._item if new else False
        )

    def update_buttons(self) -> None:
        last_changed = self.last_changed

        playback_status = self._item.playback_status
        can_go_prev = self._item.can_go_previous
        can_go_next = self._item.can_go_next
        can_pause = self._item.can_pause

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

        self.actions.set_visible(
            can_pause or can_go_next or can_go_prev
        )

    def update_slider(self) -> None:
        length = self._item.length
        if not length:
            self.slider.set_visible(False)
            return
        self.slider.set_visible(True)
        self.slider.set_range(0, length)
        self.slider.set_sensitive(self._item.can_seek)
        self.max_position.set_label(format_seconds(length))
        self.update_slider_position()

    def update_slider_position(self, *args: t.Any) -> None:
        position = self._item.position
        if position is None:
            return

        self.slider.set_value(position)
        self.current_position.set_label(format_seconds(position))

    def update_label(self) -> None:
        metadata = self._item.metadata

        xesam_artist = metadata.get("xesam:artist")
        _artists = xesam_artist if xesam_artist else None
        _title = metadata.get("xesam:title")

        if not _artists or not _title:
            title = "Nothing's playing"
            artists = ""
            self.last_changed.title = None
            self.last_changed.artists = None
        else:
            if (
                _artists == self.last_changed.artists
                and _title == self.last_changed.title
            ):
                return

            self.last_changed.title = _title
            self.last_changed.artists = _artists

            title = _title
            artists = ", ".join(_artists)

        for value, label in ((title, self.title), (artists, self.artists)):
            if value:
                label.set_tooltip_text(value)
                label.set_label(value)
            else:
                label.set_visible(False)

    def on_download(self, filepath: str | None) -> None:
        if not filepath:
            self.image.set_visible(False)
            return
        css = f"box {{ background-image: url('file://{filepath}'); }}"
        self.image_provider.load_from_data(css)

    def update_image(self) -> None:
        metadata = self._item.metadata
        art_url = metadata.get("mpris:artUrl")
        if not art_url:
            self.image.set_visible(False)
            return
        if art_url == self.last_changed.art_url:
            return
        self.image.set_visible(True)

        self.last_changed.art_url = art_url
        downloader.download_image_async(
            art_url, self.on_download, (64, 64), "arts"
        )

    def on_change(self) -> None:
        try:
            self.update_image()
            self.update_label()
            self.update_slider()
            self.update_buttons()
        except AttributeError:
            logger.warning(
                "Couldn't update player, player attributes aren't correct."
            )

    def destroy(self) -> None:
        for object, handler_id in self.handlers.items():
            if isinstance(object, Ref):
                object.unwatch(handler_id)
            elif isinstance(object, gobject.Object):
                object.disconnect(handler_id)
            else:
                object[0].unwatch(handler_id)


class PlayersBox(gtk.ScrolledWindow):
    __gtype_name__ = "PlayersBox"

    def __init__(self) -> None:
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.list = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.no_items_label = gtk.Revealer(
            child=gtk.Label(label="There isn't any players"),
            transition_duration=250,
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN,
            css_classes=("no-items",),
        )

        self.box.append(self.no_items_label)
        self.box.append(self.list)

        self.items: dict[str, Player] = {}
        super().__init__(
            child=self.box,
            css_classes=("players-box",),
            vscrollbar_policy=gtk.PolicyType.AUTOMATIC,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.handler_id = players.watch(self.update_items)
        self.update_items(players.value)

        self.timer_id = glib.timeout_add(500, self.timer)

        weakref.finalize(self, lambda: logger.debug("PlayersBox finalized"))

    def update_items(self, new_items: dict[str, MprisPlayer]) -> None:
        existing_items = set(self.items.keys())
        tray_items = set(new_items.keys())
        for item in tray_items:
            if item not in existing_items:
                tray_widget = Player(players.value[item])
                self.items[item] = tray_widget
                self.list.append(tray_widget)

        for item in existing_items:
            if item not in tray_items:
                self.items[item].destroy()
                self.list.remove(self.items[item])
                del self.items[item]

        self.no_items_label.set_reveal_child(len(self.items) == 0)

    def timer(self) -> bool:
        for key, item in self.items.items():
            if item._locked_timer:
                continue
            item.update_slider_position()
        return True

    def destroy(self) -> None:
        for key, item in self.items.items():
            item.destroy()
            self.list.remove(item)

        self.box.remove(self.no_items_label)
        self.items.clear()
        self.set_child(None)
        players.unwatch(self.handler_id)
        glib.source_remove(self.timer_id)


class PlayersWindow(widget.LayerWindow):
    __gtype_name__ = "PlayersWindow"

    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            anchors={
                "top": True,
                "left": True
            },
            margins={
                "top": HyprlandVars.gap,
                "left": HyprlandVars.gap
            },
            css_classes=("players",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="players",
            height=400,
            width=400,
            setup_popup=True
        )
        self.name = "players"
        self._child: PlayersBox | None = None

        weakref.finalize(self, lambda: logger.debug("PlayersWindow finalized"))

    def on_show(self) -> None:
        self._child = PlayersBox()
        self.set_child(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
        self.set_child(None)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
