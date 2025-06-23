from functools import lru_cache
from repository import gtk, gdk, layer_shell, glib, pango
from src.services.apps import Application, apps, reload as apps_reload
from utils import sync_debounce, toggle_css_class
from utils.logger import logger
from config import HyprlandVars
import weakref
import typing as t
from src.services.state import close_window
from src import widget


@lru_cache(512)
def cache_icon(icon: str | None) -> gtk.IconPaintable | None:
    display = gdk.Display.get_default()
    icon_theme = gtk.IconTheme.get_for_display(display)

    if icon is None:
        texture = icon_theme.lookup_icon(
            "image-missing", None, 32, 1,
            gtk.TextDirection.LTR,
            gtk.IconLookupFlags.FORCE_SYMBOLIC
        )
    else:
        texture = icon_theme.lookup_icon(
            icon, "image-missing", 32, 1,
            gtk.TextDirection.LTR,
            gtk.IconLookupFlags.FORCE_SYMBOLIC
        )
    return texture


class AppItem(gtk.Revealer):
    __gtype_name__ = "AppItem"

    def __init__(self, item: Application, search: str) -> None:
        self.on_click = sync_debounce(750, 1, True)(self._on_click)
        self.box = gtk.Box(
            css_classes=("app-item-box",)
        )
        self.button = gtk.Button(
            css_classes=("app-item",),
            child=self.box,
            tooltip_text=f"{item.name}\n{item.description or ""}"
        )
        super().__init__(
            css_classes=("app-item-revealer",),
            child=self.button,
            transition_duration=250,
            transition_type=gtk.RevealerTransitionType.SLIDE_DOWN
        )
        self.item = item

        self.icon = gtk.Picture(
            css_classes=("icon",)
        )
        self.label = gtk.Label(
            css_classes=("label",),
            label=item.name,
            ellipsize=pango.EllipsizeMode.END
        )

        texture = cache_icon(item.icon)
        if texture:
            self.icon.set_paintable(texture)

        self.box.append(self.icon)
        self.box.append(self.label)

        self.update_search(search)

        self.on_click_handler = self.button.connect("clicked", self.on_click)

    def _on_click(self, *args: t.Any) -> None:
        self.launch()

    def launch(self, *args: t.Any) -> None:
        close_window("apps_menu")
        self.item.launch()

    def update_search(self, search: str) -> None:
        if not search or not search.strip():
            self.set_reveal_child(True)
        else:
            self.set_reveal_child(self.item.match(search))

    def destroy(self) -> None:
        self.button.disconnect(self.on_click_handler)
        del self.on_click


class AppsBox(gtk.Box):
    __gtype_name__ = "AppsBox"

    def __init__(self) -> None:
        self.search = ""
        super().__init__(
            css_classes=("apps-box",),
            orientation=gtk.Orientation.VERTICAL,
            vexpand=True,
            halign=gtk.Align.FILL
        )
        self.list = gtk.Box(
            css_classes=("apps-list",),
            orientation=gtk.Orientation.VERTICAL,
            vexpand=True
        )
        self.scrollable = gtk.ScrolledWindow(
            css_classes=("apps-scrollable",),
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

        self._apps: dict[Application, AppItem] = {}

        self.append(self.search_box)
        self.append(self.scrollable)

        self.update_apps(apps.value)
        self.handler_id = apps.watch(self.update_apps)

        self.last_highest: tuple[Application, AppItem] | None = None

        weakref.finalize(self, lambda: logger.debug("AppsBox finalized"))

    def on_entry_enter(self, *args: t.Any) -> None:
        if self.last_highest:
            self.last_highest[1].launch()

    @sync_debounce(150)
    def on_search(self, *args: t.Any) -> None:
        text = self.entry.get_text()
        for item in self._apps.values():
            item.update_search(text)
        if len(text.strip()) > 0:
            self.hint_highest()
        elif self.last_highest:
            toggle_css_class(self.last_highest[1], "highest", False)
            self.last_highest = None

    def destroy(self) -> None:
        for key, item in self._apps.items():
            item.destroy()
            self.list.remove(item)
        apps.unwatch(self.handler_id)
        cache_icon.cache_clear()

    def hint_highest(self) -> None:
        items = list(self._apps.items())
        highest: tuple[Application, AppItem] | None = None
        for item in items:
            if item[1].get_reveal_child() and (
                not highest
                or item[0].score + item[0].frequency / 50 >
                highest[0].score + highest[0].frequency / 50
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

    def sort_by_frequent(self) -> None:
        new_dict = dict(
            sorted(
                self._apps.items(),
                key=lambda item: (item[0].frequency, item[0].name)
            )
        )
        self._apps = new_dict

        for child in list(self.list):  # type: ignore [call-overload]
            self.list.remove(child)

        for item, _widget in self._apps.items():
            self.list.insert_child_after(_widget, None)

    def update_apps(self, new_apps: list[Application]) -> None:
        existing = set(self._apps.keys())
        desired = set(new_apps)

        to_add = desired - existing
        to_remove = existing - desired

        for app in to_add:
            widget = AppItem(app, self.search)
            self._apps[app] = widget

        for app in to_remove:
            widget = self._apps.pop(app)
            widget.destroy()
            self.list.remove(widget)

        self.sort_by_frequent()


class AppsWindow(widget.LayerWindow):
    __gtype_name__ = "AppsWindow"

    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            anchors={
                "top": True,
                "left": True
            },
            margins={
                "top": HyprlandVars.gap,
                "left": HyprlandVars.gap
            },
            css_classes=("apps-menu",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="apps_menu",
            height=400,
            width=400,
            setup_popup=True
        )
        self.name = "apps_menu"
        self._child: AppsBox | None = None
        weakref.finalize(self, lambda: logger.debug("AppsWindow finalized"))

    def on_show(self) -> None:
        glib.idle_add(apps_reload)
        if not self._child:
            self._child = AppsBox()
            self.set_child(self._child)
        else:
            self._child.entry.grab_focus()

    def on_hide(self) -> None:
        if self._child:
            self._child.entry.set_text("")
