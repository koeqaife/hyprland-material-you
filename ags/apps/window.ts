import Gtk from "gi://Gtk?version=3.0";

export const RegularWindow = Widget.subclass<typeof Gtk.Window, Gtk.Window.ConstructorProperties>(Gtk.Window);
