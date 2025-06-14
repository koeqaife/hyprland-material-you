import versions

from gi.repository import Gtk as gtk
from gi.repository import Gtk4LayerShell as layer_shell
from gi.repository import Gtk4SessionLock as session_lock
from gi.repository import Gdk as gdk
from gi.repository import Gio as gio
from gi.repository import GLib as glib
from gi.repository import Gsk as gsk
from gi.repository import GdkPixbuf as gdk_pixbuf
from gi.repository import GObject as gobject
from gi.repository import Pango as pango
from gi.repository import NM as nm  # type: ignore [attr-defined]
from gi.repository import AstalBluetooth as bluetooth
from gi.repository import AstalWp as wp

__all__ = [
    "versions", "gtk", "layer_shell",
    "gdk", "gio", "glib", "gsk",
    "gdk_pixbuf", "gobject",
    "pango", "nm", "session_lock",
    "bluetooth", "wp"
]
