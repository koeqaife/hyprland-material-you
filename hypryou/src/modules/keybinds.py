from repository import layer_shell, gtk, gdk
import weakref
import typing as t
from utils.logger import logger
from utils.ref import unpack_reactive
from config import Settings
import src.services.hyprland as hyprland
from src.services.hyprland_config import keybind_overrides
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
    "apostrophe": "'",
    "%n%": "0-9"
}

CATEGORIES = {
    Category.ACTIONS: "action_key",
    Category.TOOLS: "build",
    Category.WINDOWS: "overview_key",
    Category.APPS: "apps",
}

CUSTOM_CATEGORY = "Custom"
CUSTOM_ICON = "keyboard"
# Same length as the longest default category, so custom groups line up
# with the others instead of growing into one long column.
CUSTOM_GROUP_SIZE = 10
# Groups per page: two rows of three on a wide monitor, three rows of two
# on a narrow one. The first page keeps the default categories.
PAGE_SIZE = 6
COLUMNS = 3
# Leaves room for the gaps around the window on the active monitor.
MAX_WIDTH_FRACTION = 0.95

PREVIOUS_PAGE_KEYS = (gdk.KEY_Left, gdk.KEY_Page_Up)
NEXT_PAGE_KEYS = (gdk.KEY_Right, gdk.KEY_Page_Down)


def effective_bind(keybind: KeyBind) -> tuple[str, ...] | None:
    """The keys a default bind is on now, or None if it is turned off."""
    disabled = unpack_reactive(Settings().get("disabled_keybinds"))
    if isinstance(disabled, list) and keybind.id in disabled:
        return None
    bind = keybind.bind
    override = keybind_overrides.value.get(keybind.id)
    if override is not None and override.bind:
        bind = override.bind
    if any(key.upper() in ("NULL", "NONE") for key in bind):
        return None
    return bind


def custom_hints() -> list[KeyBindHint]:
    """Custom binds from the settings, named by their name or command."""
    binds = unpack_reactive(Settings().get("custom_keybinds"))
    if not isinstance(binds, list):
        return []
    hints: list[KeyBindHint] = []
    for bind in binds:
        if not isinstance(bind, dict):
            continue
        keys = [
            key.strip() for key in str(bind.get("bind") or "").split("+")
            if key.strip()
        ]
        command = str(bind.get("command") or "").strip()
        if not keys or not command:
            continue
        name = str(bind.get("name") or "").strip() or command
        hints.append(KeyBindHint(tuple(keys), name))
    return hints


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


def make_category(name: str, icon: str) -> gtk.Box:
    box = gtk.Box(
        css_classes=("category-box",),
        orientation=gtk.Orientation.VERTICAL
    )
    label_box = gtk.Box(
        css_classes=("label-box",)
    )
    label_box.append(widget.Icon(icon))
    label_box.append(
        gtk.Label(
            label=name,
            css_classes=("category",),
            halign=gtk.Align.START
        )
    )
    box.append(label_box)
    box.append(gtk.Separator())
    return box


def make_page() -> gtk.FlowBox:
    return gtk.FlowBox(
        css_classes=("keybinds-box",),
        selection_mode=gtk.SelectionMode.NONE,
        hexpand=True,
        valign=gtk.Align.START,
        max_children_per_line=COLUMNS,
        row_spacing=2,
        column_spacing=2
    )


class KeybindsBox(gtk.Box):
    __gtype_name__ = "KeybindsBox"

    def __init__(self) -> None:
        super().__init__(
            css_classes=("keybinds-pages",),
            orientation=gtk.Orientation.VERTICAL
        )
        boxes: dict[Category, gtk.Box] = {}
        groups: list[gtk.Box] = []
        for category, icon in CATEGORIES.items():
            boxes[category] = make_category(category, icon)
            groups.append(boxes[category])
        for keybind in key_binds:
            if not keybind.description or not keybind.category:
                continue
            if isinstance(keybind, KeyBind):
                bind = effective_bind(keybind)
                if bind is None:
                    continue
                keybind = KeyBindHint(
                    bind, keybind.description, keybind.category
                )
            boxes[keybind.category].append(KeybindWidget(keybind))

        hints = custom_hints()
        chunks = [
            hints[i:i + CUSTOM_GROUP_SIZE]
            for i in range(0, len(hints), CUSTOM_GROUP_SIZE)
        ]
        for number, chunk in enumerate(chunks, start=1):
            name = CUSTOM_CATEGORY
            if len(chunks) > 1:
                name = f"{CUSTOM_CATEGORY} {number}"
            box = make_category(name, CUSTOM_ICON)
            for hint in chunk:
                box.append(KeybindWidget(hint))
            groups.append(box)

        self.pages: list[gtk.FlowBox] = []
        for i in range(0, len(groups), PAGE_SIZE):
            page = make_page()
            for group in groups[i:i + PAGE_SIZE]:
                page.append(group)
            self.pages.append(page)

        self.current = 0
        self.stack = gtk.Stack(
            transition_type=gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            transition_duration=200,
            vhomogeneous=False
        )
        for page in self.pages:
            self.stack.add_child(page)
        self.append(self.stack)

        self.buttons: list[gtk.Button] = []
        if len(self.pages) > 1:
            # Holding the box weakly keeps the buttons from keeping it
            # alive after the window closes.
            weak_self = weakref.ref(self)

            def go_to(_: gtk.Button, index: int) -> None:
                box = weak_self()
                if box is not None:
                    box.set_page(index)

            buttons_box = gtk.Box(
                css_classes=("page-buttons",),
                halign=gtk.Align.CENTER
            )
            for index in range(len(self.pages)):
                button = gtk.Button(
                    label=str(index + 1),
                    css_classes=("page-button",)
                )
                button.connect("clicked", go_to, index)
                buttons_box.append(button)
                self.buttons.append(button)
            self.append(buttons_box)
        self.set_page(0)

    def set_page(self, index: int) -> None:
        index = max(0, min(index, len(self.pages) - 1))
        self.current = index
        self.stack.set_visible_child(self.pages[index])
        for i, button in enumerate(self.buttons):
            if i == index:
                button.add_css_class("active")
            else:
                button.remove_css_class("active")

    def move_page(self, step: int) -> None:
        self.set_page(self.current + step)

    def set_columns(self, columns: int) -> None:
        # The window starts at 1x1 and takes its minimum size, which a
        # flow box would make one column wide.
        for page in self.pages:
            page.set_min_children_per_line(columns)
            page.set_max_children_per_line(columns)

    def natural_width(self, columns: int) -> int:
        widest = 0
        for page in self.pages:
            widths: list[int] = []
            child = page.get_first_child()
            while child is not None:
                widths.append(child.measure(gtk.Orientation.HORIZONTAL, -1)[1])
                child = child.get_next_sibling()
            width = sum(sorted(widths, reverse=True)[:columns])
            width += page.get_column_spacing() * (columns - 1)
            widest = max(widest, width)
        return widest

    def destroy(self) -> None:
        self.buttons.clear()


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

    def monitor_width(self) -> int | None:
        display = gdk.Display.get_default()
        if display is None:
            return None
        for monitor in display.get_monitors():
            if monitor.get_connector() == hyprland.active_monitor_name.value:
                return int(monitor.get_geometry().width)
        return None

    def on_key_press(
        self,
        controller: gtk.EventControllerKey,
        keyval: int,
        *args: t.Any
    ) -> None:
        if self._child is not None:
            if keyval in PREVIOUS_PAGE_KEYS:
                self._child.move_page(-1)
            elif keyval in NEXT_PAGE_KEYS:
                self._child.move_page(1)
        super().on_key_press(controller, keyval, *args)

    def on_show(self) -> None:
        self._child = KeybindsBox()
        # Three columns where they fit, two on a narrow monitor.
        columns = COLUMNS
        width = self.monitor_width()
        if width is not None:
            limit = width * MAX_WIDTH_FRACTION
            while columns > 1 and self._child.natural_width(columns) > limit:
                columns -= 1
        self._child.set_columns(columns)
        self.box.append(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
            self.box.remove(self._child)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
