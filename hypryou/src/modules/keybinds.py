from repository import layer_shell, gtk, gdk
import asyncio
import re
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
# "Group: what it does" puts a custom bind under its own title, or into a
# default category of that name.
GROUP_PREFIX = re.compile(r"^\s*([^:]{1,32}?)\s*:\s+(\S.*)$")
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
    known.update(
        hint.description for hint in custom_hints() if hint.description
    )
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
    if window is None:
        return
    window.config_hints = hints
    # Only if the window still shows the list this query was made for.
    box = child()
    if box is not None and window._child is box and box.extra != hints:
        window.show_list(hints)


def split_group(description: str) -> tuple[str | None, str]:
    match = GROUP_PREFIX.match(description)
    if match is None:
        return None, description
    return match.group(1), match.group(2)


def make_category(name: str | None, icon: str) -> gtk.Box:
    box = gtk.Box(
        css_classes=("category-box",),
        orientation=gtk.Orientation.VERTICAL
    )
    if name is None:
        # The rest of a group that went on in another box.
        return box
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
        self.extra = extra or []
        # Whether each group goes on from the one before it.
        self.continues: list[bool] = []
        # The groups only get the window's styles, and so their real size,
        # once they are inside it and visible; they wait here until build()
        # lays them out, which happens before anything is drawn.
        self.groups = self.make_groups(self.extra)
        self.holder = gtk.Box()
        for group in self.groups:
            self.holder.append(group)
        self.append(self.holder)
        self.pages: list[gtk.Box] = []
        self.buttons: list[gtk.Button] = []
        self.current = 0

    def build(self, monitor: tuple[int, int] | None) -> None:
        columns, max_height = self.fit(self.groups, monitor)
        # Measured here because a group loses the window's styles, and so
        # its real size, as soon as it leaves the holder.
        sizes = [
            group.measure(gtk.Orientation.VERTICAL, -1)[1]
            for group in self.groups
        ]
        for group in self.groups:
            self.holder.remove(group)
        self.remove(self.holder)
        self.pages = self.lay_out(self.groups, sizes, columns, max_height)

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
        self.continues = [False] * len(groups)
        for keybind in key_binds:
            section = keybind.category
            if not keybind.description or not section:
                continue
            shown: KeyBind | KeyBindHint = keybind
            if isinstance(keybind, KeyBind):
                bind = effective_bind(keybind)
                if bind is None:
                    continue
                shown = KeyBindHint(bind, keybind.description, section)
            boxes[section].append(KeybindWidget(shown))

        titles = {category.value.lower(): category for category in boxes}
        grouped: dict[str, list[KeyBindHint]] = {}
        for hint in custom_hints() + extra:
            group, description = split_group(hint.description or "")
            hint = KeyBindHint(hint.bind, description)
            default = titles.get((group or "").lower())
            if default is not None:
                boxes[default].append(KeybindWidget(hint))
                continue
            grouped.setdefault(group or CUSTOM_CATEGORY, []).append(hint)

        # Ungrouped binds come last, under the plain custom title.
        if CUSTOM_CATEGORY in grouped:
            grouped[CUSTOM_CATEGORY] = grouped.pop(CUSTOM_CATEGORY)
        for title, hints in grouped.items():
            for start in range(0, len(hints), CUSTOM_GROUP_SIZE):
                # Only the first box of a long group carries its title.
                box = make_category(
                    title if start == 0 else None, CUSTOM_ICON
                )
                for hint in hints[start:start + CUSTOM_GROUP_SIZE]:
                    box.append(KeybindWidget(hint))
                groups.append(box)
                self.continues.append(start > 0)
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
        sizes: list[int],
        columns: int,
        max_height: int
    ) -> list[gtk.Box]:
        # Each group goes under the shortest column, so a short group
        # leaves no gap below it. A long group flows like text instead,
        # from the leftmost column with room and only ever to the right,
        # so its parts stay in reading order. A group that fits nowhere
        # it may go starts the next page.
        pages: list[gtk.Box] = []
        stacks: list[gtk.Box] = []
        heights: list[int] = []
        column = 0

        def fits(index: int, height: int) -> bool:
            return (
                max_height <= 0
                or heights[index] == 0
                or heights[index] + GAP + height <= max_height
            )

        for number, (group, height) in enumerate(zip(groups, sizes)):
            continues = self.continues[number]
            leads = (
                number + 1 < len(groups) and self.continues[number + 1]
            )
            shortest = heights.index(min(heights)) if heights else -1
            if stacks and (continues or leads):
                shortest = next(
                    (
                        index
                        for index in range(column if continues else 0, columns)
                        if fits(index, height)
                    ),
                    -1
                )
            if not stacks or shortest < 0 or not fits(shortest, height):
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
            column = shortest
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
        # Last described binds from hyprland.lua, so only the first opening
        # has to build the list twice.
        self.config_hints: list[KeyBindHint] = []

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
        self.show_list(self.config_hints)
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
