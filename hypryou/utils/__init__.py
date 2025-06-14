import utils.ref as ref
import utils.format as format
import utils.downloader as downloader
import utils.colors as colors

from utils.ref import Ref
from utils.logger import setup_logger
from utils.styles import (
    apply_css,
    reload_css,
    compile_scss,
    toggle_css_class
)
from utils.format import (
    get_formatted_date,
    get_formatted_time,
    escape_markup,
    get_full_date,
    format_seconds,
    capitalize_first
)
from utils.debounce import (
    sync_debounce, debounce
)

__all__ = [
    "cliphist",
    "widget",
    "Ref",
    "ref",
    "setup_logger",
    "apply_css",
    "reload_css",
    "compile_scss",
    "get_formatted_date",
    "get_formatted_time",
    "get_full_date",
    "toggle_css_class",
    "format",
    "debounce",
    "downloader",
    "escape_markup",
    "colors",
    "format_seconds",
    "sync_debounce",
    "capitalize_first"
]
