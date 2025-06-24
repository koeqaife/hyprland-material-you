import os
from os.path import join as pjoin
import json
import typing as t
import sys
from utils.service import Signals

T = t.TypeVar('T')

DEBUG = os.environ.get("HYPRYOU_DEBUG", 0)
HOME = os.environ["HOME"]

CACHE_PATH = os.getenv("XDG_CACHE_HOME", f"{HOME}/.cache")
CONFIG_PATH = os.getenv("XDG_CONFIG_HOME", f"{HOME}/.config")
APP_CACHE_PATH = pjoin(CACHE_PATH, "hypryou")
CONFIG_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
TEMP_PATH = "/tmp/hypryou/"

color_templates = pjoin(APP_CACHE_PATH, "colors")
styles_output = pjoin(APP_CACHE_PATH, "style.css")
scss_variables = pjoin(TEMP_PATH, "_variables.scss")
main_scss = pjoin(CONFIG_DIR, "src", "scss", "main.scss")
config_path = pjoin(CONFIG_PATH, "hypryou")
settings_path = pjoin(config_path, "settings.json")
socket_path = pjoin(
    TEMP_PATH, "sockets",
    os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
)

default_settings: dict[str, t.Any] = {
    "time_format": "24",
    "always_show_battery": False,
    "corners": False,
    "dark_icons": "Tela-nord-dark",
    "light_icons": "Tela-nord-light",
    "opacity": 1,
    "wallpaper": f"{CONFIG_DIR}/assets/default_wallpaper.jpg",
    "separated_workspaces": False,
    "one_popup_at_time": True,
    "power_menu_cancel_button": True,
    "gtk4_theme": True,
    "gtk3_theme": True,
    "secure_cliphist": False,

    "browser": "firefox",
    "editor": "code",
    "files": "nautilus",
    "terminal": "alacritty",

    "cursor": "Bibata-Modern-Ice",
    "cursor_size": "24",

    "ac_lock": 300,
    "ac_dpms": 60,
    "ac_sleep": 0,
    "battery_lock": 60,
    "battery_dpms": 60,
    "battery_sleep": 60
}

os.makedirs(config_path, exist_ok=True)
os.makedirs(color_templates, exist_ok=True)
os.makedirs(APP_CACHE_PATH, exist_ok=True)
os.makedirs(TEMP_PATH, exist_ok=True)


class HyprlandVars:
    gap = 14
    rounding = 20


class Settings:
    _instance: t.Optional['Settings'] = None

    def __new__(cls) -> 'Settings':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'):
            self._signals = Signals(True)
            self._initialized = True
            self._values = {}
            try:
                with open(settings_path, 'r') as f:
                    self._values = json.load(f)
            except FileNotFoundError:
                with open(settings_path, 'w') as f:
                    f.write("{}")

    def save(self) -> None:
        with open(settings_path, 'w') as f:
            json.dump(self._values, f)

    def sync(self) -> None:
        old_values = self._values.copy()
        try:
            with open(settings_path, 'r') as f:
                self._values = json.load(f)
        except FileNotFoundError:
            with open(settings_path, 'w') as f:
                f.write("{}")
        for key, value in self._values.items():
            if key not in old_values or old_values[key] != value:
                self._signals.notify(f"changed::{key}", value)
                self._signals.notify("changed", key, value)

    def reset(self, name: str) -> None:
        self.set(name, default_settings[name])

    def set(self, name: str, value: t.Any) -> None:
        self._values[name] = value
        self.save()
        self._signals.notify(f"changed::{name}", value)
        self._signals.notify("changed", name, value)

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

    def watch(
        self, name: str,
        callback: t.Callable[[t.Any], None],
        init_call: bool = True,
        **kwargs: t.Any
    ) -> int:
        if init_call:
            callback(self.get(name))
        return self._signals.watch(f"changed::{name}", callback, **kwargs)

    def unwatch(self, handler_id: int) -> None:
        self._signals.unwatch(handler_id)
