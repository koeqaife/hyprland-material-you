from utils.debounce import sync_debounce
from utils.service import Service
from utils.logger import logger
from utils.ref import unpack_reactive, Ref
from src.services.hyprland_keybinds import key_binds
from src.services.hyprland_keybinds.common import (
    KeyBind, KeyBindHint, KeyBindOverride
)
from config import config_dir, Settings, SettingsView
import os
import typing as t

generated_config = os.path.join(config_dir, "hyprland_generated.conf")
keybind_overrides = Ref[dict[str, KeyBindOverride]](
    {}, name="keybind_overrides",
    delayed_init=True
)

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
    monitors: list[dict[str, str]] = Settings().get("monitors")
    if len(monitors) == 0:
        output += "monitor = , preferred, auto, 1\n"
    else:
        for monitor in monitors:
            if isinstance(monitor, str):
                output += f"monitor = {monitor}\n"
                continue
            if not isinstance(monitor, dict):
                continue

            output += "monitorv2 {\n"
            for key, value in monitor.items():
                if not value:
                    continue
                output += f"    {key} = {value}\n"
            output += "}\n"
    return output


def generate_blur() -> str:
    settings = Settings()
    blur = settings.get("blur.enabled")
    if not blur:
        return "# Blur is disabled by settings \n"

    xray = settings.get("blur.xray")

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
    cursor = settings.get("cursor.name")
    cursor_size = settings.get("cursor.size")

    return (
        f"env = XCURSOR_SIZE,{cursor_size}\n" +
        f"exec-once = hyprctl setcursor {cursor} {cursor_size}\n"
    )


type KeybindOverridesRaw = list[dict[str, list[str] | str]]


def generate_overrides(raw: KeybindOverridesRaw) -> dict[str, KeyBindOverride]:
    overrides: dict[str, KeyBindOverride] = {}
    for override in raw:
        if not isinstance(override, dict):
            continue
        if not isinstance(override.get("id"), str):
            continue
        if (
            "bind" in override.keys()
            and not isinstance(override["bind"], list)
            and len(override["bind"]) > 3
        ):
            continue
        bind = unpack_reactive(override.get("bind"))
        action = unpack_reactive(override.get("action"))
        overrides[str(override["id"])] = KeyBindOverride(
            id=str(override["id"]),
            bind=(
                tuple(bind)
                if bind is not None
                else None
            ),
            action=(
                tuple(override["action"])
                if isinstance(action, list)
                else str(action)
                if action is not None
                else None
            )
        )
    return overrides


def generate_binds() -> str:
    output = ""

    for bind in key_binds:
        if isinstance(bind, KeyBindHint):
            continue
        elif not isinstance(bind, KeyBind):
            continue

        key = bind.bind
        action = bind.action
        if bind.id in keybind_overrides.value.keys():
            override = keybind_overrides.value[bind.id]
            if override.bind:
                key = override.bind
            if override.action:
                action = override.action

        if len(key) == 2:
            key_str = ", ".join(key)
        elif len(key) == 3:
            key_str = f"{key[0]} {key[1]}, {key[2]}"
        elif len(key) == 1:
            key_str = f",{key[0]}"
        else:
            logger.warning(f"Bind {bind} has wrong length of bind")
            continue

        if isinstance(action, tuple):
            action_str = ", ".join(action)
        else:
            action_str = action
        bind_str = f"{key_str}, {action_str}"
        if "mouse" in key_str:
            output += f"bindm = {bind_str}\n"
        else:
            output += f"bind = {bind_str}\n"

    return output


def generate_env() -> str:
    settings = Settings()
    env_vars = {}
    output = ""
    if settings.get("apps.enabled"):
        env_vars = {
            "BROWSER": settings.get("apps.browser"),
            "TERMINAL": settings.get("apps.terminal"),
            "EDITOR": settings.get("apps.editor"),
            "FILEMANAGER": settings.get("apps.files"),

            "XDG_UTILS_BROWSER": settings.get("apps.browser"),
            "XDG_UTILS_TERMINAL": settings.get("apps.terminal"),
            "XDG_UTILS_FILEMANAGER": settings.get("apps.files")
        }
    else:
        output += "# Apps env vars were disabled by settings\n"
    lines = [f"env = {key}, {value}" for key, value in env_vars.items()]
    if len(lines) > 0:
        output += "\n".join(lines) + "\n"
    return output


def generate_general() -> str:
    settings = Settings().get_view_for("hyprland")
    snap = settings.get_view_for("snap")

    output = ""
    for key in ("gaps_in", "gaps_out", "border_size", "layout"):
        output += f"    {key} = {settings.get(key)}\n"

    snap_output = ""
    for key in ("enabled", "window_gap", "monitor_gap",
                "border_overlap", "respect_gaps"):
        _value = snap.get(key)
        value = str(_value).lower() if isinstance(_value, bool) else _value
        snap_output += f"        {key} = {value}\n"
        if key == "enabled" and not _value:
            break
    output += f"    snap {{\n{snap_output}    }}\n"

    return f"general {{\n{output}}}\n"


def generate_misc() -> str:
    settings = Settings().get_view_for("hyprland.misc")
    output = ""
    for key in ("vrr", "middle_click_paste"):
        _value = settings.get(key)
        value = str(_value).lower() if isinstance(_value, bool) else _value
        output += f"   {key} = {value}\n"
    return f"misc {{\n{output}}}\n"


def generate_decoration() -> str:
    settings = Settings().get_view_for("hyprland.decoration")
    output = ""
    for key in ("rounding", "rounding_power"):
        output += f"   {key} = {settings.get(key)}\n"
    return f"decoration {{\n{output}}}\n"


funcs = (
    generate_env,
    generate_binds,
    generate_cursor_settings,
    generate_noanim,
    generate_blur,
    generate_input,
    generate_monitors,
    generate_general,
    generate_decoration,
    generate_misc
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


def keybind_overrides_changed(value: KeybindOverridesRaw) -> None:
    keybind_overrides.value = generate_overrides(value)


class HyprlandConfigService(Service):
    def __init__(self) -> None:
        pass

    def app_init(self) -> None:
        settings = Settings()
        settings._signals.watch("changed", on_settings_changed)
        settings.watch("keybinds_overrides", keybind_overrides_changed, False)
        keybind_overrides_changed(settings.get("keybinds_overrides"))
        keybind_overrides.ready()
        generate_config()
