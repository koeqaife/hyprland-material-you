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

CUSTOM_CATEGORY = "Custom"
CUSTOM_ICON = "keyboard"
# Same length as the longest default category, so custom groups line up
# with the others instead of growing into one long column.
CUSTOM_GROUP_SIZE = 10
COLUMNS = 3
GAP = 2
# Leaves room for the gaps around the window and the page buttons.
MAX_WIDTH_FRACTION = 0.95
MAX_HEIGHT_FRACTION = 0.75

# Bits of the modmask that `hyprctl binds` reports, in the order the
# window shows them.
MODMASK_NAMES = (
    (64, "SUPER"),
    (4, "CTRL"),
    (8, "ALT"),
    (1, "SHIFT"),
)

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


def bind_from_hyprctl(item: dict[str, t.Any]) -> tuple[str, ...]:
    modmask = int(item.get("modmask") or 0)
    keys = [name for bit, name in MODMASK_NAMES if modmask & bit]
    keys.append(str(item.get("key") or ""))
    return tuple(keys)


async def config_hints() -> list[KeyBindHint]:
    """Described binds from the user's hyprland.lua.

    That file is loaded by Hyprland only, so its binds never reach
    HyprYou's runtime and have to be read back from Hyprland. Binds that
    HyprYou already lists are skipped by their description.
    """
    try:
        binds = await hyprland.client.query("binds")
    except Exception as e:
        logger.warning("Couldn't read binds from Hyprland: %s", e)
        return []
    if not isinstance(binds, list):
        return []
    known = {
        keybind.description for keybind in key_binds
        if keybind.description
    }
    known.update(hint.description for hint in custom_hints())
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
    return hints


async def add_config_binds(
    window_ref: "weakref.ref[KeybindsWindow]",
    child: "weakref.ref[KeybindsBox]"
) -> None:
    hints = await config_hints()
    window = window_ref()
    if window is None or not hints:
        return
    # Only if the window still shows the list this query was made for.
    if child() is not None and window._child is child():
        window.show_list(hints)


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


class KeybindsBox(gtk.Box):
    __gtype_name__ = "KeybindsBox"

    def __init__(self, extra: list[KeyBindHint] | None) -> None:
        super().__init__(
            css_classes=("keybinds-pages",),
            orientation=gtk.Orientation.VERTICAL
        )
        # The groups only get the window's styles, and so their real size,
        # once they are inside it; they wait here until build() lays them
        # out.
        self.groups = self.make_groups(extra or [])
        self.holder = gtk.Box(visible=False)
        for group in self.groups:
            self.holder.append(group)
        self.append(self.holder)
        self.pages: list[gtk.Box] = []
        self.buttons: list[gtk.Button] = []
        self.current = 0

    def build(self, monitor: tuple[int, int] | None) -> None:
        columns, max_height = self.fit(self.groups, monitor)
        for group in self.groups:
            self.holder.remove(group)
        self.remove(self.holder)
        self.pages = self.lay_out(self.groups, columns, max_height)

        self.stack = gtk.Stack(
            transition_type=gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            transition_duration=200
        )
        for page in self.pages:
            self.stack.add_child(page)
        self.append(self.stack)

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

    def make_groups(self, extra: list[KeyBindHint]) -> list[gtk.Box]:
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

        hints = custom_hints() + extra
        chunks = [
            hints[i:i + CUSTOM_GROUP_SIZE]
            for i in range(0, len(hints), CUSTOM_GROUP_SIZE)
        ]
        # The groups share one title: they are placed by height, not in
        # reading order, so numbers would read out of order.
        for chunk in chunks:
            box = make_category(CUSTOM_CATEGORY, CUSTOM_ICON)
            for hint in chunk:
                box.append(KeybindWidget(hint))
            groups.append(box)
        return groups

    def fit(
        self,
        groups: list[gtk.Box],
        monitor: tuple[int, int] | None
    ) -> tuple[int, int]:
        """Columns that fit the monitor's width, and a page's height."""
        if monitor is None:
            return COLUMNS, -1
        widest = max(
            group.measure(gtk.Orientation.HORIZONTAL, -1)[1]
            for group in groups
        )
        columns = COLUMNS
        while (
            columns > 1
            and widest * columns + GAP * (columns - 1)
            > monitor[0] * MAX_WIDTH_FRACTION
        ):
            columns -= 1
        return columns, int(monitor[1] * MAX_HEIGHT_FRACTION)

    def lay_out(
        self,
        groups: list[gtk.Box],
        columns: int,
        max_height: int
    ) -> list[gtk.Box]:
        # Each group goes under the shortest column, so a short group
        # leaves no gap below it. A group that fits under no column
        # starts the next page.
        pages: list[gtk.Box] = []
        stacks: list[gtk.Box] = []
        heights: list[int] = []
        for group in groups:
            height = group.measure(gtk.Orientation.VERTICAL, -1)[1]
            shortest = heights.index(min(heights)) if heights else -1
            if (
                not stacks
                or (
                    max_height > 0
                    and heights[shortest] > 0
                    and heights[shortest] + GAP + height > max_height
                )
            ):
                page = gtk.Box(spacing=GAP, valign=gtk.Align.START)
                stacks = []
                for _ in range(columns):
                    stack = gtk.Box(
                        orientation=gtk.Orientation.VERTICAL,
                        spacing=GAP
                    )
                    page.append(stack)
                    stacks.append(stack)
                heights = [0] * columns
                pages.append(page)
                shortest = 0
            stacks[shortest].append(group)
            heights[shortest] += height + (GAP if heights[shortest] else 0)
        return pages

    def set_page(self, index: int) -> None:
        if not self.pages:
            return
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

    def monitor_size(self) -> tuple[int, int] | None:
        display = gdk.Display.get_default()
        if display is None:
            return None
        for monitor in display.get_monitors():
            if monitor.get_connector() == hyprland.active_monitor_name.value:
                geometry = monitor.get_geometry()
                return int(geometry.width), int(geometry.height)
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
        self.show_list()
        if self._child is not None:
            asyncio.create_task(
                add_config_binds(weakref.ref(self), weakref.ref(self._child))
            )

    def show_list(self, extra: list[KeyBindHint] | None = None) -> None:
        self.on_hide()
        self._child = KeybindsBox(extra)
        self.box.append(self._child)
        self._child.build(self.monitor_size())

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
            self.box.remove(self._child)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
