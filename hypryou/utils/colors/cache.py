import typing as t
import json
from config import color_templates
from os.path import join
from .schemes import ColorScheme

colors_json = join(color_templates, "colors.json")


def _colors_dict(scheme: ColorScheme) -> dict[str, t.Any]:
    dict = {
        "__version__": 1,
        "wallpaper": scheme.wallpaper,
        "dark": scheme.dark,
        "light": scheme.light,
        "original_color": scheme.original_color,
        "contrast_level": scheme.contrast_level,
        "is_dark": scheme.is_dark,
        "scheme": scheme.scheme_name
    }
    return dict


def _restore_colors(colors: dict[str, str]) -> tuple[dict, dict]:
    dark = {}
    light = {}
    for name, color in colors.items():
        if name.endswith("Dark"):
            dark[name.removesuffix("Dark")] = color
        if name.endswith("Light"):
            light[name.removesuffix("Light")] = color
    return dark, light


def save_scheme(scheme: ColorScheme) -> None:
    with open(colors_json, 'w') as f:
        json.dump(_colors_dict(scheme), f, indent=2)


def load_scheme() -> ColorScheme:
    with open(colors_json) as f:
        return get_cache_object(f.read())


def get_cache_object(object: dict[str, t.Any] | str) -> ColorScheme:
    if isinstance(object, str):
        object = dict(json.loads(object))

    version = object.get("__version__", 0)
    if version == 0:
        dark, light = _restore_colors(object["colors"])
    else:
        dark = object["dark"]
        light = object["light"]
    wallpaper = object["wallpaper"]
    original_color = object["original_color"]
    contrast_level = object.get("contrast_level", 0)
    is_dark = object["is_dark"]
    scheme = object.get("scheme")

    return ColorScheme(
        is_dark,
        dark,
        light,
        contrast_level,
        original_color,
        wallpaper,
        scheme
    )
