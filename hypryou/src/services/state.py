from config import Settings
from utils.service import Service
from utils.colors import generate_by_last_wallpaper
import typing as t


def on_wallpapers_changed(*args: t.Any) -> None:
    generate_by_last_wallpaper()


class StateService(Service):
    def start(self):
        settings = Settings()
        settings.watch("wallpaper", on_wallpapers_changed, False)
