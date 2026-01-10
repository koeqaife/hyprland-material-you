from src.modules.settings.base import SettingsBoolRow, SettingsTextRow
from src.modules.settings.base import Category
from src.modules.settings.base import int_kwargs, float_kwargs
from repository import gtk


percent_min_85_kwargs = {
    "transform_fn": lambda v: str(round(float(v) * 100)),
    "transform2_fn": lambda v: min(max(float(v) / 100, 0.85), 1.0),
    "test_text": lambda v: v.isdigit()
}

percent_kwargs = {
    "transform_fn": lambda v: str(round(float(v) * 100)),
    "transform2_fn": lambda v: min(max(float(v) / 100, 0.0), 1.0),
    "test_text": lambda v: v.isdigit()
}


class EffectsPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsEffectsPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("effects-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        self.children = (
            Category("Blur"),
            SettingsBoolRow(
                "Enabled",
                "Adds blur to windows and to UI",
                "blur.enabled"
            ),
            SettingsBoolRow(
                "XRay",
                "Adds xray effect to blur",
                "blur.xray",
                depends_on={"blur.enabled"}
            ),
            SettingsTextRow(
                "Size",
                "Blur size (distance)",
                "blur.size",
                depends_on={"blur.enabled"},
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Passes",
                "The amount of passes to perform",
                "blur.passes",
                depends_on={"blur.enabled"},
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Noise",
                "The amount of passes to perform",
                "blur.noise",
                depends_on={"blur.enabled"},
                max_width_chars=4,
                **float_kwargs
            ),
            SettingsTextRow(
                "Contrast",
                "Contrast modulation for blur",
                "blur.contrast",
                depends_on={"blur.enabled"},
                max_width_chars=3,
                **float_kwargs
            ),
            SettingsTextRow(
                "Vibrancy",
                "Increase saturation of blurred colors.",
                "blur.vibrancy",
                depends_on={"blur.enabled"},
                max_width_chars=3,
                **float_kwargs
            ),
            SettingsTextRow(
                "Vibrancy darkness",
                "How strong the effect of 'Vibrancy' is on dark areas",
                "blur.vibrancy_darkness",
                depends_on={"blur.enabled"},
                max_width_chars=3,
                **float_kwargs
            ),

            Category("Opacity"),
            SettingsTextRow(
                "UI",
                "Opacity of UI (minimum: 85%)",
                "opacity",
                right_icon="percent",
                max_length=3,
                **percent_min_85_kwargs
            ),
            SettingsTextRow(
                "Active windows",
                "Opacity of active windows",
                "opacity.active",
                right_icon="percent",
                max_length=3,
                **percent_kwargs
            ),
            SettingsTextRow(
                "Inactive windows",
                "Opacity of inactive windows",
                "opacity.inactive",
                right_icon="percent",
                max_length=3,
                **percent_kwargs
            ),
            SettingsTextRow(
                "Fullscreen windows",
                "Opacity of fullscreen windows",
                "opacity.fullscreen",
                right_icon="percent",
                max_length=3,
                **percent_kwargs
            ),

            Category("Rounded corners"),
            SettingsTextRow(
                "Rounding",
                "Rounded corners' radius (in layout px)",
                "hyprland.decoration.rounding",
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Rounding Power",
                "Adjusts the curve used for rounding corners",
                "hyprland.decoration.rounding_power",
                max_width_chars=3,
                **float_kwargs
            ),

            Category("Shadow"),
            SettingsBoolRow(
                "Enabled",
                "Enable drop shadows on windows",
                "shadow.enabled"
            ),
            SettingsTextRow(
                "Range",
                "Shadow range (“size”) in layout px",
                "shadow.range",
                depends_on={"shadow.enabled"},
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Render power",
                "In what power to render the falloff",
                "shadow.render_power",
                depends_on={"shadow.enabled"},
                max_width_chars=3,
                **int_kwargs
            ),
            SettingsTextRow(
                "Color",
                "Shadow's color (hex without #)",
                "shadow.color",
                depends_on={"shadow.enabled"},
                max_width_chars=8
            ),
            SettingsTextRow(
                "Offset X",
                "Shadow's rendering offset on X axis",
                "shadow.offset_x",
                depends_on={"shadow.enabled"},
                max_width_chars=3,
                **float_kwargs
            ),
            SettingsTextRow(
                "Offset Y",
                "Shadow's rendering offset on Y axis",
                "shadow.offset_y",
                depends_on={"shadow.enabled"},
                max_width_chars=3,
                **float_kwargs
            ),
            SettingsTextRow(
                "Scale",
                "Shadow's scale",
                "shadow.scale",
                depends_on={"shadow.enabled"},
                max_width_chars=3,
                **float_kwargs
            ),
        )
        for child in self.children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.children:
            child.destroy()
