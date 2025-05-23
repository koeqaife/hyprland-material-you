import gi
from ctypes import CDLL

CDLL('libgtk4-layer-shell.so')

gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
gi.require_version('Gtk4SessionLock', '1.0')
gi.require_version('NM', '1.0')
