from repository import gtk, layer_shell, glib, gdk
from utils.logger import logger
from utils.styles import toggle_css_class
from utils.debounce import sync_debounce
from utils_cy.levenshtein import compute_score
from src.services.state import close_window
import typing as t
from os.path import join
import json
from config import ASSETS_DIR, APP_CACHE_DIR
import src.widget as widget
import weakref

emojis_file = join(ASSETS_DIR, "emojis.json")
recent_emojis = join(APP_CACHE_DIR, "recent-emojis.json")

FOUND_THRESHOLD = 0.8
CATEGORIES = {
    "Recent": "history_2",
    "Smileys & Emotion": "mood",
    "People & Body": "emoji_people",
    "Animals & Nature": "emoji_nature",
    "Food & Drink": "emoji_food_beverage",
    "Travel & Places": "emoji_transportation",
    "Activities": "trophy",
    "Objects": "emoji_objects",
    "Symbols": "emoji_symbols",
    "Flags": "flag"
}

type EmojiTuple = tuple[str, str]  # (char, name)


def get_emojis() -> dict[str, list[EmojiTuple]]:
    cached = t.cast(
        dict[str, list[EmojiTuple]] | None,
        getattr(get_emojis, "_cached", None)
    )
    if cached is not None:
        return cached
    else:
        try:
            with open(emojis_file, "r") as f:
                raw = json.load(f)
        except Exception:
            raw = {}

        emojis = {
            category: [(e["char"], e["name"]) for e in emoji_list]
            for category, emoji_list in raw.items()
            if isinstance(emoji_list, list)
        }

        setattr(get_emojis, "_cached", emojis)
        return t.cast(dict[str, list[EmojiTuple]], emojis)


class EmojisBox(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("emojis-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        self.flow_box = gtk.FlowBox(
            hexpand=True,
            vexpand=True,
            valign=gtk.Align.START,
            halign=gtk.Align.START,
            max_children_per_line=30
        )
        self.scrollable = gtk.ScrolledWindow(
            child=self.flow_box,
            hscrollbar_policy=gtk.PolicyType.NEVER,
            hexpand=True,
            vexpand=True
        )

        self.top_bar = gtk.Box(
            hexpand=True,
            css_classes=("top-bar",)
        )
        self.top_bar_scroll = gtk.ScrolledWindow(
            child=self.top_bar,
            vscrollbar_policy=gtk.PolicyType.NEVER,
            hscrollbar_policy=gtk.PolicyType.EXTERNAL,
            hexpand=True
        )
        print(self.top_bar_scroll.observe_controllers())
        self.scroll_controller = gtk.EventControllerScroll.new(
            gtk.EventControllerScrollFlags.VERTICAL |
            gtk.EventControllerScrollFlags.DISCRETE
        )
        self.top_bar_scroll.add_controller(self.scroll_controller)
        self.scroll_controller.connect("scroll", self.on_scroll)

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
        self.entry_handler = self.entry.connect("notify::text", self.on_search)

        self.top_bar.append(self.search_box)

        self.handlers: dict[gtk.Widget, int] = {}
        self.buttons: dict[str, gtk.Button] = {}

        self.current_page = ""

        self._last_active: gtk.Button | None = None
        for category, icon in CATEGORIES.items():
            btn = gtk.Button(
                child=widget.Icon(icon),
                halign=gtk.Align.START,
                valign=gtk.Align.START,
                css_classes=("category-button",),
                tooltip_text=category
            )
            self.buttons[category] = btn
            self.handlers[btn] = (
                btn.connect(
                    "clicked",
                    lambda *_, c=category: self.set_page(c)
                )
            )
            self.top_bar.append(btn)

        self.all_emojis = get_emojis()

        self.recent_emojis: list[EmojiTuple]
        try:
            with open(recent_emojis, "r") as f:
                self.recent_emojis = [
                    (emoji[0], emoji[1])
                    for emoji in json.load(f)
                ]
        except (FileNotFoundError, json.JSONDecodeError):
            self.recent_emojis = []

        self._emojis_iter: t.Iterator[EmojiTuple] | None = None
        self._emojis_iter_index = -1

        self._widget_pool: list[gtk.Button] = []
        self._virtual_pool: list[EmojiTuple] = []
        self.source_id = 0

        self.append(self.top_bar_scroll)
        self.append(self.scrollable)

        self.set_page("Recent")

    def on_scroll(
        self,
        controller: gtk.EventControllerScroll,
        dx: float,
        dy: float
    ) -> bool:
        # TODO: That'd be better to make real kinetic scroll like in scrollbar
        adjustment = self.top_bar_scroll.get_hadjustment()
        increment = abs(dy) * adjustment.get_step_increment()
        increment = increment * -1 if dy < 0 else increment
        adjustment.set_value(adjustment.get_value() + increment)
        return True

    @sync_debounce(500)
    def on_search(self, *args: t.Any) -> None:
        value = self.entry.get_text()
        if len(value.strip()) == 0:
            self.set_page(self.current_page.lstrip("\\"))
        else:
            self.current_page = f"\\{self.current_page}"
            matches: list[tuple[float, tuple[str, str]]] = []
            for _, category in self.all_emojis.items():
                for emoji in category:
                    scores: dict[str, float] = {}
                    for word in emoji[1].split():
                        for word2 in value.split():
                            _score = compute_score(word, word2)
                            if word2 not in scores or scores[word2] < _score:
                                scores[word2] = _score
                    score = sum(scores.values()) / len(scores)
                    if score > FOUND_THRESHOLD:
                        matches.append((score, emoji))
            matches.sort(reverse=True, key=lambda x: x[0])
            self._virtual_pool = [emoji for _, emoji in matches]
            self.update_pool()

    def set_page(self, page: str) -> None:
        if page == self.current_page:
            return

        if self._last_active:
            toggle_css_class(self._last_active, "selected", False)
        if page in self.buttons.keys():
            toggle_css_class(self.buttons[page], "selected", True)

        self.entry.handler_block(self.entry_handler)
        self.entry.set_text("")
        self.entry.handler_unblock(self.entry_handler)

        self._last_active = self.buttons.get(page)
        self.current_page = page

        if page == "Recent":
            self._virtual_pool = self.recent_emojis
        elif page == "EMPTY":
            self._virtual_pool = []
        else:
            self._virtual_pool = self.all_emojis[page]
        self.update_pool()

    def update_pool(self) -> None:
        if self.source_id:
            glib.source_remove(self.source_id)
            self._emojis_iter = None
            self._emojis_iter_index = -1

        self._emojis_iter = iter(self._virtual_pool)
        self.source_id = glib.idle_add(
            self._add_next_emoji,
            priority=glib.PRIORITY_LOW
        )

    def on_emoji_clicked(self, btn: gtk.Button, *args: t.Any) -> None:
        emoji = str(btn.get_label())
        clipboard = gdk.Display.get_default().get_clipboard()
        clipboard.set_content(
            gdk.ContentProvider.new_for_bytes(
                "text/plain;charset=utf-8",
                glib.Bytes.new(emoji.encode())
            )
        )
        emoji_tuple = (emoji, str(btn.get_tooltip_text()))
        for _emoji in self.recent_emojis:
            if _emoji[0] == emoji:
                self.recent_emojis.remove(_emoji)
                break
        self.recent_emojis.insert(0, emoji_tuple)
        with open(recent_emojis, "w") as f:
            json.dump(self.recent_emojis, f)
        close_window("emojis")

    def _add_next_emoji(self) -> bool:
        if self._emojis_iter is None:
            raise RuntimeError("EmojisBox._emoji_iter must not be None")
        try:
            for i in range(100):
                emoji = next(self._emojis_iter)
                emoji_char, emoji_name = emoji
                self._emojis_iter_index += 1
                index = self._emojis_iter_index
                if index > len(self._widget_pool) - 1:
                    btn = gtk.Button(
                        css_classes=("emoji", "icon-default"),
                        label=emoji_char,
                        tooltip_text=emoji_name,
                        halign=gtk.Align.START,
                        valign=gtk.Align.START
                    )
                    btn.connect(
                        "clicked", self.on_emoji_clicked
                    )
                    self.flow_box.append(btn)
                    self._widget_pool.append(btn)
                else:
                    btn = self._widget_pool[index]
                    btn.set_label(emoji_char)
                    btn.set_tooltip_text(emoji_name)
            return True
        except StopIteration:
            while len(self._widget_pool) > self._emojis_iter_index + 1:
                btn_to_remove = self._widget_pool.pop()
                self.flow_box.remove(btn_to_remove)
            self._emojis_iter = None
            self._emojis_iter_index = -1
            self.source_id = 0
            return False


class EmojisWindow(widget.LayerWindow):
    __gtype_name__ = "EmojisWindow"

    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            anchors={
                "top": True,
                "left": True
            },
            css_classes=("emoji-picker",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="emojis",
            height=1,
            width=1,
            setup_popup=True
        )
        self._child: EmojisBox | None = None
        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("AppsWindow finalized")
            )

    def on_show(self) -> None:
        if not self._child:
            self._child = EmojisBox()
            self.set_child(self._child)

        self._child.entry.grab_focus()
        self._child.set_page("Recent")

    def on_hide(self) -> None:
        if self._child:
            self._child.set_page("EMPTY")
            self._child.entry.set_text("")
