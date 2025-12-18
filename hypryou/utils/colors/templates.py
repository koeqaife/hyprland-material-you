import os
import re
from os.path import join
from config import Settings

from .schemes import ColorScheme
from .helpers import IntFloat, hex_to_rgb


ready_templates = {
    "colors.css": "@define-color {name} {hex};\n",
    "colors.scss": "${name}: {hex};\n"
}
additional = {
    "onBackground": "foreground"
}


def get_file_list(folder_path: str) -> list[str]:
    file_list: list[str] = []
    for file in os.listdir(folder_path):
        if os.path.isfile(join(folder_path, file)):
            file_list.append(join(folder_path, file))
    return file_list


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
