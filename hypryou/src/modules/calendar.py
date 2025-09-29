from repository import gtk, layer_shell
import calendar
from datetime import date
import src.widget as widget
import typing as t
from src.services.clock import full_date


def build_calendar_list(year: int, month: int) -> list[list[str]]:
    # First day is Monday
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)

    result: list[list[str]] = []
    for week in weeks:
        row = [str(day) if day != 0 else "" for day in week]
        result.append(row)

    return result


class CalendarWindow(widget.LayerWindow):
    def __init__(self, app: gtk.Application) -> None:
        super().__init__(
            app,
            layer=layer_shell.Layer.OVERLAY,
            name="calendar",
            setup_popup=True,
            hide_on_esc=True,
            keymode=layer_shell.KeyboardMode.ON_DEMAND,
            anchors={
                "top": True,
                "right": True
            },
            css_classes=("calendar",)
        )

        today = date.today()
        self.year, self.month = today.year, today.month
        self.is_today = True

        self.box = gtk.Box(
            orientation=gtk.Orientation.VERTICAL
        )
        self.header_box = gtk.Box(
            css_classes=("header-box",)
        )
        self.date_label = gtk.Label(
            css_classes=("date",),
            label="...",
            hexpand=True,
            xalign=0
        )
        self.previous = gtk.Button(
            child=widget.Icon("arrow_left"),
            css_classes=("icon-tonal", "previous")
        )
        self.next = gtk.Button(
            child=widget.Icon("arrow_right"),
            css_classes=("icon-tonal", "next")
        )
        self.today = gtk.Button(
            child=widget.Icon("today"),
            css_classes=("icon-tonal", "today")
        )
        self.header_box.append(self.date_label)
        self.header_box.append(self.previous)
        self.header_box.append(self.next)
        self.header_box.append(self.today)

        self.weekdays_box = gtk.Box(
            css_classes=("weekdays",),
            homogeneous=True
        )
        days = list(calendar.day_abbr)
        for abbr in days:
            self.weekdays_box.append(gtk.Label(
                label=abbr,
                css_classes=("weekday-entry",)
            ))

        self.entries_box = gtk.FlowBox(
            max_children_per_line=7,
            min_children_per_line=7,
            css_classes=("entries-box",),
            selection_mode=gtk.SelectionMode.NONE,
            homogeneous=True,
            row_spacing=0,
            column_spacing=0
        )

        self.box.append(self.header_box)
        self.box.append(self.weekdays_box)
        self.box.append(self.entries_box)
        self.set_child(self.box)

        self.button_handlers = {
            self.today: self.today.connect("clicked", self.on_today),
            self.next: self.next.connect("clicked", self.on_next),
            self.previous: self.previous.connect("clicked", self.on_previous),
        }
        full_date.watch(self.update_entries)

    def on_today(self, *args: t.Any) -> None:
        self.is_today = True
        self.update_entries()

    def on_next(self, *args: t.Any) -> None:
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self.is_today = False
        self.update_entries()

    def on_previous(self, *args: t.Any) -> None:
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self.is_today = False
        self.update_entries()

    def update_entries(self, *args: t.Any) -> None:
        self.entries_box.remove_all()

        if self.is_today:
            today = date.today()
            self.year, self.month = today.year, today.month

        today = date.today()
        year, month = today.year, today.month
        day = str(date.today().day)

        chosen_date = date(self.year, self.month, 1)
        self.date_label.set_label(chosen_date.strftime("%B %Y"))

        list = build_calendar_list(self.year, self.month)
        for row in list:
            for num, entry in enumerate(row):
                if not entry:
                    self.entries_box.append(gtk.Box(css_classes=("entry",)))
                    continue
                entry_widget = gtk.Label(
                    label=entry,
                    css_classes=("entry",)
                )
                if year == self.year and month == self.month:
                    if entry == day:
                        entry_widget.add_css_class("today")

                # First weekday is Monday!!
                if num == 5 or num == 6:
                    entry_widget.add_css_class("weekend")

                self.entries_box.append(entry_widget)

    def on_show(self) -> None:
        self.is_today = True
        self.update_entries()
        super().on_show()

    def destroy(self) -> None:
        for button, handler in self.button_handlers.items():
            button.disconnect(handler)
        super().destroy()
