from config import Settings
from utils import Ref
from utils.service import Service
from utils.colors import generate_by_last_wallpaper
from repository import gdk, gdk_pixbuf, glib
import typing as t
from types import NoneType

current_wallpaper = Ref[gdk.Texture | None](
    None,
    name="wallpaper_texture",
    types=(NoneType, gdk.Texture)
)


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


class StateService(Service):
    def start(self):
        settings = Settings()
        settings.watch("wallpaper", on_wallpapers_changed, False)
        glib.idle_add(generate_wallpaper_texture)
