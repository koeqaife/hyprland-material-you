from repository import gtk, gdk, glib
from config import (
    styles_output, main_scss,
    scss_variables,
    TEMP_DIR, color_templates,
    Settings
)
from src.variables import Globals
from utils.logger import logger
import typing as t
import os


def apply_css() -> None:
    if hasattr(Globals, "css_provider"):
        return

    if __debug__:
        logger.debug("Creating css provider")
    provider = gtk.CssProvider()

    gtk.StyleContext.add_provider_for_display(
        gdk.Display.get_default(),
        provider,
        gtk.STYLE_PROVIDER_PRIORITY_USER
    )

    Globals.css_provider = provider

    def load_css(*args: t.Any) -> None:
        if __debug__:
            logger.debug("Loading css")
        provider.load_from_path(styles_output)

    if os.path.isfile(styles_output):
        try:
            load_css()
            return
        except Exception as e:
            logger.exception("Error while loading css", exc_info=e)
    compile_scss(load_css)


def reload_css() -> None:
    if not hasattr(Globals, "css_provider"):
        return apply_css()

    def on_compile(pid: int, status: int, user_data: None) -> None:
        if __debug__:
            logger.debug("Reloading css")
        Globals.css_provider.load_from_path(styles_output)
        if __debug__:
            logger.debug("Reloading css done")
    compile_scss(on_compile)


def generate_scss_variables() -> None:
    hyprland = Settings().get_view_for("hyprland")
    decoration = hyprland.get_view_for("decoration")
    variables = {
        "hyprlandRounding": f"{decoration.get("rounding")}px",
        "hyprlandGap": f"{hyprland.get("gaps_out")}px",
        "layerOpacity": f"{Settings().get("opacity")}"
    }
    with open(scss_variables, 'w') as f:
        for key, value in variables.items():
            f.write(f"${key}: {value};\n")


def compile_scss(
    callback: t.Callable[[int, int, None], None] | None = None
) -> None:
    import subprocess

    if __debug__:
        logger.debug("Compiling scss")
    generate_scss_variables()
    command = [
        'sass',
        f'--load-path={color_templates}',
        f'--load-path={TEMP_DIR}',
        main_scss,
        styles_output
    ]

    proc = subprocess.Popen(command)
    if callable(callback):
        glib.child_watch_add(proc.pid, callback, None)


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
