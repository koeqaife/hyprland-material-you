from repository import gtk
from config import info, VERSION
import src.services.hyprland as hyprland
import os
import platform
from utils.system import STATIC_SYSTEM_INFO as STATIC
from utils.system import get_swap_total

from src.modules.settings.base import Row

USER = os.environ.get("USER") or os.environ.get("USERNAME")
HOSTNAME = os.environ.get("HOSTNAME") or os.uname().nodename
SHELL = os.environ.get("SHELL", "Unknown")
GTK_VERSION = f"{gtk.MAJOR_VERSION}.{gtk.MINOR_VERSION}.{gtk.MICRO_VERSION}"


class InfoRow(gtk.Box):
    __gtype_name__ = "SettingsInfoRow"

    def __init__(self) -> None:
        super().__init__(
            css_classes=("info-row", "settings-row")
        )

        self.logo = gtk.Label(
            label="M",
            css_classes=("logo",),
            halign=gtk.Align.START,
            valign=gtk.Align.START
        )
        self.info_box = gtk.Box(
            css_classes=("info-box",),
            orientation=gtk.Orientation.VERTICAL
        )

        self.children = (
            gtk.Label(
                label=info["name"],
                css_classes=("title",),
                halign=gtk.Align.START
            ),
            gtk.Label(
                label=f"Author: {info["author"]}",
                css_classes=("author",),
                halign=gtk.Align.START
            ),
            gtk.Label(
                label=f"Version: {VERSION}",
                css_classes=("version",),
                halign=gtk.Align.START
            )
        )

        self.append(self.logo)
        self.append(self.info_box)
        for child in self.children:
            self.info_box.append(child)

    def destroy(self) -> None:
        ...


class InfoPage(gtk.ScrolledWindow):
    __gtype_name__ = "SettingsInfoPage"

    def __init__(self) -> None:
        self.box = gtk.Box(
            css_classes=("page-box",),
            orientation=gtk.Orientation.VERTICAL
        )
        super().__init__(
            css_classes=("info-page", "settings-page",),
            child=self.box,
            hscrollbar_policy=gtk.PolicyType.NEVER
        )
        total_swap = int(get_swap_total())
        self.box_children = (
            InfoRow(),
            gtk.Separator(),
            Row("WM", f"Hyprland {hyprland.client.version}"),
            Row("CPU", str(STATIC["cpu"])),
            Row("Memory", f"{STATIC["total_ram"]} MB"),
            Row("Swap", f"{total_swap} MB"),
            Row("Kernel", str(STATIC["kernel"])),
            Row("Distro", str(STATIC["distro"])),
            Row("User", USER),
            Row("Hostname", HOSTNAME),
            Row("Shell", SHELL),
            Row("Python", platform.python_version()),
            Row("Gtk", GTK_VERSION)
        )
        for child in self.box_children:
            self.box.append(child)

    def destroy(self) -> None:
        for child in self.box_children:
            if hasattr(child, "destroy"):
                child.destroy()
