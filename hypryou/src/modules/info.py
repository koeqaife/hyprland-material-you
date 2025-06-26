from repository import layer_shell, gtk, glib, pango
from config import HyprlandVars, VERSION, info
import src.widget as widget
import weakref
from utils.logger import logger
from utils import toggle_css_class
import utils.system as system
import webbrowser

ICON_SIZE = 22
STATIC = {
    "total_ram": int(system.get_memory_total()),
    "cpu": f"{system.get_cpu_name()} ({system.get_cpu_counts()})",
    "kernel": " ".join(system.get_kernel_info())
}


class InfoPage(gtk.Box):
    __gtype_name__ = "InfoPage"

    def __init__(self) -> None:
        super().__init__(
            css_classes=("info-page", "stack-page"),
            orientation=gtk.Orientation.VERTICAL
        )
        self.logo_box = gtk.Box(
            css_classes=("logo-box",),
            orientation=gtk.Orientation.VERTICAL,
            hexpand=True,
            vexpand=True,
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )
        self.logo = gtk.Label(
            css_classes=("logo",),
            label="M",
            valign=gtk.Align.CENTER,
            halign=gtk.Align.CENTER
        )
        self.name = gtk.Label(
            css_classes=("name",),
            label=f"{info["name"]} by {info["author"]}"
        )
        self.version = gtk.Label(
            css_classes=("version",),
            label=VERSION
        )
        self.logo_box.append(self.logo)
        self.logo_box.append(self.name)
        self.logo_box.append(self.version)

        self.buttons_box = gtk.Box(
            css_classes=("buttons-box",),
            homogeneous=True,
            hexpand=True
        )

        self.github_icon = gtk.Image(
            icon_name="github-symbolic",
            css_classes=("icon",)
        )
        self.github_icon.set_pixel_size(ICON_SIZE)
        self.github_button = gtk.Button(
            css_classes=("github",),
            tooltip_text="Github",
            child=self.github_icon
        )

        self.discord_icon = gtk.Image(
            icon_name="discord-symbolic",
            css_classes=("icon",)
        )
        self.discord_icon.set_pixel_size(ICON_SIZE)
        self.discord_button = gtk.Button(
            css_classes=("discord",),
            tooltip_text="Discord",
            child=self.discord_icon
        )

        self.kofi_icon = gtk.Image(
            icon_name="kofi-symbolic",
            css_classes=("icon",)
        )
        self.kofi_icon.set_pixel_size(ICON_SIZE)
        self.kofi_button = gtk.Button(
            css_classes=("kofi",),
            tooltip_text="Ko-Fi",
            child=self.kofi_icon
        )

        self.buttons_box.append(self.github_button)
        self.buttons_box.append(self.discord_button)
        self.buttons_box.append(self.kofi_button)

        self.handlers = {
            self.github_button: self.github_button.connect(
                "clicked", lambda *_: webbrowser.open(info["github"])
            ),
            self.discord_button: self.discord_button.connect(
                "clicked", lambda *_: webbrowser.open(info["discord"])
            ),
            self.kofi_button: self.kofi_button.connect(
                "clicked", lambda *_: webbrowser.open(info["ko-fi"])
            )
        }

        self.append(self.logo_box)
        self.append(self.buttons_box)

    def destroy(self) -> None:
        for button, handler in self.handlers.items():
            button.disconnect(handler)


class MonitorRow(gtk.Box):
    __gtype_name__ = "MonitorRow"

    def __init__(
        self,
        name: str
    ) -> None:
        super().__init__(
            css_classes=("monitor-row",),
            hexpand=True
        )
        self.name = gtk.Label(
            label=name,
            css_classes=("label",),
            hexpand=True,
            xalign=0
        )
        self.value = gtk.Label(
            label="-",
            css_classes=("value",)
        )
        self.append(self.name)
        self.append(self.value)


class InfoRow(gtk.Box):
    __gtype_name__ = "InfoRow"

    def __init__(
        self,
        label: str,
        description: str,
        is_visible: bool = True
    ) -> None:
        super().__init__(
            css_classes=("info-row",),
            hexpand=True,
            orientation=gtk.Orientation.VERTICAL,
            visible=is_visible
        )
        self.name = gtk.Label(
            label=label,
            css_classes=("label",),
            hexpand=True,
            xalign=0
        )
        self.description = gtk.Label(
            label=description,
            css_classes=("description",),
            hexpand=True,
            xalign=0,
            ellipsize=pango.EllipsizeMode.END
        )
        self.append(self.name)
        self.append(self.description)
        self.set_tooltip_text(description)


class SystemPage(gtk.Box):
    __gtype_name__ = "SystemPage"

    def __init__(self) -> None:
        super().__init__(
            css_classes=("system-page", "stack-page"),
            orientation=gtk.Orientation.VERTICAL
        )
        self.cpu_prev_total = 0
        self.cpu_prev_idle = 0
        self.cpu_usage = MonitorRow("CPU")
        self.ram_usage = MonitorRow("Memory")
        self.swap_usage = MonitorRow("Swap")
        self.uptime = MonitorRow("Uptime")

        self.swap_row = InfoRow("Swap", "0 MB", False)

        self.children = (
            self.cpu_usage,
            self.ram_usage,
            self.swap_usage,
            self.uptime,
            gtk.Separator(
                orientation=gtk.Orientation.HORIZONTAL
            ),
            InfoRow("CPU", STATIC["cpu"]),
            InfoRow("Memory", f"{STATIC["total_ram"]} MB"),
            self.swap_row,
            InfoRow("Kernel", STATIC["kernel"])
        )

        for child in self.children:
            self.append(child)

        self.poll()
        self.timeout = glib.timeout_add(1000, self.poll)

    def update_cpu(self) -> None:
        percent, total, idle = system.get_cpu_percent(
            self.cpu_prev_total, self.cpu_prev_idle
        )
        self.cpu_prev_total = total
        self.cpu_prev_idle = idle
        self.cpu_usage.value.set_label(f"{percent}%")

    def update_memory(self) -> None:
        total, used, percent = system.get_memory_usage()
        self.ram_usage.value.set_label(f"{int(percent)}%")
        self.ram_usage.set_tooltip_text(f"{int(used)} MB / {int(total)} MB")

    def update_swap(self) -> None:
        total, used, percent = system.get_swap_usage()
        if total > 0:
            total_str = f"{int(total)} MB"
            self.swap_usage.value.set_label(f"{int(percent)}%")
            self.swap_usage.set_tooltip_text(f"{int(used)} MB / {total_str}")
            self.swap_row.description.set_label(total_str)
            self.swap_row.set_tooltip_text(total_str)

            self.swap_row.set_visible(True)
            self.swap_usage.set_visible(True)
        else:
            self.swap_row.set_visible(False)
            self.swap_usage.set_visible(False)

    def poll(self) -> bool:
        self.update_cpu()
        self.update_memory()
        self.update_swap()

        uptime = system.get_uptime_seconds()
        self.uptime.value.set_label(system.format_uptime(uptime))

        return True

    def destroy(self) -> None:
        glib.source_remove(self.timeout)


class InfoStack(gtk.Box):
    __gtype_name__ = "InfoStack"

    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL,
            css_classes=("info-box",)
        )

        self._last_active: widget.StackButton | None = None
        self.current_page = "info"
        self.buttons = {
            "info": widget.StackButton(
                "info", "Info", "info",
                self.change_page, "HyprYou info"
            ),
            "system": widget.StackButton(
                "system", "System", "browse_activity",
                self.change_page, "System monitor and info"
            ),
        }
        self.page_widgets: dict[str, InfoPage | SystemPage] = {
            "info": InfoPage(),
            "system": SystemPage()
        }
        self.buttons_box = gtk.Box(
            css_classes=("buttons-box",),
            homogeneous=True
        )
        self.stack = gtk.Stack(
            css_classes=("info-stack",),
            transition_type=gtk.StackTransitionType.CROSSFADE,
            transition_duration=250
        )

        for button in self.buttons.values():
            self.buttons_box.append(button)

        for name, page in self.page_widgets.items():
            self.stack.add_named(page, name)

        self.append(self.buttons_box)
        self.append(self.stack)
        self.update_active_button()

    def update_active_button(self) -> None:
        new_active = self.buttons[self.current_page]
        if new_active is not self._last_active:
            if self._last_active is not None:
                toggle_css_class(self._last_active, "active", False)
            toggle_css_class(new_active, "active", True)
            self._last_active = new_active

    def change_page(self, to: str) -> None:
        self.stack.set_visible_child_name(to)
        self.current_page = to
        self.update_active_button()

    def destroy(self) -> None:
        for button in self.buttons.values():
            button.destroy()
        for page in self.page_widgets.values():
            page.destroy()


class InfoWindow(widget.LayerWindow):
    __gtype_name__ = "InfoWindow"

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
            css_classes=("info",),
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            layer=layer_shell.Layer.OVERLAY,
            hide_on_esc=True,
            name="info",
            height=1,
            width=1,
            setup_popup=True
        )
        self._child: InfoStack | None = None

        weakref.finalize(self, lambda: logger.debug("InfoWindow finalized"))

    def on_show(self) -> None:
        self._child = InfoStack()
        self.set_child(self._child)

    def on_hide(self) -> None:
        if self._child:
            self._child.destroy()
        self.set_child(None)
        self._child = None

    def destroy(self) -> None:
        super().destroy()
