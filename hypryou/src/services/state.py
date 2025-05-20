from config import Settings
from utils import Ref, reload_css
from utils.service import Service
from utils.colors import generate_by_last_wallpaper
from repository import gdk, gdk_pixbuf, glib
import typing as t
from types import NoneType

opened_windows = Ref[list[str]]([], name="opened_windows")
current_wallpaper = Ref[gdk.Texture | None](
    None,
    name="wallpaper_texture",
    types=(NoneType, gdk.Texture)
)


def open_window(window_name: str) -> None:
    if window_name not in opened_windows.value:
        opened_windows.value.append(window_name)


def close_window(window_name: str) -> None:
    if window_name in opened_windows.value:
        opened_windows.value.remove(window_name)


def toggle_window(window_name: str) -> None:
    if window_name in opened_windows.value:
        opened_windows.value.remove(window_name)
    else:
        opened_windows.value.append(window_name)


def generate_wallpaper_texture() -> None:
    settings = Settings()
    pixbuf = gdk_pixbuf.Pixbuf.new_from_file(
        settings.get("wallpaper")
    )
    texture = gdk.Texture.new_for_pixbuf(pixbuf)
    current_wallpaper.value = texture


def on_wallpapers_changed(*args: t.Any) -> None:
    generate_by_last_wallpaper()
    glib.idle_add(generate_wallpaper_texture)


def on_opacity_changed(new_value: float) -> None:
    reload_css()


class StateService(Service):
    def start(self):
        settings = Settings()
        settings.watch("wallpaper", on_wallpapers_changed, False)
        settings.watch("opacity", on_opacity_changed, False)
        glib.idle_add(generate_wallpaper_texture)
