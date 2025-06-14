from __future__ import annotations

from repository import gtk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hypryou_ui import HyprYou

# This file I made for global variables
# It's just more convenient when everything in 1 class

__all__ = [
    "Globals"
]


class Globals:
    app: "HyprYou"
    css_provider: gtk.CssProvider
