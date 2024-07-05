import os
import random
import subprocess
import json
from PIL import Image
import argparse
from materialyoucolor.quantize import QuantizeCelebi  # type: ignore
from materialyoucolor.score.score import Score  # type: ignore
from materialyoucolor.hct import Hct  # type: ignore
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors  # type: ignore
from materialyoucolor.scheme.dynamic_scheme import DynamicScheme  # type: ignore
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot  # type: ignore
from materialyoucolor.scheme.scheme_expressive import SchemeExpressive  # type: ignore
from materialyoucolor.scheme.scheme_fruit_salad import SchemeFruitSalad  # type: ignore
from materialyoucolor.scheme.scheme_monochrome import SchemeMonochrome  # type: ignore
from materialyoucolor.scheme.scheme_rainbow import SchemeRainbow  # type: ignore
from materialyoucolor.scheme.scheme_vibrant import SchemeVibrant  # type: ignore
from materialyoucolor.scheme.scheme_neutral import SchemeNeutral  # type: ignore
from materialyoucolor.scheme.scheme_fidelity import SchemeFidelity  # type: ignore
from materialyoucolor.scheme.scheme_content import SchemeContent  # type: ignore
import hashlib
import pickle
import numpy as np


schemes = {
    "tonalSpot": SchemeTonalSpot,
    "expressive": SchemeExpressive,
    "fruitSalad": SchemeFruitSalad,
    "monochrome": SchemeMonochrome,
    "rainbow": SchemeRainbow,
    "vibrant": SchemeVibrant,
    "neutral": SchemeNeutral,
    "fidelity": SchemeFidelity,
    "content": SchemeContent
}


def join(*args):
    return os.path.join(*args)


home = os.path.expanduser('~')

script_dir = os.path.dirname(os.path.abspath(__file__))
cache_path = f"{home}/.cache/material/"
os.makedirs(cache_path, exist_ok=True)
os.makedirs(f"{home}/.cache/wal/", exist_ok=True)


def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb[:3])


def rgba_to_rgb(rgba):
    return f'{rgba[0]}, {rgba[1]}, {rgba[2]}'


class Color():
    def __init__(self, scheme) -> None:
        self.scheme = scheme

    def __call__(self, name: str):
        color_name = getattr(MaterialDynamicColors, name)
        if hasattr(color_name, "get_hct"):
            return rgb_to_hex(color_name.get_hct(self.scheme).to_rgba())
        else:
            return "#000000"


def update_pywal_colors_with_material_you(scheme: DynamicScheme, wallpaper: str) -> dict:
    color = Color(scheme)
    dict = {
        "wallpaper": wallpaper,
        "alpha": "100",

        "special": {
            "background": color("background"),
            "foreground": color("onBackground"),
            "cursor": color("onBackground")
        },
        "colors": {
            "color0": color("background"),
            "color1": color("onBackground"),
            "color2": color("primary"),
            "color3": color("onPrimary"),
            "color4": color("surfaceContainer"),
            "color5": color("onSurface"),
            "color6": color("error"),
            "color7": color("onError"),
            "color8": color("tertiary"),
            "color9": color("onTertiary"),
            "color10": color("secondary"),
            "color11": color("onSecondary"),
            "color12": color("secondaryContainer"),
            "color13": color("onSecondaryContainer"),
            "color14": color("shadow"),
            "color15": color("outlineVariant")
        }
    }
    return dict


class ColorsCache:
    def __init__(self, colors: DynamicScheme | dict, wallpaper: str, original_color: int) -> None:
        self.colors: dict[str, str] = {}
        self.wallpaper = wallpaper
        self.original_color = original_color
        if isinstance(colors, DynamicScheme):
            for color in vars(MaterialDynamicColors).keys():
                color_name = getattr(MaterialDynamicColors, color)
                if hasattr(color_name, "get_hct"):
                    self.colors[str(color)] = rgb_to_hex(color_name.get_hct(colors).to_rgba())
        else:
            self.colors = colors


def colors_dict(cache: ColorsCache):
    dict = {
        "wallpaper": cache.wallpaper,
        "colors": cache.colors,
        "original_color": cache.original_color
    }
    return dict


def get_cache_object(object: dict | str):
    if isinstance(object, str):
        object = dict(json.loads(object))
    colors = object["colors"]
    wallpaper = object["wallpaper"]
    original_color = object["original_color"]
    return ColorsCache(colors, wallpaper, original_color)


def get_file_list(folder_path):
    file_list = []
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


def generate_templates(folder: str, output_folder: str, scheme: DynamicScheme, color_scheme: str, wallpaper: str = ''):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_list = get_file_list(folder)

    for file_path in file_list:
        with open(file_path) as f:
            template = f.read()
        for color in vars(MaterialDynamicColors).keys():
            color_name = getattr(MaterialDynamicColors, color)
            if hasattr(color_name, "get_hct"):
                rgba = color_name.get_hct(scheme).to_rgba()
                hex_color = rgb_to_hex(rgba)
                rgb_color = rgba_to_rgb(rgba)
                template = template.replace(f"<{color}>", hex_color)
                template = template.replace(f"<{color}.rgb>", rgb_color)
        template = (
            template
            .replace("<color-scheme>", color_scheme)
            .replace("<output-folder>", output_folder)
            .replace("<wallpaper>", wallpaper)
        )
        new_path = join(output_folder, os.path.basename(file_path))
        with open(new_path, 'w') as f:
            f.write(template)

    for file in ready_templates:
        _template = ""
        for color in vars(MaterialDynamicColors).keys():
            color_name = getattr(MaterialDynamicColors, color)
            if hasattr(color_name, "get_hct"):
                rgba = color_name.get_hct(scheme).to_rgba()
                hex_color = rgb_to_hex(rgba)
                rgb_color = rgba_to_rgb(rgba)
                new_line = ready_templates[file].format(
                    name=color,
                    hex=hex_color,
                    rgb=rgb_color
                )
                _template += new_line
                if color in additional:
                    new_line = ready_templates[file].format(
                        name=additional[color],
                        hex=hex_color,
                        rgb=rgb_color
                    )
                    _template += new_line

        new_path = join(output_folder, os.path.basename(file))
        with open(new_path, 'w') as f:
            f.write(_template)



def run_hooks(folder: str):
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_list = get_file_list(folder)
    for file_path in file_list:
        file_name = os.path.basename(file_path)
        if str(file_name).endswith(".py"):
            subprocess.run(['python', '-O', file_path])
        elif str(file_name).endswith(".sh"):
            subprocess.run(['sh', file_path])


def save_updated_colors(updated_colors):
    wal_colors_path = f"{home}/.cache/wal/colors.json"
    with open(wal_colors_path, 'w') as f:
        json.dump(updated_colors, f, indent=4)


def process_image(image_path, quality=2, num_colors=128):
    def get_cache_path(image_path):
        global cache_path
        _cache_path = join(cache_path, "cached_colors")
        hash_object = hashlib.md5(image_path.encode())
        cache_filename = hash_object.hexdigest() + '.pkl'
        os.makedirs(_cache_path, exist_ok=True)
        return join(_cache_path, cache_filename)

    def load_from_cache(cache_path):
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        return None

    def save_to_cache(cache_path, data):
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)

    cache_path = get_cache_path(image_path)
    
    cached_result = load_from_cache(cache_path)
    if cached_result is not None:
        return cached_result
    
    image = Image.open(image_path).convert('RGB')
    
    image_data = np.array(image)
    pixel_array = image_data[::quality, ::quality].reshape(-1, 3)
    
    result = QuantizeCelebi(pixel_array, num_colors)
    
    color = Score.score(result)[0]
    
    save_to_cache(cache_path, color)
    
    return color


def main(color_scheme: str, image_path: str, use_color: int | None = None, scheme: DynamicScheme = schemes["tonalSpot"]):
    is_dark = True if color_scheme == "dark" else False
    if use_color is None:
        color = process_image(image_path, 4, 1024)

    else:
        color = use_color

    scheme = scheme(
        Hct.from_int(color),
        is_dark,
        0.0,
    )
    # for color in vars(MaterialDynamicColors).keys():
    #     color_name = getattr(MaterialDynamicColors, color)
    #     if hasattr(color_name, "get_hct"):
    #         print(color, rgb_to_hex(color_name.get_hct(scheme).to_rgba()))

    with open(join(cache_path, "colors.json"), 'w') as f:
        object = ColorsCache(scheme, image_path, color)
        json.dump(colors_dict(object), f, indent=2)

    updated_pywal_colors = update_pywal_colors_with_material_you(scheme, image_path)

    generate_templates(f"{script_dir}/templates", cache_path, scheme, color_scheme, image_path)
    generate_templates(f"{script_dir}/templates/svg", join(cache_path, "svg/"), scheme, color_scheme, image_path)
    save_updated_colors(updated_pywal_colors)

    subprocess.run(['wal', '-s', '-q', '-e', '-n', '-R'])
    if is_dark:
        subprocess.run(['sh', join(script_dir, 'gtk-material.sh')])
    else:
        subprocess.run(['sh', join(script_dir, 'gtk-material.sh'), '--light'])

    run_hooks(join(script_dir, "hooks"))


def _argparse() -> tuple[bool, bool, str, str, str, str]:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-R", help="Restore previous colorscheme.", action='store_true')
    group.add_argument("-w", help="Use last used wallpaper for color generation.", action='store_true')
    group.add_argument("--image", type=str, help="Image for color scheme generation")
    group.add_argument("--color", type=str, help="Main color for color scheme generation")
    parser.add_argument('--color-scheme', type=str, default='dark', choices=['dark', 'light'],
                        help="Color scheme variant")
    parser.add_argument('--scheme', type=str, default="tonalSpot", choices=list(schemes.keys()),
                        help="Scheme for color generation")

    args = parser.parse_args()

    restore_palette = args.R
    use_last_used_wallpaper = args.w
    image = args.image
    color_scheme = args.color_scheme
    use_color = args.color
    scheme = args.scheme
    return restore_palette, use_last_used_wallpaper, image, color_scheme, use_color, scheme


def _main():
    restore_palette, use_last_used_wallpaper, image, color_scheme, use_color, _scheme = _argparse()
    scheme = schemes[_scheme]
    if use_color is not None:
        try:
            with open(join(cache_path, "colors.json")) as f:
                content = get_cache_object(f.read())
            main(color_scheme, image_path=content.wallpaper, use_color=int(use_color.lstrip('#'), 16), scheme=scheme)
        except:
            main(color_scheme, image_path="/dev/null", use_color=int(use_color.lstrip('#'), 16), scheme=scheme)

    elif restore_palette:
        with open(join(cache_path, "colors.json")) as f:
            content = get_cache_object(f.read())
        main(color_scheme, image_path=content.wallpaper, use_color=content.original_color, scheme=scheme)
    elif use_last_used_wallpaper:
        with open(join(cache_path, "colors.json")) as f:
            content = get_cache_object(f.read()).wallpaper
        main(color_scheme, image_path=content, scheme=scheme)
    else:
        if os.path.isdir(image):
            files = [f for f in os.listdir(image) if f.endswith(('.png', '.jpg', '.jpeg'))]
            if files:
                image = join(image, random.choice(files))
        main(color_scheme, image_path=image, scheme=scheme)


if __name__ == "__main__":
    _main()
