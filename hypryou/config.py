import os
from os.path import join as pjoin
import json
import typing as t
import sys
from utils.service import Signals
from utils.ref import Ref

T = t.TypeVar('T')

MAJOR_VERSION = 2
MINOR_VERSION = 0
PATCH_VERSION = 0

VERSION = f"{MAJOR_VERSION}.{MINOR_VERSION}.{PATCH_VERSION}-beta"

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

info = {
    "name": "HyprYou",
    "author": "koeqaife",
    "github": "https://github.com/koeqaife/hyprland-material-you",
    "discord": "https://discord.gg/nCK3sh8mNU",
    "ko-fi": "https://ko-fi.com/koeqaife"
}

default_settings: dict[str, t.Any] = {
    "is_24hr_clock": True,
    "always_show_battery": False,
    "corners": True,
    "dark_icons": "Tela-nord-dark",
    "light_icons": "Tela-nord-light",
    "opacity": 1.0,
    "wallpaper": f"{CONFIG_DIR}/assets/default_wallpaper.jpg",
    "separated_workspaces": False,
    "one_popup_at_time": True,
    "power_menu_cancel_button": True,
    "gtk4_theme": True,
    "gtk3_theme": True,
    "secure_cliphist": False,

    "blur": True,
    "blur_xray": True,

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
            self._signals = Signals()
            self._initialized = True
            self._values: dict[str, Ref[t.Any]] = {}
            self._allow_saving = False
            try:
                with open(settings_path, 'r') as f:
                    self._update_values(json.load(f))
            except FileNotFoundError:
                with open(settings_path, 'w') as f:
                    f.write("{}")
            self._add_default()
            self._allow_saving = True

    def _create_ref(self, key: str, value: t.Any) -> None:
        def wrapper(new_value: str) -> None:
            self.save()
            self.notify_changed(key, new_value)

        ref = Ref(value, name=f"settings.{key}")
        ref.watch(wrapper)
        ref.create_ref(wrapper)
        self._values[key] = ref

    def _add_default(self) -> None:
        for key, value in default_settings.items():
            if key not in self._values.keys():
                self._create_ref(key, value)

    def _update_values(self, new: dict[str, t.Any]) -> None:
        for key, value in new.items():
            if key in self._values.keys():
                ref = self._values[key]
                ref.value = value
            else:
                self._create_ref(key, value)

        for key, ref in self._values.items():
            if key not in new.keys():
                self._values[key].value = default_settings[key]

    def save(self) -> None:
        if not self._allow_saving:
            return
        with open(settings_path, 'w') as f:
            json.dump(self.unpack(), f, indent=4)

    def sync(self) -> None:
        try:
            with open(settings_path, 'r') as f:
                self._update_values(json.load(f))
        except FileNotFoundError:
            with open(settings_path, 'w') as f:
                f.write("{}")

    def notify_changed(self, key: str, value: t.Any) -> None:
        self._signals.notify(f"changed::{key}", value)
        self._signals.notify("changed", key, value)

    def unpack(self) -> dict[str, t.Any]:
        _dict = {}
        for key, ref in self._values.items():
            _dict[key] = ref.unpack()
        return _dict

    def reset(self, name: str) -> None:
        self.set(name, default_settings[name])

    def set(self, name: str, value: t.Any) -> None:
        self._values[name].value = value

    def get(self, name: str) -> t.Any:
        if name in self._values.keys():
            return self._values[name].value
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
