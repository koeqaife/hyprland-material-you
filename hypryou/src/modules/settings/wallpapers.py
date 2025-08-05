from repository import gtk, pango, gdk_pixbuf, glib, gio
from config import APP_CACHE_DIR, Settings, wallpaper_dirs
from os.path import join
import os.path as path
import os
import hashlib
import concurrent.futures
import functools
from utils.logger import logger
from utils.styles import toggle_css_class
import threading
import typing as t
import weakref
from src.services.state import set_random_wallpaper, get_all_wallpapers
from src.services.state import task_lock as task_lock1
from utils.colors import task_lock as task_lock2
from utils.debounce import sync_debounce
from utils_cy.levenshtein import compute_score
import src.widget as widget

# That is so difficult to optimize that

THRESHOLD = 0.2
executor: concurrent.futures.ProcessPoolExecutor | None = None
task_lock = threading.Lock()

THUMB_SIZE = 200
CACHE_DIR = join(APP_CACHE_DIR, "thumbnails")
os.makedirs(CACHE_DIR, exist_ok=True)


def get_thumbnail_path(file_path: str) -> str:
    key = hashlib.sha256(file_path.encode()).hexdigest()
    return join(CACHE_DIR, f"{key}_{THUMB_SIZE}x{THUMB_SIZE}.png")


def generate_thumbnail(source_path: str, dest_path: str) -> None:
    pixbuf = gdk_pixbuf.Pixbuf.new_from_file_at_scale(
        source_path, THUMB_SIZE, THUMB_SIZE, True
    )
    pixbuf.savev(dest_path, "png", [], [])


def generate_all(file_list: list[str]) -> None:
    for f in file_list:
        dest_path = get_thumbnail_path(f)
        if not path.exists(dest_path):
            generate_thumbnail(f, dest_path)


def spawn_thumbnail_process(
    paths: list[str],
    on_done: t.Callable[[], None] | None = None
) -> None:
    global executor

    _on_done: weakref.WeakMethod[t.Any] | weakref.ReferenceType[t.Any] | None
    if on_done:
        if hasattr(on_done, "__self__"):
            _on_done = weakref.WeakMethod(on_done)
        else:
            _on_done = weakref.ref(on_done)
    else:
        _on_done = None
    on_done = None

    def _callback(future: concurrent.futures.Future[None]) -> None:
        try:
            future.result()
        except Exception as e:
            logger.error("Couldn't generate thumbnails: %s", e, exc_info=e)
        if _on_done and (method := _on_done()) is not None:
            method()
        if executor is not None:
            executor.shutdown(False)

    if (
        task_lock.acquire(blocking=False)
        and not task_lock1.locked()
        and not task_lock2.locked()
    ):
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=1
        )
        try:
            future = executor.submit(
                functools.partial(
                    generate_all,
                    paths
                )
            )
            future.add_done_callback(_callback)
        finally:
            task_lock.release()


class WallpaperCard(gtk.Button):
    __gtype_name__ = "SettingsWallpaperCard"

    def __init__(
        self,
        file: str
    ) -> None:
        self.path = file
        self.settings = Settings()
        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            vexpand=True,
        )
        super().__init__(
            css_classes=("wallpaper",),
            child=self.box,
            tooltip_text=path.basename(file),
            hexpand=True,
            vexpand=True
        )
        self.image = gtk.Picture(
            css_classes=("image",),
            content_fit=gtk.ContentFit.COVER,
            vexpand=True,
            hexpand=True
        )
        self.name = gtk.Label(
            css_classes=("name",),
            label=path.basename(file),
            xalign=0,
            ellipsize=pango.EllipsizeMode.END,
            max_width_chars=16
        )
        self.box.append(self.image)
        self.box.append(self.name)

        self.handler = self.connect("clicked", self.on_clicked)

    def on_clicked(self, *args: t.Any) -> None:
        self.settings.set("wallpaper", self.path)

    def load_image(self) -> None:
        thumb_path = get_thumbnail_path(self.path)

        if not path.exists(thumb_path):
            return

        pixbuf = gdk_pixbuf.Pixbuf.new_from_file(str(thumb_path))
        self.image.set_pixbuf(pixbuf)

    def destroy(self) -> None:
        self.image.set_pixbuf(None)
        self.disconnect(self.handler)


class WallpapersList(gtk.Box):
    __gtype_name__ = "SettingsWallpapersList"

    def __init__(self) -> None:
        self.settings = Settings()
        self.flow_box = gtk.FlowBox(
            selection_mode=gtk.SelectionMode.NONE,
            homogeneous=True,
            valign=gtk.Align.START
        )
        self.box = gtk.Box(
            vexpand=True,
            hexpand=True
        )
        super().__init__(
            css_classes=("wallpapers-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        self.items: dict[str, WallpaperCard] = {}
        self._last_active: tuple[str, WallpaperCard] | None = None
        self.load_all()
        self.settings_handler = self.settings.watch(
            "wallpaper", self.on_wallpaper_update, False
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
        self.entry_handler = (
            self.entry.connect("notify::text", self.on_search)
        )

        self.append(self.search_box)
        self.append(self.flow_box)

    @sync_debounce(150)
    def on_search(self, *args: t.Any) -> None:
        text = self.entry.get_text()
        self.flow_box.remove_all()
        if len(text.strip()) == 0:
            for item in self.items.values():
                self.flow_box.append(item)
            return

        for item in self.items.values():
            score = compute_score(item.name.get_text(), text)
            if score >= THRESHOLD:
                self.flow_box.append(item)

    def on_wallpaper_update(self, new: str) -> None:
        if self._last_active:
            toggle_css_class(self._last_active[1], "active", False)
        new_active = self.items.get(new)
        if new_active:
            toggle_css_class(new_active, "active", True)
            self._last_active = (new, new_active)

    def update_all(self) -> None:
        def _callback() -> None:
            for item in self.items.values():
                item.load_image()
            current_wallpaper = self.settings.get(
                "wallpaper"
            )
            self.on_wallpaper_update(current_wallpaper)

        glib.idle_add(_callback)

    def load_all(self) -> None:
        images = get_all_wallpapers()

        for image in images:
            _widget = WallpaperCard(image)
            self.items[image] = _widget
            self.flow_box.append(_widget)

        spawn_thumbnail_process(images, self.update_all)

    def destroy(self) -> None:
        for item in self.items.values():
            item.destroy()
        self.settings.unwatch(self.settings_handler)
        self.entry.disconnect(self.entry_handler)


class Actions(gtk.Box):
    __gtype_name__ = "SettingsWallpapersActions"

    def __init__(self) -> None:
        super().__init__(
            css_classes=("actions-box",),
            halign=gtk.Align.END
        )
        self.random_button = gtk.Button(
            css_classes=("text",),
            label="Random"
        )
        self.view_folder_button = gtk.Button(
            css_classes=("text",),
            label="View Folder"
        )

        self.button_handlers = {
            self.random_button: self.random_button.connect(
                "clicked", lambda *_: set_random_wallpaper()
            ),
            self.view_folder_button: self.view_folder_button.connect(
                "clicked", self.open_folder
            )
        }
        self.append(self.random_button)
        self.append(self.view_folder_button)

    def open_folder(self, *args: t.Any) -> None:
        try:
            file = gio.File.new_for_path(wallpaper_dirs[0])
            uri = file.get_uri()
            gio.AppInfo.launch_default_for_uri_async(
                uri,
                None,
                None,
                None
            )
        except Exception as e:
            raise e

    def destroy(self) -> None:
        for button, handler in self.button_handlers.items():
            button.disconnect(handler)


class WallpapersPage(gtk.Box):
    __gtype_name__ = "SettingsWallpapersPage"

    def __init__(self) -> None:
        self.scrollable = gtk.ScrolledWindow(
            hscrollbar_policy=gtk.PolicyType.NEVER,
            vexpand=True
        )
        super().__init__(
            css_classes=("wallpapers-page", "settings-page",),
            orientation=gtk.Orientation.VERTICAL
        )
        self.list = WallpapersList()
        self.actions = Actions()
        self.scrollable.set_child(self.list)
        self.append(self.scrollable)
        self.append(self.actions)

    def destroy(self) -> None:
        self.list.destroy()
        self.actions.destroy()
