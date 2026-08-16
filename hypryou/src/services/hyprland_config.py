import asyncio
from utils.debounce import sync_debounce
from utils.service import Service
from utils.ref import unpack_reactive, Ref
from src.services.hyprland_keybinds import key_binds
from src.services.hyprland_keybinds.common import (
    KeyBind, KeyBindOverride
)
import src.services.hyprland as hyprland
from config import config_dir, Settings, SettingsView
import os
import typing as t

generated_config = os.path.join(config_dir, "hyprland_generated.lua")
keybind_overrides = Ref[dict[str, KeyBindOverride]](
    {}, name="keybind_overrides",
    delayed_init=True
)

noanim_layers = [
    "hypryou-notifications.*",
    "hypryou-popups.*",
    "hypryou-wallpapers.*"
]

type SerializableType = str | bool | int | float | tuple | list
type HyprlandConfig = dict[str, SerializableType | HyprlandConfig]

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
        "tap_to_click",
        "tap_and_drag",
        "flip_x",
        "flip_y"
    ],
    "digit": [
        "scroll_factor"
    ]
})

current_config: HyprlandConfig = {}


def get_category(config: HyprlandConfig, name: str) -> HyprlandConfig:
    if category := config.get(name):
        if isinstance(category, dict):
            return category
        else:
            raise TypeError("Key already exists and it's not dict!")

    new_dict = {}
    config[name] = new_dict
    return new_dict


def set_key(
    config: HyprlandConfig,
    key: str,
    value: SerializableType
) -> None:
    if not isinstance(key, str):
        raise TypeError("Key must be str!")
    if not isinstance(value, (str, bool, int, float, tuple, list)):
        raise TypeError("Bad type of value! Got: " + type(value).__name__)

    if isinstance(key, str) and len(key.strip()) == 0:
        return

    old_value = config.get(key)
    if old_value and not isinstance(old_value, type(value)):
        raise TypeError(
            "Type mismatch in existing key. " +
            f"{type(old_value)} != {type(value)}"
        )

    config[key] = value


def generate_keys(
    keys: HyprlandConfigGroupKeys,
    settings: SettingsView | Settings,
    config: HyprlandConfig
) -> str:
    for _value in keys:
        if isinstance(_value, tuple):
            key, replace = _value
        else:
            key, replace = _value, _value

        value = settings.get(key)
        print(key, replace)
        set_key(config, replace, value)


def bool_convert(value: t.Any) -> str:
    return "true" if value else "false"


def generate_input() -> str:
    settings = Settings().get_view_for("input")
    if not settings.get("enabled"):
        return "-- Disabled by settings"

    input_category = get_category(current_config, "input")
    generate_keys(
        input_keys["str"], settings, input_category
    )
    generate_keys(
        input_keys["bool"], settings, input_category
    )
    generate_keys(
        input_keys["digit"], settings, input_category
    )

    options = str(settings.get("kb_options")).strip()
    change_layout = str(settings.get("change_layout")).strip()
    if change_layout:
        if options:
            options += f", {change_layout}"
        else:
            options = change_layout

    set_key(input_category, "kb_options", options)

    touchpad_settings = settings.get_view_for("touchpad")
    if touchpad_settings.get("enabled"):
        touchpad_category = get_category(input_category, "touchpad")
        generate_keys(
            input_touchpad_keys["str"], touchpad_settings,
            touchpad_category
        )
        generate_keys(
            input_touchpad_keys["bool"], touchpad_settings,
            touchpad_category
        )
        generate_keys(
            input_touchpad_keys["digit"], touchpad_settings,
            touchpad_category
        )


def generate_monitors() -> str:
    output = '\n'
    monitors: list[dict[str, str]] = Settings().get("monitors")
    if len(monitors) != 0:
        for monitor in monitors:
            if not isinstance(monitor, dict):
                continue

            output += "hl.monitor({\n"
            for key, value in monitor.items():
                if not value:
                    continue
                if key == "vrr":
                    value = int(value)
                if key == "disabled":
                    value = bool(value)
                if key == "bitdepth":
                    value = int(value)
                output += f"    {key} = {serialize_value(value)},\n"
            output += "})\n"
    return output


def make_layer_rule(namespace: str, key: str, value: SerializableType) -> str:
    indent = " " * 4
    output = "hl.layer_rule({\n"
    output += f"{indent}match = {{ namespace = \"{namespace}\" }},\n"
    output += f"{indent}{key} = {serialize_value(value)}\n"
    output += "})\n"
    return output


def generate_blur() -> str | None:
    settings = Settings().get_view_for("blur")
    if not settings.get("enabled"):
        return

    xray = settings.get("xray")

    output = (
        make_layer_rule("hypryou-.*", "blur", True),
        make_layer_rule("hypryou-.*", "xray", True),
        make_layer_rule("hypryou-.*", "ignore_alpha", 0.85)
    )
    blur_category = get_category(
        get_category(current_config, "decoration"),
        "blur"
    )
    set_key(blur_category, "xray", xray)
    set_key(blur_category, "size", settings.get("size"))
    set_key(blur_category, "passes", settings.get("passes"))
    set_key(blur_category, "noise", settings.get("noise"))
    set_key(blur_category, "contrast", settings.get("contrast"))
    set_key(
        blur_category, "vibrancy_darkness",
        settings.get("vibrancy_darkness")
    )
    set_key(blur_category, "vibrancy", settings.get("vibrancy"))

    return "\n".join(output)


def serialize_value(value: SerializableType) -> str | None:
    if isinstance(value, bool):
        return bool_convert(value)
    if isinstance(value, (int, float)):
        return f"{value}"
    if isinstance(value, str):
        return f"\"{value}\""

    if isinstance(value, (list, tuple)):
        output = []
        for element in value:
            serialized = serialize_value(element)
            if serialized is not None:
                output.append(serialized)
        return "{" + ", ".join(output) + "}"

    return None


def generate_insides_config(
    config: HyprlandConfig,
    indent: str
) -> str:
    output = ""
    for key, value in config.items():
        if isinstance(value, dict):
            output += f"{indent}{key} = " + "{\n"
            output += generate_insides_config(value, indent + " " * 4)
            output += f"{indent}" + "},\n"
            continue

        value = serialize_value(value)
        if not value:
            continue

        output += f"{indent}{key} = {value},\n"

    return output


def generate_hl_config() -> str:
    indent = " " * 4
    output = generate_insides_config(current_config, indent)

    return f"hl.config({{\n{output.strip("\n")}\n}})\n"


def generate_shadow() -> None:
    settings = Settings().get_view_for("shadow")
    if not settings.get("enabled"):
        return

    shadow_category = get_category(
        get_category(current_config, "decoration"),
        "blur"
    )
    set_key(shadow_category, "range", settings.get("range"))
    set_key(shadow_category, "render_power", settings.get("render_power"))
    set_key(shadow_category, "color", f"0x{settings.get("color")}")
    set_key(
        shadow_category, "offset",
        (settings.get("offset_x"), settings.get("offset_y"))
    )
    set_key(shadow_category, "scale", settings.get("scale"))


def generate_opacity() -> None:
    settings = Settings().get_view_for("opacity")
    decoration_category = get_category(current_config, "decoration")
    for key in ("active", "inactive", "fullscreen"):
        set_key(decoration_category, f"{key}_opacity", settings.get(key))


def generate_noanim() -> str:
    return "\n".join(
        make_layer_rule(layer, "no_anim", True)
        for layer in noanim_layers
    ) + "\n"


def generate_cursor_settings() -> str:
    settings = Settings()
    cursor = settings.get("cursor.name")
    cursor_size = settings.get("cursor.size")

    return (
        f"hl.env(\"XCURSOR_SIZE\", {cursor_size})\n" +
        f"hl.exec_cmd(\"hyprctl setcursor {cursor} {cursor_size}\")\n"
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
        if not isinstance(bind, KeyBind):
            continue

        key = bind.bind
        action_str = bind.action
        if bind.id in keybind_overrides.value.keys():
            override = keybind_overrides.value[bind.id]
            if override.bind:
                key = override.bind
            if override.action:
                action_str = override.action

        if isinstance(key, tuple):
            key_str = serialize_value(" + ".join(key))
        else:
            key_str = serialize_value(key)

        if "%N%" in key_str:
            for k in range(0, 10):
                n = k if k != 0 else 10
                _key = key_str.replace("%N%", str(k))
                _action = action_str.replace("%N%", str(n))
                bind_str = f"{_key}, {_action}"
                output += f"hl.bind({bind_str})\n"
        else:
            bind_str = f"{key_str}, {action_str}"
            if "mouse" in key_str:
                output += f"hl.bind({bind_str}, {{ mouse = true }})\n"
            else:
                output += f"hl.bind({bind_str})\n"

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
        output += "-- Apps env vars were disabled by settings\n"
    lines = [
        f"hl.env(\"{key}\", \"{value}\")"
        for key, value in env_vars.items()
    ]
    if len(lines) > 0:
        output += "\n".join(lines) + "\n"
    return output


def generate_general() -> None:
    settings = Settings().get_view_for("hyprland")
    snap = settings.get_view_for("snap")

    general_category = get_category(current_config, "general")
    for key in ("gaps_in", "gaps_out", "border_size", "layout"):
        set_key(general_category, key, settings.get(key))

    snap_category = get_category(general_category, "snap")
    for key in ("enabled", "window_gap", "monitor_gap",
                "border_overlap", "respect_gaps"):
        value = snap.get(key)
        set_key(snap_category, key, value)
        if key == "enabled" and not value:
            break


def generate_misc() -> None:
    settings = Settings().get_view_for("hyprland.misc")
    misc = get_category(current_config, "misc")
    for key in ("vrr", "middle_click_paste"):
        set_key(misc, key, settings.get(key))


def generate_decoration() -> None:
    settings = Settings().get_view_for("hyprland.decoration")
    decoration = get_category(current_config, "decoration")
    for key in ("rounding", "rounding_power"):
        set_key(decoration, key, settings.get(key))


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
    generate_misc,
    generate_shadow,
    generate_opacity,
    generate_hl_config
)


def generate_config() -> None:
    global current_config
    current_config = {}

    output = "-- DO NOT CHANGE THIS FILE, CHECK HYPRYOU SETTINGS\n"
    output += "-- FOR CUSTOM CONFIG USE hyprland.conf\n\n"
    for func in funcs:
        func_output = func()
        if func_output:
            output += f"-- -- {func.__name__} --\n{func_output}\n"

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

    async def check_errors(self) -> None:
        await asyncio.sleep(2.5)
        config_errors = (await hyprland.client.raw("configerrors")).strip()
        if config_errors:
            await hyprland.client.raw("reload")

    def start(self) -> None:
        asyncio.create_task(self.check_errors())
