import typing as t
from dataclasses import dataclass
import logging

logger = logging.getLogger("hypryou")

# This file is UI events bus
# Components will be able to watch changes
# Like if something changed, or there was command from CLI
# It'll notify all watchers
# It has to be standalone (This file isn't importing any files)


@dataclass
class Event:
    name: str
    value: str
    data: t.Any


type Watcher = t.Callable[[Event], None]


class EventsBus:
    def __init__(self) -> None:
        self._watchers: dict[str, dict[str, list[Watcher]]] = {}

    def notify(self, event: str, value: str, data: t.Any) -> None:
        if not (
            self._watchers.get(event)
            and self._watchers[event].get(value)
        ):
            return
        # this log is commented due to spam in console
        # logger.debug(
        #     "Event '%s' with value '%s' notified watchers",
        #     event, value
        # )
        _event = Event(event, value, data)
        for watcher in self._watchers[event][value]:
            watcher(_event)

        for watcher in self._watchers[event]["global"]:
            watcher(_event)

    def watch(
        self,
        event: str,
        callback: Watcher,
        value: str | t.Literal["global"] = "global",
    ) -> None:
        logger.debug(
            "Event '%s' with value '%s' got new watcher",
            event, value
        )
        if not self._watchers.get(event):
            self._watchers[event] = {"global": []}
        if not self._watchers[event].get(value):
            self._watchers[event][value] = []
        self._watchers[event][value].append(callback)

    def unwatch(
        self,
        event: str,
        callback: Watcher,
        value: str | t.Literal["global"] = "global"
    ) -> None:
        logger.debug(
            "Event '%s' with value '%s' removed watcher",
            event, value
        )
        if not self._watchers.get(event):
            self._watchers[event] = {}
        if not self._watchers[event].get(value):
            self._watchers[event][value] = []
        self._watchers[event][value].remove(callback)
