import Gtk from "gi://Gtk?version=3.0";

export const TextView = Widget.subclass<typeof Gtk.TextView, Gtk.TextView.ConstructorProperties>(Gtk.TextView, "AgsTextView");
