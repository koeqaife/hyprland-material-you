from repository import gtk, pango
from utils import widget, Ref, toggle_css_class
import typing as t
from src.variables.clock import full_date
import os


# TODO: Make buttons work


class ManagementButton(gtk.Button):
    def __init__(
        self,
        icon: str | Ref[str],
        label: str,
        state: str,
        id: str,
        activated: bool,
        on_click: t.Callable[[str], None] | None = None,
        on_right_click: t.Callable[[str], None] | None = None
    ) -> None:
        self.box = gtk.Box()
        super().__init__(
            css_classes=("management-button",),
            child=self.box
        )
        toggle_css_class(self, "activated", activated)
        self.id = id
        self.icon = widget.Icon(icon)
        self.label = gtk.Label(
            label=label,
            halign=gtk.Align.START,
            css_classes=("label",)
        )
        self.state = gtk.Label(
            label=state,
            halign=gtk.Align.START,
            css_classes=("state",),
            ellipsize=pango.EllipsizeMode.END
        )
        self.text_box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL,
            hexpand=True
        )

        self.arrow = widget.Icon("chevron_right") if on_right_click else None

        self.text_box.append(self.label)
        self.text_box.append(self.state)
        self.box.append(self.icon)
        self.box.append(self.text_box)
        if self.arrow:
            self.box.append(self.arrow)

    def destroy(self) -> None:
        ...


class InfoBox(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            css_classes=("info-box",)
        )
        self.date = gtk.Label(
            css_classes=("date-label",),
            halign=gtk.Align.START,
            hexpand=True
        )
        self.username = gtk.Label(
            css_classes=("username-label",),
            halign=gtk.Align.END,
            label=os.getenv("USER")
        )
        self.date.set_label(full_date.value)
        full_date.watch(self.on_date_update)

        self.append(self.date)
        self.append(self.username)

    def on_date_update(self, new_value: str) -> None:
        self.date.set_label(new_value)

    def destroy(self) -> None:
        full_date.unwatch(self.on_date_update)


class ManagementLine(gtk.Box):
    def __init__(
        self,
        first_child: ManagementButton,
        second_child: ManagementButton
    ) -> None:
        super().__init__(
            homogeneous=True,
            css_classes=("management-line",)
        )
        self.first_child = first_child
        self.second_child = second_child
        self.append(first_child)
        self.append(second_child)

    def destroy(self) -> None:
        self.first_child.destroy()
        self.second_child.destroy()


class ManagementFirstPage(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL
        )

        self.internet = ManagementButton(
            "signal_wifi_4_bar",
            "Internet",
            "UNKNOWN_WIFI_NAME",
            "internet",
            True,
            on_right_click=lambda: None
        )
        self.bluetooth = ManagementButton(
            "bluetooth",
            "Bluetooth",
            "Off",
            "bluetooth",
            False,
            on_right_click=lambda: None
        )
        self.dark_mode = ManagementButton(
            "contrast",
            "Dark Mode",
            "On",
            "dark_mode",
            True
        )
        self.dnd = ManagementButton(
            "do_not_disturb_off",
            "Do Not Disturb",
            "Off",
            "dnd",
            False
        )
        self.idle_inhibitor = ManagementButton(
            "schedule",
            "Idle Inhibitor",
            "Off",
            "idle_inhibitor",
            False
        )
        self.night_light = ManagementButton(
            "nightlight",
            "Night Light",
            "Off",
            "night_light",
            False
        )
        self.lines = (
            ManagementLine(self.internet, self.bluetooth),
            ManagementLine(self.dark_mode, self.dnd),
            ManagementLine(self.idle_inhibitor, self.night_light)
        )
        for line in self.lines:
            self.append(line)

    def destroy(self) -> None:
        for line in self.lines:
            line.destroy()
            self.remove(line)


class ManagementBox(gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=gtk.Orientation.VERTICAL,
            css_classes=("management-box",)
        )
        self.stack = gtk.Stack(
            transition_type=gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            transition_duration=250,
            valign=gtk.Align.START
        )
        # NOTE: In the future I can add more pages
        self.first_page = ManagementFirstPage()
        self.stack.add_named(self.first_page, "1")
        self.stack.set_visible_child_name("1")

        self.info_box = InfoBox()

        self.append(self.info_box)
        self.append(self.stack)

    def destroy(self) -> None:
        self.info_box.destroy()
        self.first_page.destroy()
