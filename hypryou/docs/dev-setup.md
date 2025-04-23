# Dev Setup

For types I recommend to use gengir (<https://github.com/santiagocezar/gengir>)
Types generation command:
> But it can be problematic with mypy (I had to change their .pyi files for fixing mypy errors)  
> You can change files Gtk.pyi, GLib.py, GObject.pyi and Gio.pyi to files from <https://github.com/pygobject/pygobject-stubs/tree/master/src/gi-stubs/repository>
 (use _Gtk4.pyi)

```sh
sudo gengir Gtk-4.0 Gtk4LayerShell-1.0
```

For code quality checking I use `Flake8` and `Mypy` (sometimes mypy --strict).
