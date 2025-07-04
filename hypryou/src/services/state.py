import threading
from config import Settings
from utils.ref import Ref
from utils.styles import reload_css
from utils.service import Service
from utils.colors import generate_by_last_wallpaper
from repository import gdk, glib, gio
import typing as t
from types import NoneType
from utils.service import Signals

_opened_windows = Ref[list[str]]([], name="opened_windows")
current_wallpaper = Ref[gdk.Texture | None](
    None,
    name="wallpaper_texture",
    types=(NoneType, gdk.Texture)
)
is_locked = Ref(False, name="is_locked")
is_idle_locked = Ref(False, name="is_idle_locked")
settings_page = Ref[str | None](
    None,
    name="settings_page",
    types=(str, NoneType)
)


class OpenedWindowsWatcher(Signals):
    def __init__(self) -> None:
        super().__init__()
        self.old_set: set[str] = set()

    def init(self) -> None:
        _opened_windows.watch(self.on_changed)

    def is_visible(self, window_name: str) -> bool:
        return window_name in _opened_windows.value

    def on_changed(self, new_value: list[str]) -> None:
        new_set = set(new_value)
        added = list(new_set - self.old_set)

        for window_name in added:
            self.notify(f"opened::{window_name}")
            self.notify(f"changed::{window_name}", True)

        removed = list(self.old_set - new_set)
        for window_name in removed:
            self.notify(f"closed::{window_name}")
            self.notify(f"changed::{window_name}", False)

        if added and Settings().get("one_popup_at_time"):
            for window_name in _opened_windows.value:
                if window_name not in added and window_name not in removed:
                    _opened_windows.value.remove(window_name)
                    self.notify(f"changed::{window_name}", False)

        self.old_set = new_set


opened_windows = OpenedWindowsWatcher()


def open_settings(page: str = "default") -> None:
    settings_page.value = page


def open_window(window_name: str) -> None:
    if window_name not in _opened_windows.value:
        _opened_windows.value.append(window_name)


def close_window(window_name: str) -> None:
    if window_name in _opened_windows.value:
        _opened_windows.value.remove(window_name)


def toggle_window(window_name: str) -> None:
    if window_name in _opened_windows.value:
        _opened_windows.value.remove(window_name)
    else:
        _opened_windows.value.append(window_name)


def generate_wallpaper_texture() -> None:
    settings = Settings()
    path = settings.get("wallpaper")

    def worker() -> None:
        file = gio.File.new_for_path(path)
        texture = gdk.Texture.new_from_file(file)
        current_wallpaper.value = texture

    threading.Thread(target=worker, daemon=True).start()


def on_wallpapers_changed(*args: t.Any) -> None:
    generate_by_last_wallpaper()
    glib.idle_add(generate_wallpaper_texture)


def on_opacity_changed(new_value: float) -> None:
    reload_css()


class StateService(Service):
    def start(self) -> None:
        opened_windows.init()
        settings = Settings()
        settings.watch("wallpaper", on_wallpapers_changed, False)
        settings.watch("opacity", on_opacity_changed, False)
        glib.idle_add(generate_wallpaper_texture)
