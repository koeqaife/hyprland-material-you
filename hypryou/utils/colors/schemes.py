from materialyoucolor.dynamiccolor.material_dynamic_colors import DynamicColor  # type: ignore # noqa
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors  # noqa
from materialyoucolor.scheme.dynamic_scheme import DynamicScheme  # type: ignore # noqa
import importlib
from .helpers import rgb_to_hex, snake_to_pascal
import typing as t

type SchemeName = t.Literal[
    "content", "expressive", "fidelity",
    "fruit_salad", "monochrome", "neutral",
    "rainbow", "tonal_spot", "vibrant"
]
schemes: tuple[SchemeName] = (
    "content", "expressive", "fidelity",
    "fruit_salad", "monochrome", "neutral",
    "rainbow", "tonal_spot", "vibrant"
)


def scheme_from_name(scheme_name: SchemeName) -> type[DynamicScheme]:
    class_name = f"Scheme{snake_to_pascal(scheme_name)}"
    module_name = f"materialyoucolor.scheme.scheme_{scheme_name}"
    module = importlib.import_module(module_name)
    scheme = getattr(module, class_name)
    return scheme


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
        "contrast_level", "scheme_name",
        "_cached_all"
    )

    def __init__(
        self,
        is_dark: bool,
        dark: DynamicScheme | dict[str, str],
        light: DynamicScheme | dict[str, str],
        contrast_level: int,
        original_color: int | None = None,
        wallpaper: str | None = None,
        scheme_name: str | None = None,
        safe_override: dict[str, dict[str, str]] | None = None
    ) -> None:
        if isinstance(dark, DynamicScheme):
            dark = get_colors(dark)
        if isinstance(light, DynamicScheme):
            light = get_colors(light)

        if safe_override:
            if isinstance(safe_override.get("dark"), dict):
                dark.update(safe_override["dark"])
            if isinstance(safe_override.get("light"), dict):
                light.update(safe_override["light"])

        self.is_dark = is_dark
        self.dark = dark
        self.light = light
        self.wallpaper = wallpaper
        self.original_color = original_color
        self.contrast_level = contrast_level
        self.scheme_name = scheme_name
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
