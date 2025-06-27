from repository import gtk, gdk
import subprocess
from config import (
    styles_output, main_scss,
    scss_variables, HyprlandVars,
    TEMP_PATH, color_templates,
    Settings
)
from src.variables import Globals
from utils.logger import logger


def apply_css() -> None:
    if hasattr(Globals, "css_provider"):
        return
    compile_scss()

    if __debug__:
        logger.debug("Creating css provider")
    provider = gtk.CssProvider()

    if __debug__:
        logger.debug("Loading css")
    provider.load_from_path(styles_output)

    gtk.StyleContext.add_provider_for_display(
        gdk.Display.get_default(),
        provider,
        gtk.STYLE_PROVIDER_PRIORITY_USER
    )

    Globals.css_provider = provider


def reload_css() -> None:
    if not hasattr(Globals, "css_provider"):
        return apply_css()

    compile_scss()
    if __debug__:
        logger.debug("Reloading css")
    Globals.css_provider.load_from_path(styles_output)
    if __debug__:
        logger.debug("Reloading css done")


def generate_scss_variables() -> None:
    variables = {
        "hyprlandRounding": f"{HyprlandVars.rounding}px",
        "hyprlandGap": f"{HyprlandVars.gap}px",
        "layerOpacity": f"{Settings().get("opacity")}"
    }
    with open(scss_variables, 'w') as f:
        for key, value in variables.items():
            f.write(f"${key}: {value};\n")


def compile_scss() -> None:
    if __debug__:
        logger.debug("Compiling scss")
    generate_scss_variables()
    command = [
        'sass',
        f'--load-path={color_templates}',
        f'--load-path={TEMP_PATH}',
        main_scss,
        styles_output
    ]

    subprocess.run(command, check=True)


def toggle_css_class(
    widget: gtk.Widget,
    css_class: str,
    condition: bool | None = None
) -> None:
    widget_css_names = widget.get_css_classes()

    if condition is None:
        if css_class in widget_css_names:
            widget.remove_css_class(css_class)
        else:
            widget.add_css_class(css_class)
    else:
        if css_class in widget_css_names and not condition:
            widget.remove_css_class(css_class)
        if css_class not in widget_css_names and condition:
            widget.add_css_class(css_class)
