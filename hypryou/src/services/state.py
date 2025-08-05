import threading
import time
from config import Settings, wallpaper_dirs, ASSETS_DIR
from config import color_templates, CONFIG_DIR
from utils.ref import Ref
from utils.styles import reload_css
from utils.service import Service
from utils.colors import generate_by_settings
from utils.logger import logger
from repository import gdk, glib, gio
import random
import typing as t
from types import NoneType
from utils.service import Signals
from os.path import join, exists
from config import state_dir
import os
from os import path
import asyncio
import src.services.hyprland as hyprland
from src.services.mpris import players
from src.services.login1 import get_login_manager
from src.services.upower import lid_is_closed

STATE_FILE_VERSION = 1
WALLPAPER_EXTENSIONS = {
    ".png", ".jpg", ".jpeg"
}

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
restored_on = -1.0
task_lock = threading.Lock()


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
    settings_page.notify_signal("open")


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


def get_all_wallpapers() -> list[str]:
    images: list[str] = [
        f"{ASSETS_DIR}/default_wallpaper.jpg"
    ]

    for dir in wallpaper_dirs:
        if not path.exists(dir) or not path.isdir(dir):
            continue

        for entry in os.listdir(dir):
            file = join(dir, entry)
            if (
                path.isfile(file)
                and path.splitext(file)[1] in WALLPAPER_EXTENSIONS
            ):
                images.append(file)

    return images


def set_random_wallpaper() -> None:
    wallpapers = get_all_wallpapers()
    random_wallpaper = random.choice(wallpapers)
    Settings().set("wallpaper", random_wallpaper)


def generate_wallpaper_texture() -> None:
    import gc
    settings = Settings()
    path = settings.get("wallpaper")

    if task_lock.acquire():
        try:
            file = gio.File.new_for_path(path)
            texture = gdk.Texture.new_from_file(file)

            old_texture = current_wallpaper.value
            current_wallpaper.value = texture

            del file
            if old_texture:
                del old_texture
            gc.collect()
        finally:
            task_lock.release()


def on_wallpapers_changed(*args: t.Any) -> None:
    generate_by_settings()
    glib.idle_add(generate_wallpaper_texture)


def save_state() -> None:
    if time.time() - restored_on < 60:
        return

    data = bytearray()
    data.extend(b"HY")
    data.append(STATE_FILE_VERSION)

    # Session lock
    data.append(1 if is_locked.value else 0)

    # Current settings page
    page_bytes = (settings_page.value or "").encode("utf-8")
    data.append(len(page_bytes))
    data.extend(page_bytes)

    # popups
    popups = _opened_windows.value
    data.append(len(popups))  # number of popups
    for popup in popups:
        pb = popup.encode("utf-8")
        if len(pb) > 255:
            raise ValueError(f"Popup name too long: {popup}")
        data.append(len(pb))
        data.extend(pb)

    with open(join(state_dir, "last-state"), "wb") as f:
        f.write(data)


def restore_state() -> None:
    path = join(state_dir, "last-state")
    if not exists(path):
        return

    with open(path, "rb") as f:
        data = f.read()
    os.remove(path)

    pos = 0
    if data[:2] != b'HY':
        return
    pos += 2

    version = data[pos]
    if version != STATE_FILE_VERSION:
        return
    pos += 1

    global restored_on
    restored_on = time.time()

    is_locked.value = data[pos] == 1
    pos += 1

    page_len = data[pos]
    pos += 1
    page = data[pos:pos + page_len].decode("utf-8")
    settings_page.value = page if page else None
    pos += page_len

    num_popups = data[pos]
    pos += 1

    for _ in range(num_popups):
        plen = data[pos]
        pos += 1
        popup = data[pos:pos + plen].decode("utf-8")
        pos += plen
        open_window(popup)


THEMES_CONFIGS = {
    "alacritty": (
        f"{color_templates}/alacritty.toml",
        f"{CONFIG_DIR}/alacritty/alacritty.toml"
    ),
    "kitty": (
        f"{color_templates}/kitty.conf",
        f"{CONFIG_DIR}/kitty/kitty.conf"
    ),
    "wezterm": (
        f"{color_templates}/wezterm.lua",
        f"{CONFIG_DIR}/wezterm.lua"
    )
}


def update_theme_link(enabled: bool, key: str) -> None:
    path = THEMES_CONFIGS[key][0]
    dest = THEMES_CONFIGS[key][1]
    if enabled:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.lexists(dest):
            os.replace(dest, dest + '.hypryou-bak')
        os.symlink(path, dest)
    else:
        if os.path.islink(dest):
            os.unlink(dest)
        bak = dest + '.hypryou-bak'
        if os.path.exists(bak):
            os.replace(bak, dest)


def on_settings_changed(key: str, value: t.Any) -> None:
    if key.startswith("themes."):
        key = key.lstrip("themes.")
        if key in THEMES_CONFIGS.keys():
            update_theme_link(value, key)
            generate_by_settings(force=True)
    elif key == "hyprland.decoration.rounding":
        reload_css()
    elif key == "opacity":
        reload_css()
    elif key == "color":
        generate_by_settings()


def on_lid_closed(is_closed: bool) -> None:
    if not is_closed:
        asyncio.create_task(
            hyprland.client.raw("dispatch dpms on")
        )
        return

    action = Settings().get("lid_action")
    if not action:
        return

    if __debug__:
        logger.debug("Lid action: %s", action)

    if action == "lock":
        if __debug__:
            logger.debug("Locking screen")
        is_locked.value = True
    elif action == "sleep":
        if __debug__:
            logger.debug("Going to sleep")
        is_locked.value = True
        for player in players.value.values():
            player.pause()
        get_login_manager().suspend()
    elif action == "dpms":
        if __debug__:
            logger.debug("Turning off displays")
        is_locked.value = True
        asyncio.create_task(
            hyprland.client.raw("dispatch dpms off")
        )


class StateService(Service):
    def start(self) -> None:
        opened_windows.init()
        settings = Settings()
        settings.watch("wallpaper", on_wallpapers_changed, False)
        settings._signals.watch("changed", on_settings_changed)
        lid_is_closed.watch(on_lid_closed)
        glib.idle_add(generate_wallpaper_texture)
