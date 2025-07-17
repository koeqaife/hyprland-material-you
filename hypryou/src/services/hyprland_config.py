from utils import sync_debounce
from utils.service import Service
from utils.logger import logger
from src.services.hyprland_keybinds import key_binds
from src.services.hyprland_keybinds.common import (
    KeyBind, KeyBindHint
)
from config import config_dir, Settings, SettingsView
import os
import typing as t

generated_config = os.path.join(config_dir, "hyprland_generated.conf")

noanim_layers = [
    "hypryou-notifications.*",
    "hypryou-popups.*",
    "hypryou-wallpapers.*"
]

BLUR = """
decoration {{
    blur {{
        enabled = true
        xray = {}
    }}
}}
"""


type HyprlandConfigGroupKeys = list[str | tuple[str, str]]


class HyprlandConfigGroup(t.TypedDict):
    str: HyprlandConfigGroupKeys
    bool: HyprlandConfigGroupKeys
    digit: HyprlandConfigGroupKeys


input_keys = t.cast(HyprlandConfigGroup, {
    "str": [
        "kb_model",
        "kb_layout",
        "kb_variant",
        "kb_rules",
        "accel_profile",
        "scroll_method"
    ],
    "bool": [
        "numlock_by_default",
        "resolve_binds_by_sym",
        "force_no_accel",
        "left_handed",
        "natural_scroll",
        "mouse_refocus"
    ],
    "digit": [
        "repeat_rate",
        "repeat_delay",
        "sensitivity",
        "follow_mouse",
        "follow_mouse_threshold",
        "focus_on_close",
        "float_switch_override_focus"
    ]
})

input_touchpad_keys = t.cast(HyprlandConfigGroup, {
    "str": [
        "tap_button_map",
    ],
    "bool": [
        "disable_while_typing",
        "natural_scroll",
        "middle_button_emulation",
        "clickfinger_behavior",
        ("tap_to_click", "tap-to-click"),
        ("tap_and_drag", "tap-and-drag"),
        "flip_x",
        "flip_y"
    ],
    "digit": [
        "scroll_factor"
    ]
})


def generate_keys(
    keys: HyprlandConfigGroupKeys,
    settings: SettingsView | Settings,
    transform_fn: t.Callable[[t.Any], str] | None = None,
    prefix: str = ""
) -> str:
    output = ""
    for _value in keys:
        if isinstance(_value, tuple):
            key, replace = _value
        else:
            key, replace = _value, _value

        value = settings.get(key)
        transformed = transform_fn(value) if transform_fn else value
        if transformed is not None:
            output += f"{prefix}{replace} = {transformed}\n"
    return output


def bool_convert(value: t.Any) -> str:
    return "true" if value else "false"


def generate_input() -> str:
    indent = "    "
    settings = Settings().get_view_for("input")
    if not settings.get("enabled"):
        return "# Disabled by settings"

    output = "\n"
    output += generate_keys(
        input_keys["str"], settings,
        prefix=indent
    )
    output += generate_keys(
        input_keys["bool"], settings,
        transform_fn=bool_convert,
        prefix=indent
    )
    output += generate_keys(
        input_keys["digit"], settings,
        prefix=indent
    )

    options = str(settings.get("kb_options")).strip()
    change_layout = str(settings.get("change_layout")).strip()
    if change_layout:
        if options:
            options += f", {change_layout}"
        else:
            options = change_layout
    output += f"{indent}kb_options = {options}\n"

    touchpad_settings = settings.get_view_for("touchpad")
    if touchpad_settings.get("enabled"):
        indent2 = indent * 2
        output2 = ""
        output2 += generate_keys(
            input_touchpad_keys["str"], touchpad_settings,
            prefix=indent2
        )
        output2 += generate_keys(
            input_touchpad_keys["bool"], touchpad_settings,
            transform_fn=bool_convert,
            prefix=indent2
        )
        output2 += generate_keys(
            input_touchpad_keys["digit"], touchpad_settings,
            prefix=indent2
        )
        output += f"{indent}touchpad {{\n{output2}{indent}}}\n"
    else:
        output += f"{indent}# Touchpad settings disabled by settings\n"

    return f"input {{{output}}}\n"


def generate_monitors() -> str:
    output = ""
    monitors: list[str] = Settings().get("monitors")
    if len(monitors) == 0:
        output += "monitor = , preferred, auto, 1\n"
    else:
        for monitor in monitors:
            if not isinstance(monitor, str):
                continue
            output += f"monitor = {monitor}\n"
    return output


def generate_blur() -> str:
    settings = Settings()
    blur = settings.get("blur")
    if not blur:
        return "# Blur is disabled by settings \n"

    xray = settings.get("blur_xray")

    output = (
        "layerrule = blur, hypryou-.*",
        "layerrule = ignorealpha 0.85, hypryou-.*",
        BLUR.format("true" if xray else "false")
    )
    return "\n".join(output)


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
    generate_noanim,
    generate_blur,
    generate_input,
    generate_monitors
)


def generate_config() -> None:
    output = "\n".join(
        f"# -- {func.__name__} --\n{func()}" for func in funcs
    )

    try:
        with open(generated_config, "r") as f:
            current_content = f.read()
    except FileNotFoundError:
        current_content = ""

    if current_content != output:
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
