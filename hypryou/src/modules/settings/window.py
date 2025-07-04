from repository import gtk
import typing as t
import src.widget as widget
from utils import toggle_css_class
from utils.logger import logger
import weakref
from src.services.state import settings_page

# Pages
from src.modules.settings.network import NetworkPage
from src.modules.settings.bluetooth import BluetoothPage
from src.modules.settings.appearance import AppearancePage


class Page(t.NamedTuple):
    title: str
    icon: str
    icon_fill: bool
    widget: type[gtk.Widget]


if t.TYPE_CHECKING:
    class PageType(gtk.Widget):
        def destroy(self) -> None:
            ...

        def on_show(self) -> None:
            ...

        def on_hide(self) -> None:
            ...


class NotImplementedYet(gtk.Label):
    def __init__(self) -> None:
        super().__init__(label="Not Implemented Yet")


pages = {
    "network": Page(
        title="Network",
        icon="network_manage",
        icon_fill=False,
        widget=NetworkPage
    ),
    "bluetooth": Page(
        title="Bluetooth",
        icon="settings_bluetooth",
        icon_fill=False,
        widget=BluetoothPage
    ),
    "appearance": Page(
        title="Appearance",
        icon="palette",
        icon_fill=True,
        widget=AppearancePage
    ),
    "wallpaper": Page(
        title="Wallpaper",
        icon="wallpaper",
        icon_fill=False,
        widget=NotImplementedYet
    ),
    "input": Page(
        title="Input",
        icon="keyboard",
        icon_fill=True,
        widget=NotImplementedYet
    ),
    "monitors": Page(
        title="Monitors",
        icon="monitor",
        icon_fill=True,
        widget=NotImplementedYet
    ),
    "sleep": Page(
        title="Sleep",
        icon="power_settings_circle",
        icon_fill=True,
        widget=NotImplementedYet
    ),
    "apps": Page(
        title="Apps",
        icon="settings_applications",
        icon_fill=True,
        widget=NotImplementedYet
    ),
    "hyprland": Page(
        title="Hyprland",
        icon="tune",
        icon_fill=False,
        widget=NotImplementedYet
    ),
    "keybinds": Page(
        title="Keybinds",
        icon="action_key",
        icon_fill=True,
        widget=NotImplementedYet
    ),
    "info": Page(
        title="Info",
        icon="info",
        icon_fill=True,
        widget=NotImplementedYet
    )
}

sidebar = (
    "network",
    "bluetooth",
    "separator",
    "appearance",
    "wallpaper",
    "separator",
    "input",
    "monitors",
    "sleep",
    "apps",
    "separator",
    "hyprland",
    "keybinds",
    "separator",
    "info"
)


class SidebarButton(gtk.Button):
    __gtype_name__ = "SettingsSidebarButton"

    def __init__(
        self,
        name: str,
        title: str,
        icon: str,
        icon_fill: bool,
        on_click: t.Callable[[str], None]
    ) -> None:
        self.on_click_ref = weakref.WeakMethod(on_click)
        self.name = name
        self.box = gtk.Box()
        super().__init__(
            css_classes=("sidebar-button",),
            child=self.box,
            hexpand=True,
            valign=gtk.Align.START
        )
        toggle_css_class(self, "icon-fill", icon_fill)

        self.icon = widget.Icon(icon)
        self.label = gtk.Label(label=title)

        self.box.append(self.icon)
        self.box.append(self.label)

        self.handler = self.connect(
            "clicked", self.on_click
        )

    def on_click(self, *args: t.Any) -> None:
        on_click = self.on_click_ref()
        if on_click is not None:
            on_click(self.name)

    def destroy(self) -> None:
        self.disconnect(self.handler)
        self.icon.destroy()


class SettingsBox(gtk.Box):
    __gtype_name__ = "SettingsBox"

    def __init__(self, window: "SettingsWindow") -> None:
        self.window = weakref.ref(window)
        super().__init__(
            css_classes=("settings-box",),
            hexpand=True,
            vexpand=True
        )

        self.sidebar = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            css_classes=("settings-sidebar",),
            vexpand=True,
            hexpand=False,
            halign=gtk.Align.START
        )
        self.sidebar_scrollable = gtk.ScrolledWindow(
            hscrollbar_policy=gtk.PolicyType.NEVER,
            child=self.sidebar
        )
        self.view = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            css_classes=("settings-view",),
            vexpand=True,
            hexpand=True,
        )
        self.title_box = gtk.Box(
            css_classes=("title-box",),
            hexpand=True
        )
        self.title = gtk.Label(
            css_classes=("page-title",),
            hexpand=True,
            valign=gtk.Align.START,
            xalign=0
        )
        self.close_button = gtk.Button(
            child=widget.Icon("close"),
            css_classes=("icon-elevated", "close"),
            halign=gtk.Align.END,
            valign=gtk.Align.CENTER
        )
        self.close_handler = self.close_button.connect(
            "clicked", self.on_close
        )
        self.title_box.append(self.title)
        self.title_box.append(self.close_button)
        self.stack = gtk.Stack(
            css_classes=("settings-stack",),
            hexpand=True,
            vexpand=True,
            transition_duration=250,
            transition_type=gtk.StackTransitionType.CROSSFADE
        )
        self.settings_title = gtk.Label(
            css_classes=("settings-title",),
            hexpand=True,
            xalign=0,
            label="Settings"
        )
        self.default_page = gtk.Label(
            label="Select a category to get started.",
            css_classes=("default-label",),
            hexpand=True,
            vexpand=True
        )
        self.stack.add_named(self.default_page, "default")
        self.sidebar.append(self.settings_title)
        self.view.append(self.title_box)
        self.view.append(self.stack)
        self.append(self.sidebar_scrollable)
        self.append(self.view)

        self.pages_widgets: dict[str, type[gtk.Widget]] = {}
        self.pages: dict[str, PageType] = {}
        self.buttons: dict[str, SidebarButton] = {}
        self.titles: dict[str, str] = {}
        self.cur_page = ""

        for key, page in pages.items():
            self.pages_widgets[key] = page.widget
            self.buttons[key] = SidebarButton(
                key,
                page.title,
                page.icon,
                page.icon_fill,
                self.change_page
            )
            self.titles[key] = page.title

        last_widget: gtk.Widget | None = None
        for object in sidebar:
            if object == "separator":
                if last_widget is not None:
                    toggle_css_class(last_widget, "next-separator", True)
                self.sidebar.append(gtk.Separator(
                    orientation=gtk.Orientation.HORIZONTAL
                ))
                last_widget = None
                continue

            if object in self.buttons:
                self.sidebar.append(self.buttons[object])
                last_widget = self.buttons[object]
            else:
                logger.warning("Couldn't find object with name %s", object)
        last_widget = None

    def on_close(self, *args: t.Any) -> None:
        window = self.window()
        if window is not None:
            window.emit("close-request")

    def change_page(self, name: str) -> None:
        last_page = self.cur_page
        if last_page:
            toggle_css_class(self.buttons[last_page], "active", False)
        if name == "default":
            self.stack.set_visible_child_name("default")
            return
        self.cur_page = name

        # Lazy load page
        if name not in self.pages.keys():
            _widget = self.pages_widgets[name]()
            self.pages[name] = _widget
            self.stack.add_named(_widget, name)

        self.stack.set_visible_child_name(name)
        toggle_css_class(self.buttons[name], "active", True)
        self.title.set_label(self.titles[name])

        # Page on_show/on_hide methods
        if last_page in self.pages.keys():
            page = self.pages[last_page]
            if hasattr(page, "on_hide") and callable(page.on_hide):
                page.on_hide()

        page = self.pages[name]
        if hasattr(page, "on_show") and callable(page.on_show):
            page.on_show()

    def destroy(self) -> None:
        self.close_button.disconnect(self.close_handler)
        for page in self.pages.values():
            if hasattr(page, "destroy"):
                page.destroy()

        for button in self.buttons.values():
            button.destroy()


class SettingsWindow(gtk.ApplicationWindow):
    __gtype_name__ = "SettingsWindow"

    def __init__(
        self,
        app: gtk.Application,
        page: str
    ) -> None:
        super().__init__(
            application=app,
            title="Settings",
            css_classes=("settings",),
            default_height=1,
            default_width=1,
            decorated=False
        )
        self._destroyed = False
        self._child = SettingsBox(self)
        self._child.change_page(page)
        self.set_child(self._child)

        self.close_handler = self.connect(
            "close-request", self.on_close_request
        )
        if __debug__:
            weakref.finalize(
                self, lambda: logger.debug("SettingsWindow finalized")
            )

    def on_close_request(self, window: gtk.Window) -> bool:
        self.destroy()
        return False

    def destroy(self) -> None:
        self._destroyed = True
        settings_page.value = None
        self.disconnect(self.close_handler)
        self._child.destroy()
        super().destroy()


class SettingsWatcher:
    @classmethod
    def register(cls, app: gtk.Application) -> "SettingsWatcher":
        return cls(app)

    def __init__(
        self,
        app: gtk.Application
    ) -> None:
        self.app = app
        self.window: SettingsWindow | None = None
        self.handler = settings_page.watch(self.on_changed)

    def on_changed(self, value: str | None) -> None:
        if value is None and self.window is not None:
            if not self.window._destroyed:
                self.window.destroy()
            self.window = None
        elif value is not None:
            if self.window is None:
                self.window = SettingsWindow(self.app, value)
                self.window.present()
            else:
                self.window._child.change_page(value)

    def destroy(self) -> None:
        if self.window is not None:
            self.window.destroy()
        settings_page.unwatch(self.handler)
