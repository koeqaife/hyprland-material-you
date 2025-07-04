from repository import gtk, layer_shell, glib, pango
from src.services.cliphist import items, repopulate, save_cache_file
from src.services.cliphist import clear_tmp
from src.services.cliphist import copy_by_id
from utils import sync_debounce, toggle_css_class
from utils.logger import logger
from config import HyprlandVars
import weakref
import typing as t
import re
from utils_cy.levenshtein import compute_text_match_score
from utils_cy.levenshtein import token_set_ratio
from src.services.state import close_window
from src import widget

FOUND_THRESHOLD = 0.5
data_regex = re.compile(
    r"\[\[ binary data (\d+) (KiB|MiB) (\w+) (\d+)x(\d+) \]\]"
)


def normalize_string(s: str) -> str:
    s = re.sub(r"[-_]", " ", s)
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    return s.lower()


class ClipItem(gtk.Revealer):
    __gtype_name__ = "ClipHistoryItem"

    def __init__(self, item: tuple[str, str], search: str) -> None:
        self.on_activate = sync_debounce(750, 1, True)(self._on_activate)
        self.button = gtk.Button(
            css_classes=("cliphist-item",),
            tooltip_text=item[1]
        )
        super().__init__(
            css_classes=("cliphist-item-revealer",),
            child=self.button,
            transition_duration=250,
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN
        )
        self.score = -1.0
        self.item = item
        self.show_image = False
        self._child: gtk.Box | gtk.Label | None = None

        self.search_strings = (
            self.item[1],
            normalize_string(self.item[1])
        )

        self.check_is_image()
        self.update_widget()

        self.update_search(search)

        self.on_click_handler = self.button.connect("clicked", self.on_click)

    def idle_widget(self) -> None:
        self.button.set_child(None)
        self._child = None
        self.show_image = False
        clear_tmp()

    def update_widget(self) -> None:
        if self.show_image and not isinstance(self._child, gtk.Box):
            file = save_cache_file(self.item[0])

            image_widget = gtk.Box(
                css_classes=("preview",),
                halign=gtk.Align.START,
                valign=gtk.Align.START
            )
            self.button.set_child(image_widget)
            self._child = image_widget

            max_width_rem = 27
            width_px = (self.width / self.height) * 200
            width_rem = width_px / 16

            css = f"background-image: url('file://{file}');"

            if width_rem > max_width_rem:
                new_height_rem = (200 / width_px) * max_width_rem
                css += (
                    f"min-height: {new_height_rem:.2f}rem; " +
                    f"min-width: {max_width_rem:.2f}rem;"
                )
            else:
                css += (
                    f"min-height: {200/16:.2f}rem; " +
                    f"min-width: {width_rem:.2f}rem;"
                )

            css_provider = gtk.CssProvider()
            image_widget.get_style_context().add_provider(
                css_provider,
                gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            css_provider.load_from_data(f"box {{ {css} }}")
        elif not isinstance(self._child, gtk.Label):
            if self.is_image:
                format = self.format.capitalize()
                label_widget = gtk.Label(
                    label=(
                        f"{format} image ({self.width}x{self.height}), " +
                        "click to reveal."
                    ),
                    css_classes=("label",)
                )
                self.button.set_child(label_widget)
                self._child = label_widget
            else:
                label_widget = gtk.Label(
                    label=self.item[1],
                    ellipsize=pango.EllipsizeMode.END,
                    css_classes=("label",),
                    halign=gtk.Align.START
                )
                self.button.set_child(label_widget)
                self._child = label_widget

    def check_is_image(self) -> None:
        match = data_regex.match(self.item[1])
        if match:
            format = match[3]
            if format == "png":
                self.add_css_class("is-image")
                self.width = int(match[4])
                self.height = int(match[5])
                self.is_image = True
                self.format = format
                return

        self.width = 0
        self.height = 0
        self.is_image = False
        self.format = None

    def on_click(self, *args: t.Any) -> None:
        if self.is_image:
            self.show_image = True
            self.update_widget()
        self.on_activate()

    def _on_activate(self, *args: t.Any) -> None:
        self._activate()

    def _activate(self, *args: t.Any) -> None:
        close_window("cliphist")
        copy_by_id(self.item[0])

    def update_search(self, search: str, search_normalized: str = "") -> None:
        if not search or not search.strip():
            self.set_reveal_child(True)
            self.score = -1
        else:
            scores = []
            for string in self.search_strings:
                raw_score = compute_text_match_score(string, search)
                normalized_score = (
                    compute_text_match_score(string, search_normalized)
                    if search_normalized else -1
                )
                token_score = (
                    token_set_ratio(string, search)
                )
                score = max(raw_score, normalized_score, token_score)
                scores.append(score)

            max_score = max(*scores)
            self.set_reveal_child(max_score >= FOUND_THRESHOLD)
            self.score = max_score

    def destroy(self) -> None:
        self.button.disconnect(self.on_click_handler)


class ClipHistoryBox(gtk.Box):
    __gtype_name__ = "ClipHistoryBox"

    def __init__(self) -> None:
        self.search = ""
        super().__init__(
            css_classes=("cliphist-box",),
            orientation=gtk.Orientation.VERTICAL,
            vexpand=True,
            halign=gtk.Align.FILL
        )
        self.list = gtk.Box(
            css_classes=("cliphist-list",),
            orientation=gtk.Orientation.VERTICAL,
            vexpand=True
        )
        self.scrollable = gtk.ScrolledWindow(
            css_classes=("cliphist-scrollable",),
            hscrollbar_policy=gtk.PolicyType.NEVER,
            vscrollbar_policy=gtk.PolicyType.AUTOMATIC,
            child=self.list,
            vexpand=True
        )

        self.search_box = gtk.Box(
            css_classes=("misc--search", "search")
        )
        self.entry_icon = widget.Icon("search")
        self.entry = gtk.Entry(
            css_classes=("entry",),
            placeholder_text="Search",
            hexpand=True
        )
        self.search_box.append(self.entry_icon)
        self.search_box.append(self.entry)
        self.entry_handlers = (
            self.entry.connect("notify::text", self.on_search),
            self.entry.connect("activate", self.on_entry_enter)
        )

        self._items: dict[str, ClipItem] = {}

        self.append(self.search_box)
        self.append(self.scrollable)

        self.update_items(items.value)
        self.handler_id = items.watch(self.update_items)

        self.last_highest: tuple[str, ClipItem] | None = None

        if __debug__:
            weakref.finalize(self, lambda: logger.debug("AppsBox finalized"))

    def on_entry_enter(self, *args: t.Any) -> None:
        if self.last_highest:
            self.last_highest[1]._activate()

    @sync_debounce(150)
    def on_search(self, *args: t.Any) -> None:
        text = self.entry.get_text()
        normalized = normalize_string(text)
        for item in self._items.values():
            item.update_search(text, normalized)
        if len(text.strip()) > 0:
            self.hint_highest()
        elif self.last_highest:
            toggle_css_class(self.last_highest[1], "highest", False)
            self.last_highest = None

    def destroy(self) -> None:
        items.unwatch(self.handler_id)
        for handler in self.entry_handlers:
            self.entry.disconnect(handler)

    def idle_items(self) -> None:
        for key, item in self._items.items():
            item.idle_widget()

    def update_items_widgets(self) -> None:
        for key, item in self._items.items():
            item.update_widget()

    def hint_highest(self) -> None:
        items = list(self._items.items())
        highest: tuple[str, ClipItem] | None = None
        for item in items:
            if item[1].get_reveal_child() and (
                not highest
                or item[1].score > highest[1].score
            ):
                highest = item

        if not highest and self.last_highest:
            toggle_css_class(self.last_highest[1], "highest", False)
            self.last_highest = None
        elif not highest:
            return
        elif not self.last_highest or self.last_highest[1] is not highest[1]:
            toggle_css_class(highest[1], "highest", True)
            if self.last_highest:
                toggle_css_class(self.last_highest[1], "highest", False)
            self.last_highest = highest

    def update_items(self, new_items: dict[str, str]) -> None:
        existing = set(self._items.keys())
        desired = set(new_items)

        to_add = [item_id for item_id in new_items if item_id not in existing]
        to_add.sort(key=int, reverse=False)
        to_remove = existing - desired

        for item_id in to_add:
            widget = ClipItem((item_id, new_items[item_id]), self.search)
            self._items[item_id] = widget
            self.list.insert_child_after(widget, None)

        for item_id in to_remove:
            widget = self._items.pop(item_id)
            widget.destroy()
            self.list.remove(widget)


class ClipHistoryWindow(widget.LayerWindow):
    __gtype_name__ = "ClipHistoryWindow"

    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            anchors={
                "top": True,
                "right": True
            },
            margins={
                "top": HyprlandVars.gap,
                "right": HyprlandVars.gap
            },
            css_classes=("cliphist",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="cliphist",
            height=1,
            width=1,
            setup_popup=True
        )
        self.name = "cliphist"
        self._child: ClipHistoryBox | None = None

        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("ClipHistoryWindow finalized")
            )

    def on_show(self) -> None:
        glib.idle_add(repopulate)
        if not self._child:
            self._child = ClipHistoryBox()
            self.set_child(self._child)
            self._child.entry.grab_focus()
        else:
            self._child.entry.grab_focus()
            self._child.update_items_widgets()

    def on_hide(self) -> None:
        if self._child:
            self._child.entry.set_text("")
            self._child.idle_items()

    def destroy(self) -> None:
        super().destroy()
