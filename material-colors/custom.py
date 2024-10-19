from materialyoucolor.scheme.dynamic_scheme import DynamicSchemeOptions, DynamicScheme  # type: ignore # noqa
from materialyoucolor.scheme.variant import Variant  # type: ignore # noqa
from materialyoucolor.palettes.tonal_palette import TonalPalette  # type: ignore # noqa
from materialyoucolor.utils.math_utils import sanitize_degrees_double  # type: ignore # noqa

"""
This file is just an example, you can change anything you want here.
Do not rename the class SchemeCustom!!!
"""


class SchemeCustom(DynamicScheme):
    def __init__(self, source_color_hct, is_dark, contrast_level):
        super().__init__(
            DynamicSchemeOptions(
                source_color_argb=source_color_hct.to_int(),
                variant="custom",
                contrast_level=contrast_level,
                is_dark=is_dark,
                primary_palette=TonalPalette.from_hue_and_chroma(
                    source_color_hct.hue, 45
                ),
                secondary_palette=TonalPalette.from_hue_and_chroma(
                    sanitize_degrees_double(source_color_hct.hue + 10), 15
                ),
                tertiary_palette=TonalPalette.from_hue_and_chroma(
                    sanitize_degrees_double(source_color_hct.hue + 30), 12
                ),
                neutral_palette=TonalPalette.from_hue_and_chroma(
                    source_color_hct.hue, 3
                ),
                neutral_variant_palette=TonalPalette.from_hue_and_chroma(
                    source_color_hct.hue, 3
                ),
            )
        )
