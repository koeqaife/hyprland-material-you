from repository import gtk

# This file I made for global variables
# It's just more convenient when everything in 1 class

__all__ = [
    "Globals"
]


class Globals:
    app: gtk.Application
    css_provider: gtk.CssProvider
