import functools
import os
import json
import subprocess
import threading
from PIL import Image
import concurrent
import concurrent.futures
from materialyoucolor.quantize import QuantizeCelebi  # type: ignore
from materialyoucolor.score.score import Score  # type: ignore
from materialyoucolor.hct import Hct  # type: ignore
from materialyoucolor.dynamiccolor.material_dynamic_colors import DynamicColor  # type: ignore # noqa
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors  # noqa
from materialyoucolor.scheme.dynamic_scheme import DynamicScheme  # type: ignore # noqa
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot  # type: ignore # noqa
import hashlib
import pickle
import numpy as np
import re
import typing as t
from config import color_templates, CONFIG_DIR
from utils.logger import logger
from utils.styles import reload_css
from utils.ref import Ref
from repository import gio, glib
from config import Settings


# I dropped support of color schemes
# Because it's just easier when there's only 1 of them


join = os.path.join
gsettings = gio.Settings.new("org.gnome.desktop.interface")


TEMPLATES_DIR = join(CONFIG_DIR, "assets", "templates")
CACHE_PATH = color_templates

colors_json = join(CACHE_PATH, "colors.json")

dark_mode = Ref(True, name="dark_mode")
task_lock = threading.Lock()


type IntFloat = int | float
type RGB = tuple[IntFloat, IntFloat, IntFloat]
type RGBA = tuple[IntFloat, IntFloat, IntFloat, IntFloat]


def rgb_to_hex(rgb: RGB) -> str:
    return '#{:02x}{:02x}{:02x}'.format(*rgb[:3])


def rgba_to_rgb(rgba: RGBA) -> str:
    return f'{rgba[0]}, {rgba[1]}, {rgba[2]}'


def get_color(color_name: str) -> DynamicColor | None:
    color = getattr(MaterialDynamicColors, color_name, None)
    if isinstance(color, DynamicColor):
        return color
    else:
        return None


class ColorsCache:
    def __init__(
        self,
        colors: DynamicScheme | dict[str, str],
        wallpaper: str | None,
        original_color: int | None,
        contrast_level: int,
        is_dark: bool,

        colors_dark: DynamicScheme | dict[str, str] | None = None,
        colors_light: DynamicScheme | dict[str, str] | None = None,
    ) -> None:
        self.colors: dict[str, str] = {}
        self.wallpaper = wallpaper
        self.original_color = original_color
        self.contrast_level = contrast_level
        self.is_dark = is_dark

        if isinstance(colors, DynamicScheme):
            for color_name in vars(MaterialDynamicColors).keys():
                color = get_color(color_name)
                if color is None:
                    continue
                self.colors[color_name] = rgb_to_hex(
                    color.get_hct(colors).to_rgba()
                )
        else:
            self.colors = colors

        _schemes = ((colors_dark, "Dark"), (colors_light, "Light"))
        for scheme, suffix in _schemes:
            if scheme is None:
                continue
            if isinstance(scheme, dict):
                for key, value in scheme.items():
                    self.colors[f"{key}{suffix}"] = value
                continue
            for color_name in vars(MaterialDynamicColors).keys():
                color = get_color(color_name)
                if color is None:
                    continue
                self.colors[f"{color_name}{suffix}"] = rgb_to_hex(
                    color.get_hct(colors).to_rgba()
                )


def colors_dict(cache: ColorsCache) -> dict[str, t.Any]:
    dict = {
        "wallpaper": cache.wallpaper,
        "colors": cache.colors,
        "original_color": cache.original_color,
        "contrast_level": cache.contrast_level,
        "is_dark": cache.is_dark
    }
    return dict


def get_cache_object(object: dict[str, t.Any] | str) -> ColorsCache:
    if isinstance(object, str):
        object = dict(json.loads(object))

    colors = object["colors"]
    wallpaper = object["wallpaper"]
    original_color = object["original_color"]
    contrast_level = object.get("contrast_level", 0)
    is_dark = object["is_dark"]

    return ColorsCache(
        colors,
        wallpaper,
        original_color,
        contrast_level,
        is_dark
    )


def get_file_list(folder_path: str) -> list[str]:
    file_list: list[str] = []
    for file in os.listdir(folder_path):
        if os.path.isfile(join(folder_path, file)):
            file_list.append(join(folder_path, file))
    return file_list


ready_templates = {
    "colors.css": "@define-color {name} {hex};\n",
    "colors.scss": "${name}: {hex};\n"
}
additional = {
    "onBackground": "foreground"
}


def generate_color_map(
    scheme: DynamicScheme,
    dark_scheme: DynamicScheme,
    light_scheme: DynamicScheme
) -> dict[str, str]:
    _schemes = (
        (scheme, ""),
        (dark_scheme, "Dark"),
        (light_scheme, "Light")
    )
    color_map: dict[str, str] = {}
    for _color_name in vars(MaterialDynamicColors).keys():
        for _scheme, suffix in _schemes:
            color = get_color(_color_name)
            color_name = f"{_color_name}{suffix}"
            if color is not None:
                rgba = color.get_hct(_scheme).to_rgba()
                color_map[color_name] = rgb_to_hex(rgba)
    return color_map


class TemplateFormatter:
    def __init__(
        self,
        scheme: DynamicScheme,
        dark_scheme: DynamicScheme,
        light_scheme: DynamicScheme,
        vars: dict[str, str],
        allowed_actions: tuple[str] | tuple[()] = ()
    ) -> None:
        self.color_map = generate_color_map(scheme, dark_scheme, light_scheme)
        self.vars = vars
        self.post_actions = allowed_actions

    def apply_transformations(
        self,
        value: str,
        transformations: list[str]
    ) -> str:
        intermediate_transforms = [
            t for t in transformations
            if not (t.startswith("strip") or t == "rgb")
        ]
        final_transforms = [
            t for t in transformations
            if t.startswith("strip") or t == "rgb"
        ]

        for transform in intermediate_transforms:
            if transform.startswith("lighten"):
                matched = re.search(r'\d+', transform)
                if not matched:
                    continue
                percent = int(matched.group())
                value = self.adjust_brightness(value, percent)
            elif transform.startswith("darken"):
                matched = re.search(r'\d+', transform)
                if not matched:
                    continue
                percent = int(matched.group())
                value = self.adjust_brightness(value, -percent)

        for transform in final_transforms:
            if transform.startswith("strip"):
                value = value.lstrip('#')
            elif transform == "rgb":
                value = self.hex_to_rgb(value)

        return value

    def adjust_brightness(
        self,
        hex_color: str,
        factor: IntFloat
    ) -> str:
        def min_max(v: int) -> int:
            return min(255, max(0, v))

        hex_color = hex_color.lstrip('#')
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        r = min_max(int(r * (1 + factor / 100)))
        g = min_max(int(g * (1 + factor / 100)))
        b = min_max(int(b * (1 + factor / 100)))

        return f'#{r:02X}{g:02X}{b:02X}'.lower()

    def hex_to_rgb(
        self,
        hex_color: str
    ) -> str:
        hex_color = hex_color.lstrip('#')
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'{r},{g},{b}'

    def parse_transformations(
        self,
        transformations_str: str
    ) -> list[str]:
        transformations = re.findall(
            r'(\w+)(?:\((\d*)\))?', transformations_str
        )
        result = []
        for command, arg in transformations:
            if command:
                if arg:
                    result.append(f"{command}({arg})")
                else:
                    result.append(command)
        return result

    def format(self, text: str) -> str:
        pattern = r'(<(?:(\w+):)?(\w+)(?:\.(.+))?>)'
        matches = re.findall(pattern, text)
        result = []
        actions = []
        last_end = 0

        for match in matches:
            full_match, tag_type, key, transformations_str = match
            start_index = text.find(full_match, last_end)
            if start_index == -1:
                continue

            result.append(text[last_end:start_index])
            value = None

            if tag_type == 'var' and key in self.vars:
                value = self.vars[key]
            elif tag_type == 'post' and key in self.post_actions:
                value = f"Post action: {key}"
                actions.append(f"{key}.{transformations_str}")
            elif tag_type is None and key in self.color_map:
                value = self.color_map[key]

            if value is not None:
                if transformations_str and tag_type is None:
                    transformations = self.parse_transformations(
                        transformations_str
                    )
                    value = self.apply_transformations(value, transformations)
                result.append(value)
                last_end = start_index + len(full_match)

        result.append(text[last_end:])

        str_result = ''.join(result)

        str_result = re.sub(r'<\\\\([^>]+)>', r'<\1>', str_result)

        return str_result, actions


def generate_templates(
    folder: str,
    output_folder: str,
    scheme: DynamicScheme,
    dark_scheme: DynamicScheme,
    light_scheme: DynamicScheme,
    is_dark: bool,
    wallpaper: str | None = None,
    allowed_actions: tuple[str] | tuple[()] = ()
) -> dict[str, list[str]]:
    actions: dict[str, list[str]] = {}
    color_scheme = "dark" if is_dark else "light"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if not os.path.exists(folder):
        os.makedirs(folder)

    file_list = get_file_list(folder)

    for file_path in file_list:
        with open(file_path) as f:
            template = f.read()
        formatter = TemplateFormatter(
            scheme,
            dark_scheme,
            light_scheme,
            {
                "colorScheme": color_scheme,
                "outputFolder": output_folder,
                "wallpaper": wallpaper or ""
            },
            allowed_actions
        )
        template, _actions = formatter.format(template)
        new_path = join(output_folder, os.path.basename(file_path))
        with open(new_path, 'w') as f:
            f.write(template)
        if _actions:
            actions[new_path] = _actions

    _schemes = (
        (scheme, ""),
        (dark_scheme, "Dark"),
        (light_scheme, "Light")
    )
    for file in ready_templates:
        _template = ""
        for _color_name in vars(MaterialDynamicColors).keys():
            for _scheme, suffix in _schemes:
                color = get_color(_color_name)
                color_name = f"{_color_name}{suffix}"
                if color is None:
                    continue

                rgba = color.get_hct(_scheme).to_rgba()
                hex_color = rgb_to_hex(rgba)
                rgb_color = rgba_to_rgb(rgba)
                new_line = ready_templates[file].format(
                    name=color_name,
                    hex=hex_color,
                    rgb=rgb_color
                )
                _template += new_line
                if color_name in additional:
                    new_line = ready_templates[file].format(
                        name=additional[color_name],
                        hex=hex_color,
                        rgb=rgb_color
                    )
                    _template += new_line

            new_path = join(output_folder, os.path.basename(file))
            with open(new_path, 'w') as f:
                f.write(_template)

    return actions


def process_image(
    image_path: str,
    quality: int = 2,
    num_colors: int = 128
) -> int:
    def get_cache_path(image_path: str) -> str:
        cache_path = join(CACHE_PATH, "cached_colors")
        hash_object = hashlib.md5(image_path.encode())
        cache_filename = hash_object.hexdigest() + '.pkl'
        os.makedirs(cache_path, exist_ok=True)
        return join(cache_path, cache_filename)

    def load_from_cache(cache_path: str) -> t.Any:
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        return None

    def save_to_cache(cache_path: str, data: t.Any) -> None:
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)

    cache_path = get_cache_path(image_path)

    cached_result = load_from_cache(cache_path)
    if cached_result is not None:
        return int(cached_result)

    image = Image.open(image_path).convert('RGB')

    image_data = np.array(image)
    pixel_array = image_data[::quality, ::quality].reshape(-1, 3)

    result = QuantizeCelebi(pixel_array, num_colors)

    color = int(Score.score(result)[0])

    save_to_cache(cache_path, color)

    return color


def update_settings() -> None:
    settings = Settings()

    if not dark_mode.value:
        gsettings.set_string("gtk-theme", "adw-gtk3")
        gsettings.set_string("color-scheme", "prefer-light")
        gsettings.set_string("icon-theme", settings.get("light_icons"))
    else:
        gsettings.set_string("gtk-theme", "adw-gtk3-dark")
        gsettings.set_string("color-scheme", "prefer-dark")
        gsettings.set_string("icon-theme", settings.get("dark_icons"))


@t.overload
def generate_colors_sync(
    image_path: str,
    use_color: t.Literal[None] = None,
    is_dark: bool = True,
    contrast_level: int = 0
) -> None:
    ...


@t.overload
def generate_colors_sync(
    image_path: t.Literal[None],
    use_color: int,
    is_dark: bool = True,
    contrast_level: int = 0
) -> None:
    ...


def generate_colors_sync(
    image_path: str | None = None,
    use_color: int | None = None,
    is_dark: bool = True,
    contrast_level: int = 0
) -> None:
    if use_color is None and image_path is not None:
        color = process_image(image_path, 4, 1024)
    elif use_color is not None and image_path is None:
        color = use_color
    else:
        raise TypeError("Either image_path or use_color should be not None.")

    dark_scheme = SchemeTonalSpot(
        Hct.from_int(color),
        True,
        contrast_level
    )
    light_scheme = SchemeTonalSpot(
        Hct.from_int(color),
        False,
        contrast_level
    )
    scheme = dark_scheme if is_dark else light_scheme

    with open(colors_json, 'w') as f:
        object = ColorsCache(
            scheme, image_path, use_color, contrast_level, is_dark,
            dark_scheme, light_scheme
        )
        json.dump(colors_dict(object), f, indent=2)

    allowed_actions = ("compile_scss")
    post = generate_templates(
        TEMPLATES_DIR,
        CACHE_PATH,
        scheme,
        dark_scheme,
        light_scheme,
        is_dark,
        image_path,
        allowed_actions
    )

    for file_path, actions in post.items():
        for action in actions:
            if action.startswith("compile_scss"):
                command = action.split(".", 1)
                file_name = (
                    command[1]
                    if len(command) > 1
                    else os.path.basename(file_path)
                )
                output = join(
                    CACHE_PATH,
                    "compiled",
                    file_name
                )
                compile_scss(file_path, output)


def compile_scss(path: str, output: str) -> None:
    logger.debug("Compiling scss")
    command = [
        'sass',
        path,
        output
    ]

    subprocess.Popen(command)


def default_on_complete() -> None:
    reload_css()
    sync()
    update_settings()


def generate_colors(
    image_path: str | None = None,
    use_color: int | None = None,
    is_dark: bool = True,
    contrast_level: int = 0,
    on_complete: t.Callable[[], None] | None = None
) -> None:
    def _callback(future: concurrent.futures.Future[None]) -> None:
        try:
            future.result()
        except Exception as e:
            logger.error("Couldn't generate colors: %s", e, exc_info=e)

        glib.idle_add(default_on_complete)
        if on_complete:
            on_complete()

    if task_lock.acquire(blocking=False):
        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as (
                executor
            ):
                future = executor.submit(
                    functools.partial(
                        generate_colors_sync,
                        image_path=image_path,
                        use_color=use_color,
                        is_dark=is_dark,
                        contrast_level=contrast_level
                    )
                )
                future.add_done_callback(_callback)
        finally:
            task_lock.release()
    else:
        logger.warning(
            "Another task is already running, skipping the new task."
        )


def generate_by_wallpaper(
    image_path: str,
    on_complete: t.Callable[[], None] | None = None
) -> None:
    try:
        with open(colors_json) as f:
            content = get_cache_object(f.read())
        generate_colors(
            image_path,
            None,
            content.is_dark,
            contrast_level=content.contrast_level,
            on_complete=on_complete
        )
    except FileNotFoundError:
        generate_colors(
            image_path,
            None,
            True,
            0,
            on_complete=on_complete
        )


def generate_by_color(
    color: int,
    on_complete: t.Callable[[], None] | None = None
) -> None:
    try:
        with open(colors_json) as f:
            content = get_cache_object(f.read())
        generate_colors(
            None,
            color,
            content.is_dark,
            contrast_level=content.contrast_level,
            on_complete=on_complete
        )
    except FileNotFoundError:
        generate_colors(
            None,
            color,
            True,
            0,
            on_complete=on_complete
        )


def generate_by_last_wallpaper(
    on_complete: t.Callable[[], None] | None = None
) -> None:
    try:
        with open(colors_json) as f:
            content = get_cache_object(f.read())
        wallpaper = Settings().get("wallpaper")
        generate_colors(
            wallpaper,
            None,
            content.is_dark,
            contrast_level=content.contrast_level,
            on_complete=on_complete
        )
    except (FileNotFoundError, AssertionError):
        generate_colors(
            None,
            0x0000FF,
            True,
            0,
            on_complete=on_complete
        )


def restore_palette(
    on_complete: t.Callable[[], None] | None = None
) -> None:
    try:
        with open(colors_json) as f:
            content = get_cache_object(f.read())
        assert content.original_color is not None
        generate_colors(
            content.wallpaper,
            content.original_color,
            content.is_dark,
            content.contrast_level,
            on_complete=on_complete
        )
    except (FileNotFoundError, AssertionError):
        generate_colors(
            None,
            0x0000FF,
            True,
            0,
            on_complete=on_complete
        )


def set_dark_mode(
    is_dark: bool,
    on_complete: t.Callable[[], None] | None = None
) -> None:
    try:
        with open(colors_json) as f:
            content = get_cache_object(f.read())
        generate_colors(
            content.wallpaper,
            content.original_color,
            is_dark,
            content.contrast_level,
            on_complete=on_complete
        )
    except (FileNotFoundError, AssertionError):
        generate_colors(
            None,
            0x0000FF,
            is_dark,
            0,
            on_complete=on_complete
        )


def sync() -> None:
    try:
        with open(colors_json) as f:
            content = get_cache_object(f.read())
        dark_mode.value = content.is_dark
    except FileNotFoundError:
        restore_palette()
