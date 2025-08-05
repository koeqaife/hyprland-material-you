from repository import layer_shell, gtk
import weakref
from utils.logger import logger
from src.services.hyprland_keybinds import key_binds
from src.services.hyprland_keybinds.common import Category
from src.services.hyprland_keybinds.common import KeyBind
from src.services.hyprland_keybinds.common import KeyBindHint
import src.widget as widget


ICONS = {
    "super": "keyboard_command_key",
    "shift": "shift",
    "up": "arrow_upward",
    "down": "arrow_downward",
    "right": "arrow_right",
    "left": "arrow_left",
    "space": "space_bar"
}

REPLACE = {
    "slash": "/",
    "minus": "-",
    "plus": "+",
    "period": ".",
    "comma": ",",
    "semicolon": ";",
    "grave": "`",
    "equala": "=",
    "bracketleft": "[",
    "bracketright": "]",
    "backslash": "\\",
    "apostrophe": "'"
}

CATEGORIES = {
    Category.ACTIONS: "action_key",
    Category.TOOLS: "build",
    Category.APPS: "apps",
    Category.WINDOWS: "select_window",
    Category.WORKSPACES: "overview_key",
    Category.MISC: "construction"
}


class KeybindWidget(gtk.Box):
    def __init__(self, keybind: KeyBind | KeyBindHint) -> None:
        super().__init__(
            css_classes=("keybind",)
        )
        self.keybind = keybind
        for i in range(0, len(keybind.bind)):
            key = keybind.bind[i].lower()
            is_end = i >= len(keybind.bind) - 1
            if key in ICONS:
                self.append(
                    widget.Icon(
                        ICONS[key],
                        css_classes=("bind-key",)
                    )
                )
            else:
                if key in REPLACE:
                    key = REPLACE[key]
                self.append(
                    gtk.Label(
                        label=key.capitalize(), css_classes=("bind-key",)
                    )
                )
            if not is_end:
                self.append(gtk.Label(label="+", css_classes=("plus",)))
        self.append(
            gtk.Label(
                label=f" - {keybind.description}",
                css_classes=("description",)
            )
        )


class KeybindsBox(gtk.FlowBox):
    __gtype_name__ = "KeybindsBox"

    def __init__(self) -> None:
        super().__init__(
            css_classes=("keybinds-box",),
            selection_mode=gtk.SelectionMode.NONE,
            hexpand=True,
            max_children_per_line=3,
            row_spacing=2,
            column_spacing=2
        )
        self.boxes: dict[Category, gtk.Box] = {}
        for category, icon in CATEGORIES.items():
            box = gtk.Box(
                css_classes=("category-box",),
                orientation=gtk.Orientation.VERTICAL
            )
            label_box = gtk.Box(
                css_classes=("label-box",)
            )
            _icon = widget.Icon(icon)
            label = gtk.Label(
                label=category,
                css_classes=("category",),
                halign=gtk.Align.START
            )
            label_box.append(_icon)
            label_box.append(label)

            box.append(label_box)
            box.append(gtk.Separator())
            self.boxes[category] = box
            self.append(box)
        for keybind in key_binds:
            if not keybind.description or not keybind.category:
                continue
            _widget = KeybindWidget(keybind)
            self.boxes[keybind.category].append(_widget)

    def destroy(self) -> None:
        ...


class KeybindsWindow(widget.LayerWindow):
    __gtype_name__ = "KeybindsWindow"

    def __init__(self, app: gtk.Application) -> None:
        self.box = gtk.Box(
            hexpand=True,
            vexpand=True
        )
        super().__init__(
            app,
            css_classes=("keybinds",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="keybindings",
            height=1,
            width=1,
            setup_popup=True,
            child=self.box
        )
        self._child: KeybindsBox | None = None

        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("InfoWindow finalized")
            )

    def on_show(self) -> None:
        self._child = KeybindsBox()
        self.box.append(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
        self.box.remove(self._child)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
