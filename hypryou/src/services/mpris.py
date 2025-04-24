from __future__ import annotations

import time
from repository import gio, glib
import typing as t
from src.services.dbus import dbus_proxy, bus, cache_proxy_properties
from src.services.events import Event
from src.variables import Globals
from utils.logger import logger
from utils import Ref

MPRIS_PREFIX = "org.mpris.MediaPlayer2."

players = Ref[dict[str, "MprisPlayer"]]({}, name="mpris_players")
current_player = Ref[
    "tuple[bool, MprisPlayer] | tuple[()]"
](
    (), name="mpris_player"
)

type LoopStatus = t.Literal["None", "Track", "Playlist"]
type PlaybackStatus = t.Literal["Playing", "Paused", "Stopped"]


def update_current_player() -> None:
    print("UPDATE CURRENT")
    last_changed_player: tuple[float, MprisPlayer] | None = None

    for bus_name, player in players.value.items():
        # If found playing player it'll show it
        # Basically it'll show the first player in list
        # So if two players are playing it'll show the first who've added
        if player.playback_status == "Playing":
            current_player.value = (False, player)
            return

        # If it didn't find playing player it'll add last changed player
        if (
            last_changed_player is None
            or last_changed_player[0] < player._last_changed_time
        ):
            last_changed_player = (player._last_changed_time, player)

    if last_changed_player:
        # If current_player was last_changed_player it'll be able to change it
        # If not it won't touch it (for example if last player was playing)
        if (
            not current_player.value
            or current_player.value[0]
            or current_player.value[1]._bus_name not in players.value
        ):
            current_player.value = (True, last_changed_player[1])


class MprisMetadata(t.TypedDict, total=False):
    mpris_trackid: str
    mpris_length: int
    xesam_title: str
    xesam_artist: list[str]
    xesam_album: str
    xesam_album_artist: t.Optional[str]
    xesam_genre: list[str]

    xesam_composer: t.Optional[list[str]]
    xesam_conductor: t.Optional[list[str]]
    xesam_track_number: t.Optional[int]
    xesam_disc_number: t.Optional[int]
    xesam_date: t.Optional[str]
    xesam_url: t.Optional[str]
    xesam_lyrics: t.Optional[str]
    xesam_media_type: t.Optional[str]
    xesam_rating: t.Optional[float]

    mpris_artUrl: t.Optional[str]
    mpris_shuffle: t.Optional[bool]
    mpris_loopStatus: t.Optional[str]
    mpris_volume: t.Optional[float]
    mpris_playback_status: t.Optional[str]


def to_mpris_metadata(d: dict[str, t.Any]) -> MprisMetadata:
    converted = {
        key.replace(':', '_'): value
        for key, value in d.items()
    }
    return t.cast(MprisMetadata, converted)


class MprisPlayer:
    def __init__(self, proxy: gio.DBusProxy):
        self._proxy: gio.DBusProxy = proxy
        self._bus_name = self.get_bus_name()
        self._bus_path = proxy.get_object_path()
        self._conn = proxy.get_connection()

        self._last_known_position: float = -1
        self._pos_changed_time = time.monotonic()
        self._playback_status = self.playback_status
        self._metadata: MprisMetadata | None = None

        self._last_changed_time = time.monotonic()
        self.conns = [
            self._proxy.connect(
                "g-properties-changed", self.properties_changed
            ),
            self._proxy.connect(
                "g-signal", self.on_dbus_signal
            )
        ]
        self._cache_properties()

    def on_dbus_signal(
        self,
        proxy: gio.DBusProxy,
        bus_name: str,
        signal_name: str,
        signal_args: glib.Variant
    ) -> None:
        if signal_name == "Seeked":
            args = t.cast(tuple[float], signal_args.unpack())
            self._last_known_position = args[0] / 1_000_000
            self._pos_changed_time = time.monotonic()
            self._last_changed_time = time.monotonic()
            update_current_player()
            Globals.events.notify("mpris_player_changed", self._bus_name, {
                "time": self.position
            })

    def finalize(self) -> None:
        for conn in self.conns:
            self._proxy.disconnect(conn)
        if current_player.value and self is current_player.value[1]:
            current_player.value = ()

    def get_bus_name(self) -> str:
        bus_name = self._proxy.get_name()
        if bus_name is None:
            raise RuntimeError("Proxy bus name is None.")
        else:
            self._bus_name = bus_name
        return bus_name

    def properties_changed(
        self,
        proxy: gio.DBusProxy,
        changed_properties_variant: glib.Variant,
        invalid_properties: list[str]
    ) -> None:
        changed_properties = t.cast(
            dict[str, str],
            changed_properties_variant.unpack()
        )
        self._cache_properties(list(changed_properties.keys()))
        if "PlaybackStatus" in changed_properties:
            self._last_known_position = self.position
            self._pos_changed_time = time.monotonic()
            self._playback_status = self.playback_status

        self._last_changed_time = time.monotonic()
        update_current_player()

        Globals.events.notify("mpris_player_changed", self._bus_name, None)

    def prop(self, property_name: str) -> t.Any:
        value = self._proxy.get_cached_property(property_name)
        if value is None:
            return None
        return value.unpack()

    def set_prop(
        self,
        property_name: str,
        value: glib.Variant
    ) -> None:
        self._proxy.set_property(
            property_name,
            value
        )
        self._proxy.set_cached_property(
            property_name,
            value
        )

    def call_method(
        self,
        method_name: str,
        parameters: glib.Variant | None = None
    ) -> None:
        self._proxy.call_sync(
            method_name,
            parameters,
            gio.DBusCallFlags.NONE,
            -1,
            None
        )

    def next(self) -> None:
        self.call_method("Next")

    def previous(self) -> None:
        self.call_method("Previous")

    def pause(self) -> None:
        self.call_method("Pause")

    def play_pause(self) -> None:
        self.call_method("PlayPause")

    def stop(self) -> None:
        self.call_method("Stop")

    def play(self) -> None:
        self.call_method("Play")

    def seek(self, offset: int) -> None:
        self.call_method("Seek", glib.Variant("x", offset))

    def set_position(self, track_id: str, position: int) -> None:
        self.call_method(
            "SetPosition",
            glib.Variant("(ox)", (track_id, position))
        )

    def open_uri(self, uri: str) -> None:
        self.call_method("OpenUri", glib.Variant("s", uri))

    @property
    def playback_status(self) -> PlaybackStatus:
        return t.cast(PlaybackStatus, self.prop("PlaybackStatus"))

    @property
    def loop_status(self) -> LoopStatus:
        return t.cast(LoopStatus, self.prop("LoopStatus"))

    @loop_status.setter
    def loop_status(self, new_value: LoopStatus) -> None:
        self.set_prop("LoopStatus", glib.Variant("s", new_value))

    @property
    def rate(self) -> float:
        return t.cast(float, self.prop("Rate"))

    @rate.setter
    def rate(self, new_value: float) -> None:
        self.set_prop("Rate", glib.Variant("d", new_value))

    @property
    def shuffle(self) -> bool:
        return t.cast(bool, self.prop("Shuffle"))

    @shuffle.setter
    def shuffle(self, new_value: bool) -> None:
        self.set_prop("Shuffle", glib.Variant("b", new_value))

    @property
    def metadata(self) -> MprisMetadata:
        if not self._metadata:
            metadata = t.cast(dict[str, t.Any], self.prop("Metadata"))
            self._metadata = to_mpris_metadata(metadata)
        return self._metadata

    @property
    def volume(self) -> float:
        return t.cast(float, self.prop("Volume"))

    @volume.setter
    def volume(self, new_value: float) -> None:
        self.set_prop("Volume", glib.Variant("d", new_value))

    @property
    def cached_position(self) -> int:
        """Cached position of current playing track

        Returns:
            int: Position in microseconds
        """
        return t.cast(int, self.prop("Position")) or 0

    @property
    def position(self) -> float:
        """Position of current playing track

        Returns:
            float: Position in seconds
        """
        if self._last_known_position == -1:
            self._last_known_position = self.cached_position / 1_000_000
            self._pos_changed_time = time.monotonic()
        if self._playback_status == "Playing":
            now = time.monotonic()
            delta = now - self._pos_changed_time
            return self._last_known_position + delta
        return self._last_known_position

    @property
    def minimum_rate(self) -> float:
        return t.cast(float, self.prop("MinimumRate"))

    @property
    def maximum_rate(self) -> float:
        return t.cast(float, self.prop("MaximumRate"))

    @property
    def can_go_next(self) -> bool:
        return t.cast(bool, self.prop("CanGoNext"))

    @property
    def can_go_previous(self) -> bool:
        return t.cast(bool, self.prop("CanGoPrevious"))

    @property
    def can_play(self) -> bool:
        return t.cast(bool, self.prop("CanPlay"))

    @property
    def can_pause(self) -> bool:
        return t.cast(bool, self.prop("CanPause"))

    @property
    def can_seek(self) -> bool:
        return t.cast(bool, self.prop("CanSeek"))

    @property
    def can_control(self) -> bool:
        return t.cast(bool, self.prop("CanControl"))

    def _cache_properties(self, changed: list[str] | None = None) -> None:
        cache_proxy_properties(
            self._conn,
            self._proxy,
            changed,
            self._cache_properties_finish
        )

    def _cache_properties_finish(self, *args: t.Any) -> None:
        self._metadata = None
        update_current_player()


class MprisWatcher:
    def __init__(self) -> None:
        Globals.events.watch(
            "dbus_signal",
            self.on_name_owner_changed,
            "name_owner_changed"
        )

    def on_name_owner_changed(self, event: Event) -> None:
        name, old_owner, new_owner = t.cast(
            tuple[str, str, str],
            event.data
        )
        if name.startswith(MPRIS_PREFIX):
            if old_owner != "" and new_owner == "":  # Disappeared
                self.remove_player(name)
            elif old_owner == "" and new_owner != "":  # Appeared
                self.add_player(name)

    def scan_existing_players(self) -> None:
        result = dbus_proxy.call_sync(
            "ListNames",
            None,
            gio.DBusCallFlags.NONE,
            -1,
            None
        )
        names = t.cast(list[str], result.unpack()[0])
        players = [name for name in names if name.startswith(MPRIS_PREFIX)]
        for name in players:
            self.add_player(name)

    def add_player(self, name: str) -> None:
        if name in players.value:
            return

        proxy = gio.DBusProxy.new_sync(
            bus,
            gio.DBusProxyFlags.NONE,
            None,
            name,
            "/org/mpris/MediaPlayer2",
            "org.mpris.MediaPlayer2.Player",
            None
        )
        player = MprisPlayer(proxy)
        players.value[name] = player
        logger.debug("Added new mpris player: %s", name)

    def remove_player(self, name: str) -> None:
        if name in players.value:
            player = players.value[name]
            player.finalize()
            del players.value[name]
            logger.debug("Removed mpris player: %s", name)
            update_current_player()


def start() -> None:
    logger.debug("Starting mpris watcher")
    watcher = MprisWatcher()
    watcher.scan_existing_players()
