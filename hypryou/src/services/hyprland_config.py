from utils import sync_debounce
from utils.service import Service
from utils.logger import logger
from src.services.hyprland_keybinds import key_binds
from src.services.hyprland_keybinds.common import (
    KeyBind, KeyBindHint
)
from config import config_path, Settings
import os

generated_config = os.path.join(config_path, "hyprland_generated.conf")

noanim_layers = [
    "hypryou-notifications.*",
    "hypryou-popups.*",
    "hypryou-wallpapers.*"
]


def generate_noanim() -> str:
    return "\n".join(
        f"layerrule = noanim, {layer}"
        for layer in noanim_layers
    ) + "\n"


def generate_cursor_settings() -> str:
    settings = Settings()
    cursor = settings.get("cursor")
    cursor_size = settings.get("cursor_size")

    return (
        f"env = XCURSOR_SIZE,{cursor_size}\n" +
        f"exec-once = hyprctl setcursor {cursor} {cursor_size}\n"
    )


def generate_binds() -> str:
    output = ""
    for bind in key_binds:
        if isinstance(bind, KeyBindHint):
            continue
        elif not isinstance(bind, KeyBind):
            continue

        if len(bind.bind) == 2:
            key_str = ", ".join(bind.bind)
        elif len(bind.bind) == 3:
            key_str = f"{bind.bind[0]} {bind.bind[1]}, {bind.bind[2]}"
        elif len(bind.bind) == 1:
            key_str = f",{bind.bind[0]}"
        else:
            logger.warning(f"Bind {bind} has wrong length of bind")
            continue

        if isinstance(bind.action, tuple):
            action = ", ".join(bind.action)
        else:
            action = bind.action
        bind_str = f"{key_str}, {action}"
        if "mouse" in key_str:
            output += f"bindm = {bind_str}\n"
        else:
            output += f"bind = {bind_str}\n"

    return output


def generate_env() -> str:
    settings = Settings()
    env_vars = {
        "BROWSER": settings.get("browser"),
        "TERMINAL": settings.get("terminal"),
        "EDITOR": settings.get("editor"),
        "FILEMANAGER": settings.get("files"),

        "XDG_UTILS_BROWSER": settings.get("browser"),
        "XDG_UTILS_TERMINAL": settings.get("terminal"),
        "XDG_UTILS_FILEMANAGER": settings.get("files")
    }
    lines = [f"env = {key}, {value}" for key, value in env_vars.items()]
    output = "\n".join(lines)
    return output + "\n"


funcs = (
    generate_env,
    generate_binds,
    generate_cursor_settings,
    generate_noanim
)


def generate_config() -> None:
    output = ""
    for func in funcs:
        name = func.__name__
        output += f"\n# -- {name} --\n"
        output += func()
    with open(generated_config, "w") as f:
        f.write(output)


@sync_debounce(100)
def on_settings_changed(key: str, value: str) -> None:
    generate_config()


class HyprlandConfigService(Service):
    def __init__(self) -> None:
        pass

    def app_init(self) -> None:
        generate_config()

    def start(self) -> None:
        Settings()._signals.watch("changed", on_settings_changed)
