from repository import layer_shell, gtk, gdk
import asyncio
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

OTHER_CATEGORY = "Other"
OTHER_ICON = "keyboard"

# Bits of the modmask that `hyprctl binds` reports, in the order the
# window shows them.
MODMASK_NAMES = (
    (64, "SUPER"),
    (4, "CTRL"),
    (8, "ALT"),
    (1, "SHIFT"),
)

# Leaves room for the gaps around the window on the active monitor.
MAX_HEIGHT_FRACTION = 0.85
MAX_WIDTH_FRACTION = 0.95
COLUMNS = 3


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


def bind_from_hyprctl(item: dict[str, t.Any]) -> tuple[str, ...]:
    modmask = int(item.get("modmask") or 0)
    keys = [name for bit, name in MODMASK_NAMES if modmask & bit]
    keys.append(str(item.get("key") or ""))
    return tuple(keys)


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

    def __init__(self, on_resize: t.Callable[[], None]) -> None:
        super().__init__(
            css_classes=("keybinds-box",),
            selection_mode=gtk.SelectionMode.NONE,
            hexpand=True,
            max_children_per_line=COLUMNS,
            row_spacing=2,
            column_spacing=2
        )
        self.destroyed = False
        self.on_resize = on_resize
        self.boxes: dict[Category, gtk.Box] = {}
        for category, icon in CATEGORIES.items():
            box = self.make_category(category, icon)
            self.boxes[category] = box
            self.append(box)

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
            self.boxes[keybind.category].append(KeybindWidget(keybind))

        # Binds from the user's own config and from custom keybinds only
        # exist in Hyprland, so they are read from there.
        self.other_box = self.make_category(OTHER_CATEGORY, OTHER_ICON)
        self.other_child: gtk.FlowBoxChild | None = None
        asyncio.create_task(self.load_other_binds())

    def make_category(self, name: str, icon: str) -> gtk.Box:
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

    async def load_other_binds(self) -> None:
        try:
            binds = await hyprland.client.query("binds")
        except Exception as e:
            logger.warning("Couldn't read binds from Hyprland: %s", e)
            return
        if self.destroyed or not isinstance(binds, list):
            return

        # Default binds carry their description too, so they are told
        # apart by it; the workspace binds share one for all ten keys.
        known = {
            keybind.description for keybind in key_binds
            if keybind.description
        }
        seen: set[tuple[tuple[str, ...], str]] = set()
        hints: list[KeyBindHint] = []
        for item in binds:
            if not isinstance(item, dict) or item.get("submap"):
                continue
            description = str(item.get("description") or "").strip()
            if not description or description in known:
                continue
            bind = bind_from_hyprctl(item)
            if not bind[-1] or (bind, description) in seen:
                continue
            seen.add((bind, description))
            hints.append(KeyBindHint(bind, description))

        if not hints:
            return
        hints.sort(key=lambda hint: (hint.description or "").lower())
        for hint in hints:
            self.other_box.append(KeybindWidget(hint))
        self.append(self.other_box)
        self.on_resize()

    def destroy(self) -> None:
        self.destroyed = True


class KeybindsWindow(widget.LayerWindow):
    __gtype_name__ = "KeybindsWindow"

    def __init__(self, app: gtk.Application) -> None:
        self.box = gtk.Box(
            hexpand=True,
            vexpand=True
        )
        # With many binds the list would grow past the screen, so it
        # scrolls once it reaches most of the monitor's height.
        self.scroll = gtk.ScrolledWindow(
            hscrollbar_policy=gtk.PolicyType.NEVER,
            vscrollbar_policy=gtk.PolicyType.AUTOMATIC,
            propagate_natural_height=True,
            propagate_natural_width=True,
            child=self.box
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
            child=self.scroll
        )
        self._child: KeybindsBox | None = None

        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("InfoWindow finalized")
            )

    def monitor_size(self) -> tuple[int, int] | None:
        display = gdk.Display.get_default()
        if display is None:
            return None
        for monitor in display.get_monitors():
            if monitor.get_connector() == hyprland.active_monitor_name.value:
                geometry = monitor.get_geometry()
                return geometry.width, geometry.height
        return None

    def fit_size(self) -> None:
        # The window starts at 1x1 and so takes its minimum size, which a
        # scrolled window keeps small. Ask for the width of the widest
        # columns and the height they need, up to most of the monitor.
        if self._child is None:
            return
        widths: list[int] = []
        child = self._child.get_first_child()
        while child is not None:
            widths.append(child.measure(gtk.Orientation.HORIZONTAL, -1)[1])
            child = child.get_next_sibling()
        if not widths:
            return
        per_line = min(COLUMNS, len(widths))
        width = sum(sorted(widths, reverse=True)[:per_line])
        width += self._child.get_column_spacing() * (per_line - 1)

        size = self.monitor_size()
        max_height = -1
        if size is not None:
            width = min(width, int(size[0] * MAX_WIDTH_FRACTION))
            max_height = int(size[1] * MAX_HEIGHT_FRACTION)

        self.box.set_size_request(width, -1)
        height = self.box.measure(gtk.Orientation.VERTICAL, width)[1]
        if max_height > 0:
            height = min(height, max_height)
        self.scroll.set_min_content_height(height)

    def on_show(self) -> None:
        self._child = KeybindsBox(self.fit_size)
        self.box.append(self._child)
        self.fit_size()

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
            self.box.remove(self._child)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
