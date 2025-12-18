from materialyoucolor.dynamiccolor.material_dynamic_colors import DynamicColor  # type: ignore # noqa
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors  # noqa
from materialyoucolor.scheme.dynamic_scheme import DynamicScheme  # type: ignore # noqa
from .helpers import rgb_to_hex


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
