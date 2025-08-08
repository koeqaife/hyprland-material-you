import os
from os.path import join as pjoin
import json
import typing as t
from utils.service import Signals
from utils.ref import Ref

T = t.TypeVar('T')

HOME = os.environ["HOME"]

CACHE_DIR = os.getenv("XDG_CACHE_HOME", f"{HOME}/.cache")
CONFIG_DIR = os.getenv("XDG_CONFIG_HOME", f"{HOME}/.config")
PICTURES_DIR = os.getenv("XDG_PICTURES_DIR", f"{HOME}/Pictures")
APP_CACHE_DIR = pjoin(CACHE_DIR, "hypryou")
ORIGINAL_DIR = "/usr/lib/hypryou"
TEMP_DIR = f"/tmp/hypryou-{os.getenv("USER", "unknown")}"
ASSETS_DIR = "/usr/share/hypryou"

color_templates = pjoin(APP_CACHE_DIR, "colors")
styles_output = pjoin(APP_CACHE_DIR, "style.css")
scss_variables = pjoin(TEMP_DIR, "_variables.scss")
main_scss = pjoin(ASSETS_DIR, "scss", "main.scss")
config_dir = pjoin(CONFIG_DIR, "hypryou")
settings_path = pjoin(config_dir, "settings.json")
socket_path = pjoin(
    TEMP_DIR, "sockets",
    os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
)
state_dir = pjoin(
    TEMP_DIR, "state",
    os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
)
# NOTE: ~/wallpaper is for backward compatibility with v1
wallpaper_dirs = [
    pjoin(PICTURES_DIR, "wallpapers"),
    pjoin(HOME, "wallpaper")
]

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
    "opacity": 1.0,
    "wallpaper": f"{ASSETS_DIR}/default_wallpaper.jpg",
    "separated_workspaces": False,
    "one_popup_at_time": True,
    "power_menu_cancel_button": True,
    "secure_cliphist": False,
    "floating_sidebar": False,
    "hide_empty_workspaces": False,
    "color": "",

    "themes.gtk3": True,
    "themes.gtk4": True,
    "themes.kitty": False,
    "themes.wezterm": False,
    "themes.alacritty": False,
    "themes.telegram": False,

    "icons.dark": "Tela-nord-dark",
    "icons.light": "Tela-nord-light",

    "blur.enabled": True,
    "blur.xray": True,

    "apps.enabled": True,
    "apps.browser": "firefox",
    "apps.editor": "code",
    "apps.files": "nautilus",
    "apps.terminal": "alacritty",

    "cursor.name": "Bibata-Modern-Ice",
    "cursor.size": 24,

    "idle.ac.lock": 300,
    "idle.ac.dpms": 60,
    "idle.ac.sleep": 0,
    "idle.battery.lock": 60,
    "idle.battery.dpms": 60,
    "idle.battery.sleep": 60,

    # Input
    "input.enabled": True,
    "input.kb_model": "",
    "input.kb_layout": "us",
    "input.kb_variant": "",
    "input.kb_options": "",
    "input.change_layout": "",
    "input.kb_rules": "",
    "input.numlock_by_default": False,
    "input.resolve_binds_by_sym": False,
    "input.repeat_rate": 25,
    "input.repeat_delay": 600,
    "input.sensitivity": 0.0,
    "input.accel_profile": "",
    "input.force_no_accel": False,
    "input.left_handed": False,
    "input.scroll_method": "",
    "input.natural_scroll": False,
    "input.follow_mouse": 1,
    "input.follow_mouse_threshold": 0.0,
    "input.focus_on_close": 0,
    "input.mouse_refocus": True,
    "input.float_switch_override_focus": 1,

    # Input touchpad
    "input.touchpad.enabled": False,
    "input.touchpad.disable_while_typing": True,
    "input.touchpad.natural_scroll": False,
    "input.touchpad.scroll_factor": 1.0,
    "input.touchpad.middle_button_emulation": False,
    "input.touchpad.tap_button_map": "lrm",
    "input.touchpad.clickfinger_behavior": False,
    "input.touchpad.tap_to_click": True,
    "input.touchpad.tap_and_drag": True,
    "input.touchpad.flip_x": False,
    "input.touchpad.flip_y": False,

    # Hyprland
    "hyprland.gaps_in": 5,
    "hyprland.gaps_out": 12,
    "hyprland.border_size": 0,
    "hyprland.layout": "dwindle",
    "hyprland.decoration.rounding": 16,
    "hyprland.decoration.rounding_power": 2.0,

    # Hyprland misc
    "hyprland.misc.vrr": 0,
    "hyprland.misc.middle_click_paste": True,

    # Hyprland snap
    "hyprland.snap.enabled": False,
    "hyprland.snap.window_gap": 10,
    "hyprland.snap.monitor_gap": 10,
    "hyprland.snap.border_overlap": False,
    "hyprland.snap.respect_gaps": False,

    # Hyprsunset
    "hyprsunset.temperature": 3500,

    "lid_action": "dpms",
    "monitors": [],
    "keybinds_overrides": []
}


def makedirs() -> None:
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(color_templates, exist_ok=True)
    os.makedirs(APP_CACHE_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(wallpaper_dirs[0], exist_ok=True)


def get_version() -> str:
    if ver := getattr(get_version, "_version", None):
        return str(ver)
    with open(pjoin(ORIGINAL_DIR, "version.txt")) as f:
        version = f.read()
    setattr(get_version, "_version", version)
    return version


class Settings:
    __slots__ = (
        "_signals", "_initialized",
        "_values", "_allow_saving",
        "_file_dict", "_views",
        "mutable"
    )
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
            self._file_dict: dict[str, t.Any] = {}
            self._views: dict[str, SettingsView] = {}
            self.mutable = True
            self.sync()
            self._allow_saving = True

    def _ensure_ref(self, key: str) -> None:
        if key not in self._values:
            if key not in default_settings:
                raise KeyError(f"{key} doesn't exist in settings")
            self._create_ref(
                key,
                self._file_dict.get(key, default_settings.get(key))
            )

    def _create_ref(self, key: str, value: t.Any) -> None:
        if key in self._values.keys():
            return

        def wrapper(new_value: str) -> None:
            self.save()
            self.notify_changed(key, new_value)

        ref = Ref(value, name=f"settings.{key}", deep=True)
        ref.watch(wrapper)
        ref.create_ref(wrapper)
        self._values[key] = ref

    def _update_values(self, new: dict[str, t.Any]) -> None:
        for key, value in new.items():
            if key not in default_settings.keys():
                continue
            if key in self._values.keys():
                ref = self._values[key]
                ref.value = value

        for key, ref in self._values.items():
            if key not in new.keys():
                self._values[key].value = default_settings[key]

    def save(self) -> None:
        if not self.mutable:
            return

        if not self._allow_saving:
            return
        new_dict = self.unpack()
        if new_dict != self._file_dict:
            with open(settings_path, 'w') as f:
                self._file_dict = new_dict
                data = json.dumps(self._file_dict, indent=4)
                f.write(data)

    def sync(self) -> None:
        try:
            with open(settings_path, 'r') as f:
                self._file_dict = dict(json.load(f))
                self._update_values(self._file_dict)
        except FileNotFoundError:
            if os.path.exists(os.path.dirname(settings_path)):
                with open(settings_path, 'w') as f:
                    f.write("{}")

    def notify_changed(self, key: str, value: t.Any) -> None:
        self._signals.notify(f"changed::{key}", value)
        self._signals.notify("changed", key, value)

    def unpack(self) -> dict[str, t.Any]:
        _dict = {}
        for key, value in self._file_dict.items():
            _dict[key] = value

        for key, ref in self._values.items():
            if (
                not (value := ref.unpack()) == default_settings[key]
                or key in self._file_dict
            ):
                _dict[key] = value
        return _dict

    def reset(self, key: str) -> None:
        self._ensure_ref(key)
        self.set(key, default_settings[key])

    def set(self, key: str, value: t.Any) -> None:
        self._ensure_ref(key)
        self._values[key].value = value

    def get(self, key: str) -> t.Any:
        if key in self._values.keys():
            return self._values[key].value
        else:
            return self._file_dict.get(key, default_settings[key])

    def get_ref(self, key: str) -> Ref[t.Any]:
        self._ensure_ref(key)
        return self._values[key]

    def toggle(self, key: str) -> None:
        self._ensure_ref(key)
        value = self.get(key)
        if isinstance(value, bool):
            self.set(key, not value)
        else:
            raise ValueError(f"{key} is not bool!")

    def toggle_between(self, key: str, first: T, second: T) -> None:
        self._ensure_ref(key)
        value = self.get(key)
        if value == first:
            self.set(key, second)
        elif value == second:
            self.set(key, first)

    def watch(
        self, key: str,
        callback: t.Callable[[t.Any], None],
        init_call: bool = True,
        **kwargs: t.Any
    ) -> int:
        self._ensure_ref(key)
        if init_call:
            callback(self.get(key))
        return self._signals.watch(f"changed::{key}", callback, **kwargs)

    def unwatch(self, handler_id: int) -> None:
        self._signals.unwatch(handler_id)

    def get_view_for(self, key: str) -> "SettingsView":
        if key in self._views.keys():
            return self._views[key]
        else:
            view = SettingsView(key, self)
            self._views[key] = view
            return view


class SettingsView:
    __slots__ = ("_prefix", "_instance")

    def __init__(
        self,
        prefix: str,
        instance: Settings
    ) -> None:
        self._prefix = prefix
        self._instance = instance

    def save(self) -> None:
        self._instance.save()

    def sync(self) -> None:
        self._instance.sync()

    def notify_changed(self, key: str, value: str) -> None:
        key = f"{self._prefix}.{key}"
        self._instance.notify_changed(key, value)

    def unpack(self) -> dict[str, t.Any]:
        return self._instance.unpack()

    def reset(self, key: str) -> None:
        key = f"{self._prefix}.{key}"
        self._instance.reset(key)

    def set(self, key: str, value: t.Any) -> None:
        key = f"{self._prefix}.{key}"
        self._instance.set(key, value)

    def get(self, key: str) -> t.Any:
        key = f"{self._prefix}.{key}"
        return self._instance.get(key)

    def get_ref(self, key: str) -> Ref[t.Any]:
        key = f"{self._prefix}.{key}"
        return self._instance.get_ref(key)

    def toggle(self, key: str) -> None:
        key = f"{self._prefix}.{key}"
        self._instance.toggle(key)

    def toggle_between(self, key: str, first: T, second: T) -> None:
        key = f"{self._prefix}.{key}"
        self._instance.toggle_between(key, first, second)

    def watch(
        self,
        key: str,
        callback: t.Callable[[t.Any], None],
        init_call: bool = True,
        **kwargs: t.Any
    ) -> int:
        key = f"{self._prefix}.{key}"
        return self._instance.watch(
            key,
            callback,
            init_call,
            **kwargs
        )

    def unwatch(self, handler_id: int) -> None:
        self._instance.unwatch(handler_id)

    def get_view_for(self, key: str) -> "SettingsView":
        key = f"{self._prefix}.{key}"
        return self._instance.get_view_for(key)
