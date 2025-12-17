import os
import json
import threading
import concurrent.futures
from materialyoucolor.dynamiccolor.material_dynamic_colors import DynamicColor  # type: ignore # noqa
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors  # noqa
from materialyoucolor.scheme.dynamic_scheme import DynamicScheme  # type: ignore # noqa
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot  # type: ignore # noqa
import hashlib
import re
import typing as t
from config import color_templates, ASSETS_DIR, CONFIG_DIR
from config import config_dir, TEMP_DIR
from utils.logger import logger
from utils.ref import Ref
from repository import gio, glib
from config import Settings
from pathlib import Path
from os.path import join
from utils.styles import reload_css
from utils_cy.helpers import downsample_image_rgb
if t.TYPE_CHECKING:
    import subprocess

# I dropped support of color schemes
# Because it's just easier when there's only 1 of them

executor: concurrent.futures.ProcessPoolExecutor | None = None


TEMPLATES_DIR = join(ASSETS_DIR, "templates")
USER_TEMPLATES_DIR = join(config_dir, "templates")
CACHE_PATH = color_templates

GTK3_PATH = join(CONFIG_DIR, "gtk-3.0")
GTK4_PATH = join(CONFIG_DIR, "gtk-4.0")

gtk3_css = join(CACHE_PATH, "compiled", "gtk-3.0.css")
gtk4_css = join(CACHE_PATH, "compiled", "gtk-4.0.css")

colors_json = join(CACHE_PATH, "colors.json")

dark_mode = Ref(True, name="dark_mode")
task_lock = threading.Lock()


type IntFloat = int | float
type RGB = tuple[IntFloat, IntFloat, IntFloat]
type RGBA = tuple[IntFloat, IntFloat, IntFloat, IntFloat]


def rgb_to_hex(rgb: RGB) -> str:
    return '#{:02x}{:02x}{:02x}'.format(*rgb[:3])


def hex_to_rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip('#')

    if len(hex_color) == 3:
        hex_color = ''.join(ch * 2 for ch in hex_color)

    if len(hex_color) != 6:
        raise ValueError('Invalid hex color format')

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f'{r}, {g}, {b}'


def get_colors(scheme: DynamicScheme) -> dict[str, str]:
    color_map: dict[str, str] = {}

    for color_name, color in vars(MaterialDynamicColors).items():
        if not isinstance(color, DynamicColor):
            continue
        if color_name.endswith("paletteKeyColor"):
            continue

        if color is not None:
            rgba = color.get_hct(scheme).to_rgba()
            color_map[color_name] = rgb_to_hex(rgba)

    return color_map


class ColorScheme:
    __slots__ = (
        "dark", "light", "is_dark",
        "wallpaper", "original_color",
        "contrast_level", "_cached_all"
    )

    def __init__(
        self,
        is_dark: bool,
        dark: DynamicScheme | dict[str, str],
        light: DynamicScheme | dict[str, str],
        contrast_level: int,
        original_color: int | None = None,
        wallpaper: str | None = None
    ) -> None:
        if isinstance(dark, DynamicScheme):
            dark = get_colors(dark)
        if isinstance(light, DynamicScheme):
            light = get_colors(light)

        self.is_dark = is_dark
        self.dark = dark
        self.light = light
        self.wallpaper = wallpaper
        self.original_color = original_color
        self.contrast_level = contrast_level
        self._cached_all: dict[str, str] | None = None

    @property
    def current_colors(self) -> dict[str, str]:
        return self.dark if self.is_dark else self.light

    @property
    def all_colors(self) -> dict[str, str]:
        if self._cached_all:
            return self._cached_all
        schemes = (
            (self.current_colors, ""),
            (self.dark, "Dark"),
            (self.light, "Light")
        )
        color_map: dict[str, str] = {}
        for scheme, suffix in schemes:
            for name, color in scheme.items():
                color_map[f"{name}{suffix}"] = color
        self._cached_all = color_map
        return color_map


def colors_dict(scheme: ColorScheme) -> dict[str, t.Any]:
    dict = {
        "__version__": 1,
        "wallpaper": scheme.wallpaper,
        "dark": scheme.dark,
        "light": scheme.light,
        "original_color": scheme.original_color,
        "contrast_level": scheme.contrast_level,
        "is_dark": scheme.is_dark
    }
    return dict


def restore_colors(colors: dict[str, str]) -> tuple[dict, dict]:
    dark = {}
    light = {}
    for name, color in colors.items():
        if name.endswith("Dark"):
            dark[name.removesuffix("Dark")] = color
        if name.endswith("Light"):
            light[name.removesuffix("Light")] = color
    return dark, light


def get_cache_object(object: dict[str, t.Any] | str) -> ColorScheme:
    if isinstance(object, str):
        object = dict(json.loads(object))

    version = object.get("__version__", 0)
    if version == 0:
        dark, light = restore_colors(object["colors"])
    else:
        dark = object["dark"]
        light = object["light"]
    wallpaper = object["wallpaper"]
    original_color = object["original_color"]
    contrast_level = object.get("contrast_level", 0)
    is_dark = object["is_dark"]

    return ColorScheme(
        is_dark,
        dark,
        light,
        contrast_level,
        original_color,
        wallpaper
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


class TemplateFormatter:
    def __init__(
        self,
        scheme: ColorScheme,
        vars: dict[str, str],
        allowed_actions: tuple[str, ...] | tuple[()] = ()
    ) -> None:
        self.color_map = scheme.all_colors
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
            elif transform.startswith("mix"):
                matched = re.search(
                    r'mix\(([^,]+),\s*(0\.\d+|1(?:\.0*)?)\)',
                    transform
                )
                if not matched:
                    continue
                color_ref = matched.group(1).strip()
                ratio = float(matched.group(2))
                if color_ref in self.color_map:
                    other_color = self.color_map[color_ref]
                elif re.match(
                    r'^#?[0-9a-fA-F]{3,6}$',
                    color_ref
                ):
                    other_color = color_ref
                else:
                    continue

                value = self.mix_colors(value, other_color, ratio)

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

    def mix_colors(self, color1: str, color2: str, ratio: float) -> str:
        color1 = color1.lstrip('#')
        color2 = color2.lstrip('#')

        if len(color1) == 3:
            color1 = ''.join(c * 2 for c in color1)
        if len(color2) == 3:
            color2 = ''.join(c * 2 for c in color2)

        r1, g1, b1 = (
            int(color1[0:2], 16),
            int(color1[2:4], 16),
            int(color1[4:6], 16)
        )
        r2, g2, b2 = (
            int(color2[0:2], 16),
            int(color2[2:4], 16),
            int(color2[4:6], 16)
        )

        r = round(r1 * (1 - ratio) + r2 * ratio)
        g = round(g1 * (1 - ratio) + g2 * ratio)
        b = round(b1 * (1 - ratio) + b2 * ratio)

        return f'#{r:02x}{g:02x}{b:02x}'

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
        matches = re.findall(
            r'(\w+)(?:\(\s*([^)]+?)\s*\))?',
            transformations_str
        )
        result: list[str] = []
        for command, arg in matches:
            if command:
                if arg:
                    result.append(f"{command}({arg})")
                else:
                    result.append(command)
        return result

    def format(self, text: str) -> tuple[str, list[str]]:
        settings = Settings()
        pattern = r'<(?:(\w+):)?(\w+)(?:\.([^>]+?))?>'
        matches = re.finditer(pattern, text)
        result = []
        actions = []
        last_end = 0
        break_on_end = False

        for match in matches:
            full_match = match.group(0)
            tag_type = match.group(1) or ""
            key = match.group(2)
            transformations_str = match.group(3) or ""
            start_index, end_index = match.span(0)
            if start_index == -1:
                continue

            result.append(text[last_end:start_index])
            value = None

            if tag_type == 'var' and key in self.vars:
                value = self.vars[key]
            elif tag_type == 'post' and key in self.post_actions:
                value = f"Post action: {key}"
                actions.append(f"{key}.{transformations_str}")
            elif tag_type == "settings":
                settings_key = f"{key}.{transformations_str}"
                if settings.get(settings_key):
                    value = "Enabled by settings"
                else:
                    value = "Disabled by settings"
                    break_on_end = True
            elif not tag_type and key in self.color_map:
                value = self.color_map[key]

            if value is not None:
                if transformations_str and not tag_type:
                    transformations = self.parse_transformations(
                        transformations_str
                    )
                    value = self.apply_transformations(value, transformations)
                result.append(value)
                last_end = start_index + len(full_match)

            if break_on_end:
                last_end = len(text)
                break

        result.append(text[last_end:])

        str_result = ''.join(result)

        str_result = re.sub(r'<\\\\([^>]+)>', r'<\1>', str_result)

        return str_result, actions


def generate_templates(
    folder: str,
    output_folder: str,
    scheme: ColorScheme,
    allowed_actions: tuple[str, ...] | tuple[()] = ()
) -> dict[str, list[str]]:
    actions: dict[str, list[str]] = {}
    color_scheme = "dark" if scheme.is_dark else "light"

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
            {
                "colorScheme": color_scheme,
                "outputFolder": output_folder,
                "wallpaper": scheme.wallpaper or ""
            },
            allowed_actions
        )
        template, _actions = formatter.format(template)
        new_path = join(output_folder, os.path.basename(file_path))
        with open(new_path, 'w') as f:
            f.write(template)
        if _actions:
            actions[new_path] = _actions

    for file in ready_templates:
        _template = ""
        for name, hex_color in scheme.all_colors.items():
            rgb_color = hex_to_rgb(hex_color)
            new_line = ready_templates[file].format(
                name=name,
                hex=hex_color,
                rgb=rgb_color
            )
            _template += new_line
            if name in additional:
                new_line = ready_templates[file].format(
                    name=additional[name],
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
            import pickle
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        return None

    def save_to_cache(cache_path: str, data: t.Any) -> None:
        import pickle
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)

    cache_path = get_cache_path(image_path)

    cached_result = load_from_cache(cache_path)
    if cached_result is not None:
        return int(cached_result)

    from materialyoucolor.quantize import QuantizeCelebi  # type: ignore
    from materialyoucolor.score.score import Score  # type: ignore

    pixel_array = downsample_image_rgb(image_path, quality)

    result = QuantizeCelebi(pixel_array, num_colors)

    color = int(Score.score(result)[0])

    save_to_cache(cache_path, color)

    return color


def update_settings() -> None:
    settings = Settings()
    gsettings = gio.Settings.new("org.gnome.desktop.interface")

    if settings.get("themes.gtk3") or settings.get("themes.gtk4"):
        if not dark_mode.value:
            gsettings.set_string("gtk-theme", "adw-gtk3")
        else:
            gsettings.set_string("gtk-theme", "adw-gtk3-dark")

    if not dark_mode.value:
        gsettings.set_string("color-scheme", "prefer-light")
        gsettings.set_string("icon-theme", settings.get("icons.light"))
    else:
        gsettings.set_string("color-scheme", "prefer-dark")
        gsettings.set_string("icon-theme", settings.get("icons.dark"))


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
    from materialyoucolor.hct import Hct  # type: ignore

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
    scheme = ColorScheme(
        is_dark, dark_scheme, light_scheme, contrast_level,
        use_color, image_path
    )

    with open(colors_json, 'w') as f:
        json.dump(colors_dict(scheme), f, indent=2)

    allowed_actions = ("compile_scss", "mark")
    post = generate_templates(
        TEMPLATES_DIR,
        CACHE_PATH,
        scheme,
        allowed_actions
    )
    if os.path.isdir(USER_TEMPLATES_DIR):
        post.update(generate_templates(
            USER_TEMPLATES_DIR,
            CACHE_PATH,
            scheme,
            allowed_actions
        ))

    marked: dict[str, str] = {}
    processes: list["subprocess.Popen[bytes]"] = []
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
                processes.append(compile_scss(file_path, output))
            elif action.startswith("mark"):
                name = action.split(".", 1)[1]
                marked[name] = file_path

    post_actions(marked, scheme)

    for proc in processes:
        proc.wait(15)


def generate_telegram_theme(path: str, bg: str) -> None:
    import zipfile
    import pyvips
    image_path = join(TEMP_DIR, "telegram", "background.png")
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    if bg.startswith("#") and len(bg) == 7:
        r = int(bg[1:3], 16)
        g = int(bg[3:5], 16)
        b = int(bg[5:7], 16)
        color = [r, g, b]
    else:
        raise ValueError("Unsupported color format, expected #RRGGBB")

    image = pyvips.Image.black(16, 16).new_from_image(color)
    image.write_to_file(image_path)
    del image

    theme_path = join(CACHE_PATH, "theme.tdesktop-theme")
    with zipfile.ZipFile(theme_path, "w") as zipf:
        zipf.write(path, "colors.tdesktop-theme")
        zipf.write(image_path, "background.png")

    os.remove(image_path)


def post_actions(marked: dict[str, str], scheme: ColorScheme) -> None:
    if "telegram" in marked.keys():
        path = marked["telegram"]
        generate_telegram_theme(path, scheme.current_colors["background"])


def compile_scss(path: str, output: str) -> "subprocess.Popen[bytes]":
    import subprocess
    if __debug__:
        logger.debug("Compiling scss: %s", repr(path))
    command = [
        'sass',
        path,
        output
    ]

    return subprocess.Popen(command)


def update_gtk(
    theme_key: str,
    src_path: str,
    dst_dir: str
) -> None:
    import shutil

    if not Settings().get(theme_key):
        return
    if os.path.isfile(src_path):
        src = Path(src_path)
        dst = Path(dst_dir) / "gtk.css"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)


def update_gtk3() -> None:
    update_gtk("themes.gtk3", gtk3_css, GTK3_PATH)


def update_gtk4() -> None:
    update_gtk("themes.gtk4", gtk4_css, GTK4_PATH)


def default_on_complete() -> None:
    reload_css()
    sync()
    update_settings()
    update_gtk3()
    update_gtk4()


def generate_colors(
    image_path: str | None = None,
    use_color: int | None = None,
    is_dark: bool = True,
    contrast_level: int = 0,
    on_complete: t.Callable[[], None] | None = None
) -> None:
    import functools
    global executor

    def _callback(future: concurrent.futures.Future[None]) -> None:
        try:
            future.result()
        except Exception as e:
            logger.error("Couldn't generate colors: %s", e, exc_info=e)

        glib.idle_add(default_on_complete)
        if on_complete:
            on_complete()
        if executor is not None:
            executor.shutdown(False)
        task_lock.release()

    if task_lock.acquire(blocking=False):
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
        try:
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
        except Exception:
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
    except (FileNotFoundError, json.JSONDecodeError):
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
    except (FileNotFoundError, json.JSONDecodeError):
        generate_colors(
            None,
            color,
            True,
            0,
            on_complete=on_complete
        )


def generate_by_settings(
    on_complete: t.Callable[[], None] | None = None,
    force: bool = False
) -> bool:
    try:
        settings = Settings()
        with open(colors_json) as f:
            content = get_cache_object(f.read())
        color = str(settings.get("color")).lstrip("#")
        if color:
            cached_color = content.original_color
            color_int = int(color, 16)
            if color_int != cached_color or force:
                generate_by_color(color_int, on_complete=on_complete)
                return False
        else:
            wallpaper = str(settings.get("wallpaper"))
            cached_wallpaper = content.wallpaper
            if wallpaper != cached_wallpaper or force:
                generate_by_wallpaper(wallpaper, on_complete=on_complete)
                return False
        dark_mode.value = content.is_dark
        if on_complete:
            on_complete()
        return True
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        restore_palette()
        return False


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
    except (FileNotFoundError, AssertionError, json.JSONDecodeError):
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
        dark_mode.value = is_dark
        generate_colors(
            content.wallpaper,
            content.original_color,
            is_dark,
            content.contrast_level,
            on_complete=on_complete
        )
    except (FileNotFoundError, json.JSONDecodeError):
        generate_colors(
            None,
            0x0000FF,
            is_dark,
            0,
            on_complete=on_complete
        )


def sync() -> ColorScheme | None:
    try:
        with open(colors_json) as f:
            content = get_cache_object(f.read())
        dark_mode.value = content.is_dark
        return content
    except (FileNotFoundError, json.JSONDecodeError):
        restore_palette()
        return None
