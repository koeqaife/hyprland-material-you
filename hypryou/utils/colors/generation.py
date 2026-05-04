from utils_cy.helpers import downsample_image_rgb
import os
import hashlib
from os.path import join
from ..vscode_theme import copy_extension
from ..fish_themer import update_fish_themes
import typing as t
import json
import threading
import concurrent.futures
from config import color_templates, ASSETS_DIR, CONFIG_DIR
from config import config_dir, TEMP_DIR
from utils.logger import logger
from repository import gio, glib
from config import Settings
from pathlib import Path
from utils.styles import reload_css
if t.TYPE_CHECKING:
    import subprocess

from .templates import generate_templates
from .schemes import ColorScheme, SchemeName, scheme_from_name
from .cache import save_scheme, load_scheme

executor: concurrent.futures.ProcessPoolExecutor | None = None

TEMPLATES_DIR = join(ASSETS_DIR, "templates")
USER_TEMPLATES_DIR = join(config_dir, "templates")
USER_COLORS_FILE = join(config_dir, "colors.json")

GTK3_PATH = join(CONFIG_DIR, "gtk-3.0")
GTK4_PATH = join(CONFIG_DIR, "gtk-4.0")

gtk3_css = join(color_templates, "compiled", "gtk-3.0.css")
gtk4_css = join(color_templates, "compiled", "gtk-4.0.css")

task_lock = threading.Lock()


def process_image(
    image_path: str,
    quality: int = 2,
    num_colors: int = 128
) -> int:
    def _get_cache_path(image_path: str) -> str:
        cache_path = join(color_templates, "cached_colors")
        hash_object = hashlib.md5(image_path.encode())
        cache_filename = hash_object.hexdigest() + '.pkl'
        os.makedirs(cache_path, exist_ok=True)
        return join(cache_path, cache_filename)

    def _load_from_cache(cache_path: str) -> t.Any:
        if os.path.exists(cache_path):
            import pickle
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        return None

    def _save_to_cache(cache_path: str, data: t.Any) -> None:
        import pickle
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)

    cache_path = _get_cache_path(image_path)

    cached_result = _load_from_cache(cache_path)
    if cached_result is not None:
        return int(cached_result)

    from materialyoucolor.quantize import QuantizeCelebi  # type: ignore
    from materialyoucolor.score.score import Score  # type: ignore

    pixel_array = downsample_image_rgb(image_path, quality)

    result = QuantizeCelebi(pixel_array, num_colors)

    color = int(Score.score(result)[0])

    _save_to_cache(cache_path, color)

    return color


def update_settings() -> None:
    settings = Settings()
    gsettings = gio.Settings.new("org.gnome.desktop.interface")
    dark_mode = settings.get("appearance.dark_mode")

    if settings.get("themes.gtk3") or settings.get("themes.gtk4"):
        if not dark_mode:
            gsettings.set_string("gtk-theme", "adw-gtk3")
        else:
            gsettings.set_string("gtk-theme", "adw-gtk3-dark")

    if not dark_mode:
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
    contrast_level: int = 0,
    scheme_name: SchemeName = "tonal_spot"
) -> None:
    from materialyoucolor.hct import Hct  # type: ignore

    if use_color is None and image_path is not None:
        color = process_image(image_path, 4, 1024)
    elif use_color is not None and image_path is None:
        color = use_color
    else:
        raise TypeError("Either image_path or use_color should be not None.")

    safe_override: dict[str, dict[str, str]] | None = None
    if os.path.isfile(USER_COLORS_FILE):
        try:
            with open(USER_COLORS_FILE, "r") as f:
                safe_override = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    Scheme = scheme_from_name(scheme_name)
    dark_scheme = Scheme(
        Hct.from_int(color),
        True,
        contrast_level,
        spec_version="2021"
    )
    light_scheme = Scheme(
        Hct.from_int(color),
        False,
        contrast_level,
        spec_version="2021"
    )
    scheme = ColorScheme(
        is_dark, dark_scheme, light_scheme, contrast_level,
        use_color, image_path, scheme_name, safe_override
    )

    save_scheme(scheme)

    allowed_actions = ("compile_scss", "mark")
    post = generate_templates(
        TEMPLATES_DIR,
        color_templates,
        scheme,
        allowed_actions
    )
    if os.path.isdir(USER_TEMPLATES_DIR):
        post.update(generate_templates(
            USER_TEMPLATES_DIR,
            color_templates,
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
                    color_templates,
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

    theme_path = join(color_templates, "theme.tdesktop-theme")
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
    update_settings()
    update_gtk3()
    update_gtk4()
    update_fish_themes()

def generate_colors(
    image_path: str | None = None,
    use_color: int | None = None,
    is_dark: bool = True,
    contrast_level: int = 0,
    on_complete: t.Callable[[], None] | None = None,
    scheme_name: SchemeName = "tonal_spot"
) -> None:
    import functools
    global executor

    def _callback(future: concurrent.futures.Future[None]) -> None:
        try:
            future.result()
            copy_extension() # VS Code theme copying/generating/updating
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
                    contrast_level=contrast_level,
                    scheme_name=scheme_name
                )
            )
            future.add_done_callback(_callback)
        except Exception:
            task_lock.release()
    else:
        logger.warning(
            "Another task is already running, skipping the new task."
        )


def generate_by_settings(
    on_complete: t.Callable[[], None] | None = None,
    force: bool = False
) -> bool:
    settings = Settings().get_view_for("appearance")
    dark_mode = settings.get("dark_mode")
    scheme_name = settings.get("scheme")

    scheme = load_scheme()
    color = str(settings.get("color")).lstrip("#")
    if scheme.is_dark != dark_mode:
        force = True
    if scheme.scheme_name != scheme_name:
        force = True

    if color:
        cached_color = scheme.original_color
        color_int = int(color, 16)
        if color_int != cached_color or force:
            generate_colors(
                None,
                color_int,
                dark_mode,
                contrast_level=scheme.contrast_level,
                on_complete=on_complete,
                scheme_name=scheme_name
            )
            return False
    else:
        wallpaper = str(settings.get("wallpaper"))
        cached_wallpaper = scheme.wallpaper
        if wallpaper != cached_wallpaper or force:
            generate_colors(
                wallpaper,
                None,
                dark_mode,
                contrast_level=scheme.contrast_level,
                on_complete=on_complete,
                scheme_name=scheme_name
            )
            return False
    if on_complete:
        on_complete()
    return True
