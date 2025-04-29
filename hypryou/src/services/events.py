import typing as t
from dataclasses import dataclass
import logging

logger = logging.getLogger("hypryou")

# This file is UI events bus
# Components will be able to watch changes
# Like if something changed, or there was command from CLI
# It'll notify all watchers
# It has to be standalone (This file isn't importing any files)


type EventName = t.Literal[
    "name_owner_changed", "tray_item_changed",
    "mpris_player_changed", "hyprland",
    "toggle_window", "global",
    "settings_changed", "notification_replaced",
    "notification_dismissed"
]


class TrayItemChangedData(t.TypedDict):
    prop: str
    signal_name: str


class MprisPlayerChangedData(t.TypedDict):
    time: float


@dataclass
class Event:
    data: t.Any
    value: t.Hashable = "global"
    name: EventName = "global"


@dataclass
class TrayItemChanged(Event):
    data: TrayItemChangedData | None
    value: t.Hashable = "global"
    name = "tray_item_changed"


@dataclass
class NameOwnerChanged(Event):
    data: tuple[str, str, str]
    value: t.Hashable = "global"
    name = "name_owner_changed"


@dataclass
class MprisPlayerChanged(Event):
    data: MprisPlayerChangedData | None
    value: t.Hashable
    name = "mpris_player_changed"


type Watcher = t.Callable[[t.Any], None]


class EventsBus:
    def __init__(self) -> None:
        self._watchers: dict[str, dict[t.Hashable, list[Watcher]]] = {}

    def notify(
        self, event: Event
    ) -> None:
        name = event.name
        value = event.value
        if not (
            self._watchers.get(name)
            and self._watchers[name].get(value)
        ):
            return
        # this log is commented due to spam in console
        # logger.debug(
        #     "Event '%s' with value '%s' notified watchers",
        #     name, value
        # )
        for watcher in self._watchers[name][value]:
            watcher(event)

        for watcher in self._watchers[name]["global"]:
            watcher(event)

    def watch(
        self,
        event_name: EventName,
        callback: Watcher,
        value: t.Hashable | t.Literal["global"] = "global",
    ) -> None:
        logger.debug(
            "Event '%s' with value '%s' got new watcher",
            event_name, value
        )
        if not self._watchers.get(event_name):
            self._watchers[event_name] = {"global": []}
        if not self._watchers[event_name].get(value):
            self._watchers[event_name][value] = []
        self._watchers[event_name][value].append(callback)

    def unwatch(
        self,
        event_name: EventName,
        callback: Watcher,
        value: t.Hashable | t.Literal["global"] = "global"
    ) -> None:
        logger.debug(
            "Event '%s' with value '%s' removed watcher",
            event_name, value
        )
        if not self._watchers.get(event_name):
            self._watchers[event_name] = {}
        if not self._watchers[event_name].get(value):
            self._watchers[event_name][value] = []
        self._watchers[event_name][value].remove(callback)
