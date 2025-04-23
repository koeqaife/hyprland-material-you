import os
from os.path import join as pjoin
import json
import typing as t
from src.variables import Globals
from src.services.events import Event, Watcher
import sys

T = t.TypeVar('T')

DEBUG = os.environ.get("HYPRYOU_DEBUG", 0)
HOME = os.environ["HOME"]

CACHE_PATH = os.getenv("XDG_CACHE_HOME", f"{HOME}/.cache")
APP_CACHE_PATH = pjoin(CACHE_PATH, "hypryou")
CONFIG_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
TEMP_PATH = "/tmp/hypryou/"

hyprland_gap = 14

styles_output = pjoin(TEMP_PATH, "style.css")
main_scss = pjoin(CONFIG_DIR, "src", "scss", "main.scss")
colors_file = pjoin(HOME, ".cache", "material", "colors.css")
config_path = pjoin(HOME, ".config", "hypryou")
settings_path = pjoin(config_path, "settings.json")
socket_path = pjoin(
    TEMP_PATH, "sockets",
    os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
)

default_settings: dict[str, t.Any] = {
    "time_format": "24",
    "bar_position": "top",
    "always_show_battery": False,
    "corners": False
}

os.makedirs(config_path, exist_ok=True)
os.makedirs(APP_CACHE_PATH, exist_ok=True)


type Wrappers = dict[t.Callable[[t.Any], None], Watcher]


class Settings:
    _instance: t.Optional['Settings'] = None

    def __new__(cls) -> 'Settings':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._values = {}
            self._events = Globals.events
            self._wrappers: Wrappers = {}

            try:
                with open(settings_path, 'r') as f:
                    self._values = json.load(f)
            except FileNotFoundError:
                with open(settings_path, 'w') as f:
                    f.write("{}")

    def sync(self) -> None:
        with open(settings_path, 'w') as f:
            json.dump(self._values, f)

    def reset(self, name: str) -> None:
        self.set(name, default_settings[name])

    def set(self, name: str, value: t.Any) -> None:
        self._values[name] = value
        self.sync()
        self._events.notify("settings_changed", name, value)

    def get(self, name: str) -> t.Any:
        if name in self._values:
            return self._values[name]
        else:
            return default_settings.get(name)

    def toggle(self, name: str) -> None:
        value = self.get(name)
        if isinstance(value, bool):
            self.set(name, not value)
        else:
            raise ValueError(f"{name} is not bool!")

    def toggle_between(self, name: str, first: T, second: T) -> None:
        value = self.get(name)
        if value == first:
            self.set(name, second)
        elif value == second:
            self.set(name, first)

    def _wrapper(self, callback: t.Callable[[t.Any], None]) -> Watcher:
        if callback not in self._wrappers:
            def func(event: Event) -> None:
                callback(event.data)
            self._wrappers[callback] = func
            return func
        else:
            return self._wrappers[callback]

    def subscribe(
        self, name: str,
        callback: t.Callable[[t.Any], None],
        init_call: bool = True
    ) -> None:
        if init_call:
            callback(self.get(name))
        self._events.watch("settings_changed", self._wrapper(callback), name)

    def unsubscribe(
        self, name: str,
        callback: t.Callable[[t.Any], None]
    ) -> None:
        wrapper = self._wrapper(callback)
        self._events.unwatch("settings_changed", wrapper, name)
        del self._wrappers[callback]
